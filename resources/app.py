import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from nosi_crewai.dynamic_main import main as dynamic_main
from nosi_crewai.dynamic_crew import DynamicCrew, InvalidProcessTypeError
from nosi_crewai.service.add_teams import add_teams
from nosi_crewai.service.add_agent import add_agent
from nosi_crewai.service.get_agents import get_all_agents
from nosi_crewai.service.get_teams import get_teams_info
from nosi_crewai.service.get_tools import get_available_tools
from nosi_crewai.service.get_llm import get_llms
from nosi_crewai.service.get_tasks import get_tasks
from nosi_crewai.service.add_task import add_task
import traceback

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def index():
    return "Welcome to the NOSI Crew AI API!"

@app.route('/run_crew', methods=['POST'])
def run_crew():
    # Check if the service is available
    service_url = os.getenv('LLM_SERVICE_URL')
    if not service_url:
        return jsonify({"error": "LLM_SERVICE_URL is not set in the environment"}), 500

    '''try:
        response = requests.get(service_url)
        response.raise_for_status()
    except requests.RequestException as e:
        app.logger.error(f"Local LLM service at LLM_SERVICE_URL is not available")
        return jsonify({"error": "Local LLM service is not available"}), 503'''

    # example of data structure at the end of dynamic_main
    data = request.json
    tasks = data.get('tasks') # gives tasks to be done list with [(description, expected_format, agent)]
    # the agent is the one that does the task, if you select sequential process -> agent section must be filled with the role of the agent or none if it is a hierarquical process
    selected_entity = data.get('selected_entity') # gives team or agent to be used, has to come as a dict {"agent 1":{"role":(...), "goal":(...), etc}, "agent 2": {...}, ...}
    selected_input = data.get('selected_input', None) # additional input data for the crew, has to come as a dict {"input 1":(...), "input 2": (...), ...}, (..) can be any data type, None if not needed
    running_options = data.get('running_options') # gives crew options, has to come as the default if none choosen e.g.: {"process": "hierarchical"} or {"process": "sequential"}
    process = running_options.get('process', 'hierarchical') # default process is hierarchical

    if not tasks or not selected_entity or not running_options:
        return jsonify({"error": "Missing tasks, selected_entity (team or agent) or running options"}), 400

    # Log the input data for debugging
    app.logger.info(f"Received tasks: {tasks}, selected_entity: {selected_entity}, running_options: {running_options}")

    # checks if tasks have agent for sequential process and if it is on the selected agents list
    if process == 'sequential':
        for task in tasks:
            if 'agent' not in task:
                return jsonify({"error": "Each task in sequential process must contain an 'agent' key"}), 400

            tasked_agent = task.get('agent')
            # You can now use the agent variable as needed
            app.logger.info(f"Task: {task}; Task agent: {tasked_agent}")

            # Check if the tasked_agent is equal to any role in selected_entity
            agent_found = False
            for agent, details in selected_entity.items():
                if tasked_agent == details.get('role'):
                    agent_found = True
                    break

            if not agent_found:
                return jsonify({"error": f"Agent '{tasked_agent}' in task does not match any role in selected_entity"}), 400
    elif process == 'hierarchical':
        for task in tasks:
            if 'agent' in task:
                return jsonify({"error": "Each task in hierarchical process must not contain an 'agent' key"}), 400
    else:
        return jsonify({"error": "Invalid process type"}), 400

    # Start the crew execution
    try:
        results = execute_crew(tasks, selected_entity, running_options, selected_input)
    except InvalidProcessTypeError as e:
        app.logger.error(f"Invalid process type: {str(e)}")
        return jsonify({"error": str(e)}), 400  # Return the custom error message with a 400 status
    except Exception as e:
        app.logger.error(f"Error during crew execution: {str(e)}")
        return jsonify({"error": "Crew execution failed", "details": str(e)}), 500  # Include details

    return jsonify({"message": "Crew execution successful", "results": results}), 202


def execute_crew(tasks, selected_entity, running_options, selected_input):
    try:
        transformed_results = dynamic_main(tasks, selected_entity, running_options, selected_input)
        print("Crew execution completed. Results saved in MongoDB.")
        return transformed_results
    except Exception as e:
        print(f"Error executing crew: {str(e)}")
        app.logger.error(traceback.format_exc())  # Log the traceback
        raise


@app.route('/create_team', methods=['POST'])
def create_teams_endpoint():
    # gets json dict with selected_agents (choosen existing agents to form a team) and team_name
    data = request.json
    selected_agents = data.get('selected agents') # selected agents entry has all the info about the agents [(role, goal, etc)]
    team_name = data.get('team name')

    if team_name is None:  # Check if task_name is provided
        return jsonify({"error": "Missing team name data"}), 400

    # gets all teams information
    existing_teams_info = get_teams_info()
    # Extract existing roles from all_agent_info
    existing_teams_names = set(existing_teams_info.keys())

    if team_name in existing_teams_names: # checks for repeated team names
        return jsonify({"error": "Team name already exists, choose a different one"}), 400

    # gets all info about existing agents
    existing_agents = get_all_agents()
    # Extract existing role names from the existing agents
    existing_agents_names = {agent["agent"]["role"] for agent in existing_agents}  # Accessing the nested structure

    if selected_agents is None: # Check if new_agents is provided
        return jsonify({"error": "Missing selected agents"}), 400

    for agent in selected_agents:
        # Ensure 'role', 'goal', 'backstory' keys exist in the agent dictionary
        if "role" and "backstory" and "goal" not in agent:
            return jsonify({"error": "Wrong format of selected agents. Must have all info (role, goal, etc)"}), 400

        # Check for if agent name exists in database
        if agent["role"] not in existing_agents_names:
            return jsonify({"error": "Agent is not a agent on the database", "message": str(e)}), 500

    try:
        add_teams(selected_agents, team_name)
        return jsonify({"message": "Team created successfully"}), 202
    except Exception as e:
        return jsonify({"error": "Failed to add agents to agent list.", "message": str(e)}), 500

'''
#TODO: add costum tools as options
@app.route('/create_tools', methods=['POST'])
def create_tools_endpoint():
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']

    # If the user does not select a file, the browser submits an empty part without a filename
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        filename = add_tools(file)
        return jsonify({'message': 'File uploaded successfully!', 'filename': filename}), 200
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to add agents to agent list.', "message": str(e)}), 400
'''

@app.route('/create_agent', methods=['POST'])  # creates agent if role is not already in the database
def create_agent_endpoint():
    # gets json dict with new agent (role, goal, backstory, llm, tools)
    data = request.json
    new_agent = data.get('new_agent')
    llm_model = new_agent.get('llm', 'azure/gpt-4o-mini') # defaults to azure/gpt-4o-mini

    if new_agent is None:  # Check if new_agent is provided
        return jsonify({"error": "Missing new agents data"}), 400

    # Gets all info about existing agents
    existing_agents = get_all_agents()

    # gets all info about existing agents
    existing_agents = get_all_agents()
    # Extract existing role names from the existing agents
    existing_agents_names = {agent["agent"]["role"] for agent in existing_agents}  # Accessing the nested structure

    # Check for repeated agent names
    if new_agent["role"] in existing_agents_names:
        return jsonify({"error": "Agent name already exists, choose a different one"}), 400

    existing_llms = get_llms()

    if llm_model not in existing_llms: # checks for repeated task names
        return jsonify({"error": "LLM model not in the available llms list"}), 400

    try:
        add_agent(new_agent)
        return jsonify({"message": "Agent created successfully"}), 202
    except Exception as e:
        return jsonify({"error": "Failed to add agents to agent list.", "message": str(e)}), 500

@app.route('/create_task', methods=['POST'])  # creates agent if role is not already in the database
def create_task_endpoint():
    # gets json dict with new agent (role, goal, backstory, llm, tools)
    data = request.json
    new_task = data.get('new task')
    task_name = data.get('task name')

    if task_name is None:  # Check if task_name is provided
        return jsonify({"error": "Missing task name data"}), 400

    if new_task is None:  # Check if new_task is provided
        return jsonify({"error": "Missing new task data"}), 400

    # Gets all info about existing tasks
    existing_tasks = get_tasks()

    # Extract existing tasks names
    existing_tasks_names = set(existing_tasks.keys())

    if task_name in existing_tasks_names: # checks for repeated task names
        return jsonify({"error": "Task name already exists, choose a different one"}), 400

    # Extract existing task descriptions from the existing tasks
    existing_tasks_description = {task["description"] for task in existing_tasks.values()}  # Using dict format

    # Extract existing task expected outputs from the existing tasks
    existing_tasks_output = {task["expected_output"] for task in existing_tasks.values()}  # Using dict format

    if new_task['description'] in existing_tasks_description and new_task['expected_output'] in existing_tasks_output: # checks for repeated task names
        return jsonify({"error": "Task already exists: Repeated description and expected output"}), 400

    try:
        add_task(new_task, task_name)
        return jsonify({"message": "Task created successfully"}), 202
    except Exception as e:
        return jsonify({"error": "Failed to add tasks to task list.", "message": str(e)}), 500

@app.route('/get_all_agents', methods=['GET']) # gets all agents information
def get_all_agents_endpoint():
    try:
        all_agents = get_all_agents() # returns list of agents with their info [(role, data)]
        return jsonify({"all agents": all_agents}), 200
    except Exception as e:
        return jsonify({"error": "Failed to load all agents configurations.", "message": str(e)}), 500

@app.route('/get_teams', methods=['GET'])
def get_teams():
    try:
        teams = get_teams_info() # returns all teams' information (agents that compose it)
        return jsonify({"teams": teams}), 200
    except Exception as e:
        return jsonify({"error": "Failed to load team configurations.", "message": str(e)}), 500

@app.route('/get_tasks', methods=['GET']) # gets all agents information
def get_tasks_endpoint():
    try:
        tasks = get_tasks() # returns list of agents with their info [(role, data)]
        return jsonify({"tasks": tasks}), 200
    except Exception as e:
        return jsonify({"error": "Failed to load tasks configurations.", "message": str(e)}), 500


@app.route('/get_tools', methods=['GET']) # Gets available tools
def get_tools():
    try:
        tools = get_available_tools() # returns all available tools for the user
        return jsonify({"tools": tools}), 200
    except Exception as e:
        return jsonify({"error": "Failed to load tool configurations.", "message": str(e)}), 500

@app.route('/get_llms', methods=['GET']) # Gets available llm models
def get_available_llms():
    try:
        # gets available llms to test (in a list)
        available_llms = get_llms()
        return jsonify({"llm models": available_llms}), 200
    except Exception as e:
        return jsonify({"error": "Failed to load available llm models.", "message": str(e)}), 500

if __name__ == '__main__':
    #app.debug = True
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

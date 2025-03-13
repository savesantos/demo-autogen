from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import HandoffTermination, TextMentionTermination
from autogen_agentchat.messages import HandoffMessage
from autogen_agentchat.teams import Swarm
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
import os
import sys
from langchain_community.tools import DuckDuckGoSearchResults
from dotenv import load_dotenv
import agentops

# Load environment variables from .env file
load_dotenv()

def duckduckgo_search_tool(search_query: str): 
    tool = DuckDuckGoSearchResults()
    result = tool.invoke(search_query)
    return result

model_client = AzureOpenAIChatCompletionClient(
    model="gpt-4o-mini",
    api_version=os.getenv("OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("OPENAI_API_BASE"),
    api_key=os.getenv("OPENAI_API_KEY"), # For key-based authentication.
)

general_manager = AssistantAgent(
    "general_manager",
    model_client=model_client,
    handoffs=["researcher_assistant", "data_analyst"],
    system_message="""You are the Cincinnati Bengals general manager.
    You are in charge of signing new players to the team.
    You must analyze the players statistics before signing them to find those that will be the best fit for the team.
    You must also take into account the salary cap when signing new players.
    The data_analyst is in charge of analyzing the players statistics.
    The researcher_assistant is in charge of collecting the data about the players.
    If you need information from the user, you must first send your message, then you can handoff to the user.
    Use TERMINATE when the all tasks are complete.""",
)


data_analyst = AssistantAgent(
    "data_analyst",
    model_client=model_client,
    handoffs=["general_manager", "researcher_assistant"],
    system_message="""You are a data analyst specialized in analyzing NFL players statistics.
    The reseacher_assistant is in charge of collecting the data about the players.
    The general_manager is in charge of signing new players to the team and making the final decision.
    If you need information from the user, you must first send your message, then you can handoff to the user.""",
)

researcher_assistant = AssistantAgent(
    "researcher_assistant",
    model_client=model_client,
    handoffs=["general_manager", "data_analyst"],
    tools=[duckduckgo_search_tool],
    system_message="""You are a researcher assistant specialized in collecting data about NFL players.
    You have the brave_search_tool to help you find information about the players on the web.
    The data_analyst is in charge of analyzing the players statistics.
    The general_manager is in charge of signing new players to the team and making the final decision.
    If you need information from the user, you must first send your message, then you can handoff to the user.""",
)

termination = TextMentionTermination("TERMINATE")
team = Swarm([general_manager, data_analyst, researcher_assistant], termination_condition=termination)

task = "I need to revamp the Cincinnati Bengals defense." \
"I need you to find the defensive players that are available in the 2025 free agency market that will be a good fit for the team." \
"Analyze the players statistics and make a recommendation of 3 players that we should sign." \
"Also, tell me how much they will cost." \
"Don't forget to list the reasons why you think they will be a good fit for the team." \
"Once you have the information, present it in a final report."

async def run_team_stream() -> None:
    task_result = await Console(team.run_stream(task=task))
    last_message = task_result.messages[-1]

    while isinstance(last_message, HandoffMessage) and last_message.target == "user":
        user_message = input("User: ")

        task_result = await Console(
            team.run_stream(task=HandoffMessage(source="user", target=last_message.source, content=user_message))
        )
        last_message = task_result.messages[-1]


# Use asyncio.run(...) if you are running this in a script.
import asyncio

if __name__ == "__main__":
    api_key = os.getenv("AGENTOPS_API_KEY")

    agentops.init(
        api_key=api_key,
        default_tags=['autogen']
    )
    
    asyncio.run(run_team_stream())
    agentops.end_session("Success")

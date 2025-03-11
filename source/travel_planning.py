from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from langchain_community.tools import BraveSearch 
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

api_key = os.getenv("BRAVE_SEARCH_API_KEY")

def brave_search_tool(search_query: str): 
    tool = BraveSearch.from_api_key(api_key=api_key)
    result = tool.run(search_query)
    return result

# Define a model client. You can use other model client that implements
# the `ChatCompletionClient` interface.
model_client = AzureOpenAIChatCompletionClient(
    model="gpt-4o-mini",
    api_version=os.getenv("OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("OPENAI_API_BASE"),
    api_key=os.getenv("OPENAI_API_KEY"), # For key-based authentication.
)

planning_agent = AssistantAgent(
    "PlanningAgent",
    description="An agent for planning tasks, this agent should be the first to engage when given a new task.",
    model_client=model_client,
    system_message="""
    You are a planning agent.
    Your job is to break down complex tasks into smaller, manageable subtasks.
    Your team members are:
        web_search_agent: Searches for travel information and suggestions
        local_agent: Provides local suggestions and activities
        travel_summary_agent: Summarizes the travel plan
        user_proxy: Represents the user, needed to approve the final plan

    You only plan and delegate tasks - you do not execute them yourself.

    When assigning tasks, use this format:
    1. <agent> : <task>

    After all tasks are complete, pass the control to the user_proxy agent to approve the final plan.
    """,
)

web_search_agent = AssistantAgent(
    "web_search_agent",
    model_client=model_client,
    tools=[brave_search_tool],
    description="A helpful assistant that can plan trips.",
    system_message="You are a helpful assistant that can suggest a travel plan for a user based on their request. Use the tool to search for information on the web to provide the best possible suggestions.",
)

local_agent = AssistantAgent(
    "local_agent",
    model_client=model_client,
    description="A local assistant that can suggest local activities or places to visit.",
    system_message="You are a helpful assistant that can suggest authentic and interesting local activities or places to visit for a user and can utilize any context information provided.",
)

travel_summary_agent = AssistantAgent(
    "travel_summary_agent",
    model_client=model_client,
    description="A helpful assistant that can summarize the travel plan.",
    system_message="You are a helpful assistant that can take in all of the suggestions and advice from the other agents and provide a detailed final travel plan. You must ensure that the final plan is integrated and complete. YOUR FINAL RESPONSE MUST BE THE COMPLETE PLAN.",
)

user_proxy = UserProxyAgent("user_proxy", input_func=input)  # Use input() to get user input from console.

termination = TextMentionTermination("APPROVED")

task = "" \
"Plan a 6 day trip to someplace in Europe this summer for a couple in Lisbon, Portugal. " \
"It can't be Prague, Budapest and Rome. " \
"If possible the destination should have a beach involved or an amuzement park. " \
"Our budget is limited to a maximum of 700€ per person. " \
"Offer insigths on budget requirements with fligths included by searching on the web. " \
"Provide references to information taken from the web."

selector_prompt = """Select an agent to perform task.

{roles}

Current conversation context:
{history}

Read the above conversation, then select an agent from {participants} to perform the next task.
Make sure the planner agent has assigned tasks before other agents start working.
Only select one agent.
"""

group_chat = SelectorGroupChat(
    [planning_agent, web_search_agent, local_agent, travel_summary_agent, user_proxy], 
    model_client=model_client,
    termination_condition=termination,
    selector_prompt=selector_prompt,
    allow_repeated_speaker=True,  # Allow an agent to speak multiple turns in a row.
)

async def main():
    await Console(group_chat.run_stream(task=task))

if __name__ == "__main__":
    asyncio.run(main())

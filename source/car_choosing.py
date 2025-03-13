from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from langchain_community.tools import BraveSearch 
import os
import sys
import asyncio
from dotenv import load_dotenv
import agentops

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

web_search_agent = AssistantAgent(
    "web_search_agent",
    model_client=model_client,
    tools=[brave_search_tool],
    description="A helpful assistant that can search for information on the web.",
    system_message="You are a helpful assistant that can search the web to find a car fitting the instructions of the user.",
)

assistant_agent = AssistantAgent(
    "assistant_agent",
    model_client=model_client,
    description="An assistant that can pose questions to the user to find out more about their preferences and give suggestions.",
    system_message="You are an assistant that can ask questions to the user to find out more about their preferences and give suggestions.",
)

user_proxy = UserProxyAgent("user_proxy", input_func=input)  # Use input() to get user input from console.

termination = TextMentionTermination("APPROVED")

task = "" \
    "The user is looking to buy a new car. " \
    "They want a car that is fuel efficient, has a good safety rating, and is within their budget. " \
    "Please gather additional information about the user's preferences by asking questions. " \
    "Then search the web for cars that fit the user's preferences and suggest appropriate options. " \
    "Once you have found suitable options, pass the control to the user_proxy agent for final approval."

group_chat = RoundRobinGroupChat(
    [assistant_agent, user_proxy, web_search_agent], 
    termination_condition=termination
)

async def main():
    await Console(group_chat.run_stream(task=task))

if __name__ == "__main__":
    api_key = os.getenv("AGENTOPS_API_KEY")

    agentops.init(
        api_key=api_key,
        default_tags=['autogen']
    )
    
    asyncio.run(main())
    agentops.end_session("Success")


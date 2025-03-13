import asyncio
from autogen_ext.models.openai import  AzureOpenAIChatCompletionClient
from autogen_ext.teams.magentic_one import MagenticOne
from autogen_agentchat.ui import Console
import os
from dotenv import load_dotenv
import agentops

# Load environment variables from .env file
load_dotenv()


async def example_usage():
    client = AzureOpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_version=os.getenv("OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("OPENAI_API_BASE"),
        api_key=os.getenv("OPENAI_API_KEY"), # For key-based authentication.
    )
    m1 = MagenticOne(client=client)
    task = "What was the last thing I asked you?"
    result = await Console(m1.run_stream(task=task))
    print(result)


if __name__ == "__main__":
    api_key = os.getenv("AGENTOPS_API_KEY")

    agentops.init(
        api_key=api_key,
        default_tags=['autogen']
    )

    asyncio.run(example_usage())
    agentops.end_session("Success")


from autogen_agentchat.ui import Console
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.agents.video_surfer import VideoSurfer
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_agentchat.agents import UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
import os
import sys
import asyncio
from dotenv import load_dotenv

from autogen_ext.agents.video_surfer.tools import (
    get_screenshot_at,
    save_screenshot,
    transcribe_video_screenshot,
)

# Load environment variables from .env file
load_dotenv()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Define a model client. You can use other model client that implements
# the `ChatCompletionClient` interface.
model_client = AzureOpenAIChatCompletionClient(
    model="gpt-4o-mini",
    api_version=os.getenv("OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("OPENAI_API_BASE"),
    api_key=os.getenv("OPENAI_API_KEY"), # For key-based authentication.
)

# Define an agent
video_agent = VideoSurfer(
    name="VideoSurfer",
    model_client=model_client,
    )

web_surfer_agent = MultimodalWebSurfer(
    name="MultimodalWebSurfer",
    model_client=model_client,
    )

user_proxy = UserProxyAgent("user_proxy", input_func=input)  # Use input() to get user input from console.

# Create the termination condition which will end the conversation when the user says "APPROVE".
termination = TextMentionTermination("APPROVE")

# Create the team.
team = RoundRobinGroupChat([video_agent, web_surfer_agent, user_proxy], termination_condition=termination)

# Run the agent and stream the messages to the console.
# NOTE: if running this inside a Python script you'll need to use asyncio.run(main()).
async def main() -> None:
    # Run the conversation and stream to the console.
    await team.reset()
    stream = team.run_stream(task="what is happening in the video source/private_assets/video.mp4")
    await Console(stream)

# Run the main function
asyncio.run(main())

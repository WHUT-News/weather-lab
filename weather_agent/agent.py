import os
import wave
from dotenv import load_dotenv
from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from google.adk.tools import ToolContext
from google.genai.types import GenerateContentConfig, AutomaticFunctionCallingConfig

from .sub_agents.forecast_writer.agent import forecast_writer_agent
from .sub_agents.forecast_speaker.agent import forecast_speaker_agent
from .sub_agents.forecast_photographer.agent import forecast_photographer_agent

from .tools import set_session_value, get_current_timestamp

from .forecast_storage_client import (
    get_cached_forecast_from_storage,
    upload_forecast_to_storage,
)

load_dotenv()

async def conditional_upload_forecast(callback_context):
    """
    Upload forecast to storage only if it wasn't retrieved from cache.
    Skips upload if FORECAST_CACHED is True.
    """
    # Check if forecast was retrieved from cache
    if callback_context.state.get("FORECAST_CACHED", False):
        # Skip upload for cached forecasts
        return

    # Upload new forecast to storage
    await upload_forecast_to_storage(callback_context)


weather_media_team = ParallelAgent(
    name="weather_media_team",
    description="A team of agents that work together to produce weather forecast audio and picture.",
    sub_agents=[
        forecast_speaker_agent,
        forecast_photographer_agent,
    ],
)

weather_studio_team = SequentialAgent(
    name="weather_studio_team",
    description="A team of agents that work together to provide current weather information.",
    sub_agents=[
        forecast_writer_agent, 
        weather_media_team
    ],
)


root_agent = Agent(
    name="weather_agent",
    model=os.getenv("MODEL"),
    instruction="""
    You are a weather report agent. Your task is to provide accurate and up-to-date weather forecast in a city.

    Steps to follow:
    1. Ask the user for a city and the type of weather information.
    2. After receiving the user's input for weather info, store the following data in the session before proceeding to next steps:
      * the city in the session with the key 'CITY'
      * the type of weather information in the session with the key 'WEATHER_TYPE'. If you are unsure, default to "current weather condition".
      * the current date and time in the session with the key 'FORECAST_TIMESTAMP'
    3. BEFORE delegating to sub-agents, use get_cached_forecast_from_storage with the city name to check if a recent forecast exists in Cloud SQL.
        - If cached is True:
            * Store the cache status in session with key 'FORECAST_CACHED' as True
            * Store the forecast_at timestamp in session with key 'FORECAST_TIMESTAMP'
            * The forecast_text field contains the weather forecast as text
            * Store the forecast_text in session with key 'FORECAST_TEXT'
            * Store the audio_filepath in session with key 'FORECAST_AUDIO'
            * Store the picture_filepath in session with key 'FORECAST_PICTURE'
            * SKIP calling weather_studio_team entirely - you already have everything!
            * Inform the user the weather info (mention cache age in minutes, if useful)
        - If cached is False:
            * Delegate the task of producing the weather forecast to the weather_studio_team.
            * After the sub-agents complete, use upload_forecast_to_storage to store the results in Cloud SQL.
    """,
    after_agent_callback=conditional_upload_forecast,
    sub_agents=[weather_studio_team],
    tools=[
        get_current_timestamp,
        set_session_value,
        get_cached_forecast_from_storage,
    ],
)

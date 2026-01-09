import os 
import time
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools import ToolContext

from .tools.get_current_weather import get_current_weather
from ...tools import set_session_value
from ...write_file import write_text_file

load_dotenv()

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

forecast_writer_agent = Agent(
    name="forecast_writer_agent",
    model=os.getenv("MODEL"),
    instruction= f"""You are a professional weather forecaster. Based on the following current weather data for {{CITY}},
        write a friendly and engaging weather forecast announcement. 
        The announcement should be:
        - Conversational and easy to understand
        - About 4-5 sentences long
        - Start with a greeting and mention the city name
        - Describe the current weather conditions (including temperature, humidity, wind speed, etc.)
        - Include practical advice (e.g., "bring an umbrella", "dress warmly")
        - end with 'Brought to you by W-H-U-T Weather Services.'
        - Suitable for text-to-speech conversion

        Steps to follow:
        1. Use the get_current_weather tool to obtain the current weather data.
        2. Use the set_session_value tool to store the generated forecast in the session with the key 'FORECAST_TEXT'.
        3. Use the write_file tool to save the forecast to a text file in the directory named after the city.
        4. Store the file path in the session with the key 'FORECAST_TEXT_FILE'.

        Finally, respond with a confirmation message including the file path where the forecast has been saved.

        Write only the announcement text, nothing else.""",
    
    tools=[get_current_weather, set_session_value, write_text_file],
)
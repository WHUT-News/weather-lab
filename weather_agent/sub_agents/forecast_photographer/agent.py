import os 
from dotenv import load_dotenv
from google.adk.agents import Agent

from .tools.generate_picture import generate_picture
from ...tools import set_session_value

load_dotenv()

forecast_photographer_agent = Agent(
    name="forecast_photographer_agent",
    model=os.getenv("MODEL"),
    instruction= f"""You are a professional photographer. Based on the weather text in {{FORECAST_TEXT}} for {{CITY}},
        You should follow these steps:
         1. Read the weather forecast text stored in the session with the key 'FORECAST_TEXT'.
         2. If the forecast text is missing, set the session value 'FORECAST_PICTURE' to None and then stop.
         3. If the forecast text is present, understand the forecast content and determine an appropriate theme for the picture.
            - The theme options are "cityscape", "sky line", "park", and "famous place of interest".
         4. Based on the text forecast and the theme, generate a realistic image using the generate_picture tool.
         5. Check the result from generate_picture:
            - If successful (status is "success"), store the file path in session with key 'FORECAST_PICTURE'.
            - If failed (status is "error"), store None in session with key 'FORECAST_PICTURE' and inform that the picture generation failed but the weather forecast is still available.
         6. Your task is complete regardless of whether image generation succeeded or failed - the weather forecast can be delivered without a picture.
        """,
    tools=[generate_picture, set_session_value],
)

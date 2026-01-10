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
         2. Understand the forecast content and select an appropriate theme to make the announcement engaging and suitable for the weather conditions.
         3. Convert the text forecast into a realistic image using the generate_picture tool.
         4. Check the result from generate_picture:
            - If successful (status is "success"), store the file path in session with key 'FORECAST_PICTURE'.
            - If failed (status is "error"), store None in session with key 'FORECAST_PICTURE' and inform that the picture generation failed but the weather forecast is still available.
         5. Your task is complete regardless of whether image generation succeeded or failed - the weather forecast can be delivered without a picture.
        """,
    tools=[generate_picture, set_session_value],
)

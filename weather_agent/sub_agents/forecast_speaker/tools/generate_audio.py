import os
import time
from dotenv import load_dotenv

from google import genai
from google.genai import types
from google.adk.tools import ToolContext

from ....write_file import write_audio_file

load_dotenv()

def generate_audio(tool_context: ToolContext, city_name: str, tone: str="cheerfully") -> dict[str, str]:
    # Generate docstring to explain the function
    """Generates an audio file from the given text content using text-to-speech synthesis.
    
    The audio file is saved locally and the file path is stored in session state
    for upload to Cloud SQL storage by the weather agent.
    
        Args:
            tool_context (ToolContext): The tool context containing session state
            city_name (str): The name of the city for which the forecast is being made
            tone (str): The tone in which the content should be spoken. Default is "cheerfully".
        Return:
            dict[str, str]: A dictionary containing the status and file path of the generated audio file.
    """
    content = tool_context.state.get("FORECAST_TEXT", "No forecast available at this moment. Please try again later.")

    client = genai.Client()

    response = client.models.generate_content(
        model=os.getenv("TTS_MODEL"),
        contents=f"Say in the {tone} tone: {content}",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name='Kore',
                    ),
                ),
            ),
        ),
    )

    audio_data = response.candidates[0].content.parts[0].inline_data.data

    result = write_audio_file(tool_context, city_name, audio_data)

    return result

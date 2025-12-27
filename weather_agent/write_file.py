import os
import time
import base64
from dotenv import load_dotenv

from google import genai
from google.genai import types
from google.adk.tools import ToolContext
import wave

from .tools import get_current_timestamp

load_dotenv()

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

# Set up the wave file to save the output:
def _save_wave_file(file_path, pcm, channels=1, rate=24000, sample_width=2):
   with wave.open(file_path, "wb") as wf:
      wf.setnchannels(channels)
      wf.setsampwidth(sample_width)
      wf.setframerate(rate)
      wf.writeframes(pcm)
      
def write_audio_file(tool_context: ToolContext, city_name: str, audio_data) -> dict[str, str]:
    """
    Write the forecast text stored in the session to a text file.
    Args:
        tool_context: The tool context containing session state
        city_name: The name of the city for which the forecast is being made
        audio_data: Base64-encoded audio data string or bytes to write to file
    Returns:
        dict[str, str]: A dictionary containing the status and the file_path of the saved text file.
    """

    # expand the current timestamp to the file name
    forecast_timestamp = tool_context.state.get("FORECAST_TIMESTAMP", get_current_timestamp())
    file_name = f"forecast_audio_{forecast_timestamp}.wav"

    # Save to local OUTPUT_DIR as temporary storage
    # File will be uploaded to Cloud SQL by the weather agent
    directory = os.path.join(OUTPUT_DIR, city_name)
    if not os.path.exists(directory):
        os.makedirs(directory)

    file_path = os.path.join(directory, file_name)

    # Decode base64 string to bytes if needed
    if isinstance(audio_data, str):
        audio_bytes = base64.b64decode(audio_data)
    else:
        audio_bytes = audio_data

    _save_wave_file(file_path, audio_bytes) # Saves the file to the specified directory

    # Store audio file path in session state for agent to use in upload
    tool_context.state["FORECAST_AUDIO"] = file_path

    return {"status": "success", "file_path": file_path}


def write_text_file(tool_context: ToolContext, city_name: str) -> dict[str, str]:
    """
    Write the forecast text stored in the session to a text file.
    Args:
        tool_context: The tool context containing session state
        city_name: The name of the city for which the forecast is being made
    Returns:
        dict[str, str]: A dictionary containing the status and the file_path of the saved text file.
    """

    content = tool_context.state.get("FORECAST_TEXT", "No forecast available at this moment. Please try again later.")

    # expand the current timestamp to the file name
    forecast_timestamp = tool_context.state.get("FORECAST_TIMESTAMP", get_current_timestamp())
    file_name = f"forecast_text_{forecast_timestamp}.txt"

    directory = os.path.join(OUTPUT_DIR, city_name)
    if not os.path.exists(directory):
        os.makedirs(directory)

    file_path = os.path.join(directory, file_name)
    with open(file_path, "w") as f:
        f.write(content)

    return {"status": "success", "file_path": file_path}

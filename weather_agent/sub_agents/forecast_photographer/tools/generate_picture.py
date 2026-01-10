import os
import time
from dotenv import load_dotenv

import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from google.api_core.exceptions import GoogleAPIError
from google.adk.tools import ToolContext

from ....write_file import write_picture_file

load_dotenv()

def generate_picture(tool_context: ToolContext, city_name: str, theme: str="city skyline") -> dict[str, str]:
    # Generate docstring to explain the function
    """Generates a picture from the given text content using image generation.

    The picture file is saved locally and the file path is stored in session state
    for upload to Cloud SQL storage by the weather agent.

        Args:
            tool_context (ToolContext): The tool context containing session state
            city_name (str): The name of the city for which the forecast is being made
            theme (str): The theme for the generated picture. Default is "city skyline".
        Return:
            dict[str, str]: A dictionary containing the status and file path of the generated picture file.
    """
    content = tool_context.state.get("FORECAST_TEXT", "No forecast available at this moment. Please try again later.")

    try:
        # Initialize Vertex AI
        vertexai.init(
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        )

        # Load the Imagen model
        model = ImageGenerationModel.from_pretrained(os.getenv("IMG_MODEL", "imagen-4.0-generate-001"))

        # Generate the image
        prompt = f"Generate a picture of a {theme} for the city of {city_name} based on this weather forecast: {content}"

        images = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio=os.getenv("IMG_ASPECT_RATIO", "16:9"),
        )

        # Get the first generated image
        generated_image = images[0]
        image_data = generated_image._image_bytes

        result = write_picture_file(tool_context, city_name, image_data)

        return result

    except GoogleAPIError as e:
        # Handle quota exceeded and other API errors gracefully
        if e.code == 429:
            error_msg = f"Image generation quota exceeded. Weather forecast is available without the picture."
        else:
            error_msg = f"Image generation failed: {str(e)}"

        return {
            "status": "error",
            "message": error_msg,
            "file_path": None
        }

    except Exception as e:
        # Handle any other unexpected errors
        return {
            "status": "error",
            "message": f"Unexpected error during image generation: {str(e)}",
            "file_path": None
        }

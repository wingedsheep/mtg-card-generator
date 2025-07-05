import os
import replicate
from io import BytesIO
from pathlib import Path
from PIL import Image

import os
import replicate
from io import BytesIO
from pathlib import Path
from PIL import Image

from image_generation_strategies import ImageGeneratorStrategy
from tools.huggingface_diffusers_tool import HuggingFaceDiffusersTool
from models import Card, Config
from typing import Any, Dict

class ReplicateImageGenerator(ImageGeneratorStrategy):
    def __init__(self, global_config: Any, strategy_specific_config: Dict):
        print("[DEBUG ReplicateImageGenerator] __init__ called") # DEBUG
        super().__init__(global_config, strategy_specific_config)
        print("[DEBUG ReplicateImageGenerator] super().__init__ finished") # DEBUG

    def _initialize_client_if_needed(self):
        # This overrides the base class's method, so super call in __init__ will call this one.
        print("[DEBUG ReplicateImageGenerator] _initialize_client_if_needed called") # DEBUG
        api_key = self.global_config.get_api_key("replicate")
        print(f"[DEBUG ReplicateImageGenerator] API key from config: {api_key}") # DEBUG
        if not api_key:
            # print("[DEBUG ReplicateImageGenerator] API key is None or empty, raising ValueError") # DEBUG
            raise ValueError("Replicate API key not found in settings.json.")
        os.environ["REPLICATE_API_TOKEN"] = api_key
        print(f"[DEBUG ReplicateImageGenerator] REPLICATE_API_TOKEN set to: {os.environ.get('REPLICATE_API_TOKEN')}") # DEBUG

    def generate_image(self, art_prompt: str, card: Any, output_dir: Path, image_name: str) -> str:
        selected_model_type = self.strategy_specific_config.get("selected_model_type", "flux")
        model_info = self.strategy_specific_config.get("models", {}).get(selected_model_type)

        if not model_info:
            raise ValueError(f"Configuration for Replicate model type '{selected_model_type}' not found.")

        model_id = model_info.get("id")
        model_params_config = model_info.get("params", {})

        if not model_id:
            raise ValueError(f"Model ID for Replicate model type '{selected_model_type}' not found.")

        # Prepare parameters for Replicate API
        api_params = {"prompt": art_prompt}

        is_saga = "Saga" in card.type
        if is_saga:
            api_params["aspect_ratio"] = model_params_config.get("aspect_ratio_saga", "9:16") # Default for sagas
        else:
            api_params["aspect_ratio"] = model_params_config.get("aspect_ratio_standard", "5:4") # Default for standard

        # Add other specific params from config
        for key, value in model_params_config.items():
            if key not in ["aspect_ratio_standard", "aspect_ratio_saga"]:
                api_params[key] = value

        print(f"Generating image with Replicate model: {model_id}, params: {api_params}")

        try:
            image_response_url = replicate.run(model_id, input=api_params)

            if not image_response_url: # Check if response is empty or None
                raise Exception("Replicate returned an empty response.")

            # Assuming image_response_url is a URL to the image
            # If it can be a list, take the first element:
            if isinstance(image_response_url, list):
                if not image_response_url:
                    raise Exception("Replicate returned an empty list of images.")
                image_response_url = image_response_url[0]


            import requests
            image_data = requests.get(image_response_url).content

            # Cropping logic (simplified, can be enhanced based on exact needs and strategy_specific_config.cropping)
            cropping_config = self.strategy_specific_config.get("cropping", {})
            final_image_data = image_data

            pil_image = Image.open(BytesIO(image_data))
            original_width, original_height = pil_image.size

            # Determine target aspect ratio for potential cropping
            target_ratio_val = None
            if is_saga and cropping_config.get("crop_to_4x5_saga"):
                target_ratio_val = 4/5
            elif not is_saga and cropping_config.get("crop_to_5x4_standard"):
                target_ratio_val = 5/4

            if target_ratio_val:
                current_ratio = original_width / original_height
                if abs(current_ratio - target_ratio_val) > 0.01: # If not already target ratio
                    if current_ratio > target_ratio_val: # Image is wider than target
                        new_width = int(original_height * target_ratio_val)
                        left = (original_width - new_width) // 2
                        pil_image = pil_image.crop((left, 0, left + new_width, original_height))
                    else: # Image is taller than target
                        new_height = int(original_width / target_ratio_val)
                        top = (original_height - new_height) // 2
                        pil_image = pil_image.crop((0, top, original_width, top + new_height))

                    output_bytes = BytesIO()
                    pil_image.save(output_bytes, format=pil_image.format or 'PNG')
                    final_image_data = output_bytes.getvalue()
                    print(f"Cropped image to target aspect ratio: {'4:5' if is_saga else '5:4'}")


            image_file_path = output_dir / self.global_config.get_image_generation_config().get("default_output_dir_name", "card_images") / image_name
            self._ensure_output_dir_exists(image_file_path)

            with open(image_file_path, "wb") as f:
                f.write(final_image_data)

            print(f"Image saved to {image_file_path}")
            return str(image_file_path)

        except Exception as e:
            print(f"Error generating image with Replicate: {e}")
            raise


class HuggingFaceDiffusersImageGenerator(ImageGeneratorStrategy):
    def __init__(self, global_config: Any, strategy_specific_config: Dict):
        super().__init__(global_config, strategy_specific_config)
        # Tool is initialized here, using its specific config block
        self.tool = HuggingFaceDiffusersTool(
            model_id=self.strategy_specific_config.get("model_id", "runwayml/stable-diffusion-v1-5"),
            device=self.strategy_specific_config.get("device", "cuda")
        )

    def generate_image(self, art_prompt: str, card: Any, output_dir: Path, image_name: str) -> str:
        params = self.strategy_specific_config.get("params", {}).copy() # Get common params like steps, scale
        dimensions_config = self.strategy_specific_config.get("dimensions", {})

        is_saga = "Saga" in card.type
        if is_saga:
            params["width"] = dimensions_config.get("saga_width", 512)
            params["height"] = dimensions_config.get("saga_height", 768)
        else:
            params["width"] = dimensions_config.get("standard_width", 512)
            params["height"] = dimensions_config.get("standard_height", 512)

        image_subdir = self.global_config.get_image_generation_config().get("default_output_dir_name", "card_images")
        full_output_dir_for_tool = output_dir / image_subdir

        # The tool itself handles os.makedirs for its output_dir argument
        saved_image_path = self.tool.generate_image(
            prompt=art_prompt,
            output_dir=str(full_output_dir_for_tool), # Tool expects string path
            image_name=image_name,
            num_inference_steps=params.get("num_inference_steps", 50),
            guidance_scale=params.get("guidance_scale", 7.5),
            height=params["height"],
            width=params["width"]
        )
        print(f"Image generated with Diffusers and saved to {saved_image_path}")
        return saved_image_path

# Utility for cropping, can be moved to a utils file if preferred
def crop_image_bytes(image_data_bytes: bytes, target_aspect_ratio: float, is_saga: bool) -> bytes:
    """Crops image bytes to a target aspect ratio."""
    image = Image.open(BytesIO(image_data_bytes))
    width, height = image.size
    current_ratio = width / height

    if abs(current_ratio - target_aspect_ratio) < 0.01: # Already close
        return image_data_bytes

    if current_ratio > target_aspect_ratio: # Image is wider
        new_width = int(height * target_aspect_ratio)
        left = (width - new_width) // 2
        cropped_image = image.crop((left, 0, left + new_width, height))
    else: # Image is taller
        new_height = int(width / target_aspect_ratio)
        top = (height - new_height) // 2
        cropped_image = image.crop((0, top, width, top + new_height))

    output_buffer = BytesIO()
    cropped_image.save(output_buffer, format=image.format or 'PNG')
    print(f"Image cropped to {'Saga' if is_saga else 'Standard'} aspect ratio: {target_aspect_ratio:.2f}")
    return output_buffer.getvalue()

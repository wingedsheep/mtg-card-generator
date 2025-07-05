import torch
from diffusers import StableDiffusionPipeline
from PIL import Image
import os

class HuggingFaceDiffusersTool:
    def __init__(self, model_id: str = "runwayml/stable-diffusion-v1-5", device: str = "cuda"):
        """
        Initializes the HuggingFaceDiffusersTool.

        Args:
            model_id (str): The ID of the pre-trained model to use from Hugging Face Model Hub.
            device (str): The device to run the model on ("cuda" or "cpu").
        """
        self.model_id = model_id
        self.device = device
        if self.device == "cuda" and not torch.cuda.is_available():
            print("CUDA is not available. Falling back to CPU.")
            self.device = "cpu"

        print(f"Loading model {self.model_id} on {self.device}...")
        self.pipe = StableDiffusionPipeline.from_pretrained(self.model_id)
        self.pipe = self.pipe.to(self.device)
        print("Model loaded successfully.")

    def generate_image(self, prompt: str, output_dir: str = "generated_images",
                       image_name: str = "generated_image.png",
                       num_inference_steps: int = 50, guidance_scale: float = 7.5,
                       height: int = 512, width: int = 512) -> str:
        """
        Generates an image based on the given prompt.

        Args:
            prompt (str): The text prompt to generate the image from.
            output_dir (str): The directory to save the generated image.
            image_name (str): The name of the saved image file.
            num_inference_steps (int): The number of denoising steps.
            guidance_scale (float): Classifier-free guidance scale.
            height (int): The height in pixels of the generated image.
            width (int): The width in pixels of the generated image.

        Returns:
            str: The path to the saved image.
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        print(f"Generating image for prompt: '{prompt}'...")
        image = self.pipe(
            prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            height=height,
            width=width
        ).images[0]

        image_path = os.path.join(output_dir, image_name)
        image.save(image_path)
        print(f"Image saved to {image_path}")

        return image_path

if __name__ == '__main__':
    # This is an example of how to use the tool.
    # It will not run in the current sandbox environment due to installation issues.

    # print("Attempting to initialize HuggingFaceDiffusersTool...")
    # try:
    #     diffusers_tool = HuggingFaceDiffusersTool()
    #     print("Tool initialized.")

    #     prompt = "A fantasy landscape with mountains and a river"
    #     output_directory = "example_generated_art"
    #     file_name = "fantasy_landscape.png"

    #     print(f"Generating image with prompt: '{prompt}'")
    #     image_path = diffusers_tool.generate_image(
    #         prompt,
    #         output_dir=output_directory,
    #         image_name=file_name
    #     )
    #     print(f"Example image generated and saved to: {image_path}")

    # except Exception as e:
    #     print(f"Could not run HuggingFaceDiffusersTool example: {e}")
    #     print("This is expected in the current environment due to library installation issues.")
    pass

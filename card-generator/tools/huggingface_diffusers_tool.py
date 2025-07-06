import torch
from diffusers import StableDiffusionPipeline
from pathlib import Path


class HuggingFaceDiffusersTool:
    def __init__(self, model_id: str = "runwayml/stable-diffusion-v1-5", device: str = "cuda"):
        """
        Initialize the Hugging Face Diffusers tool.

        Args:
            model_id: The model identifier from Hugging Face Hub
            device: Device to run inference on (cuda/cpu)
        """
        self.model_id = model_id
        self.device = device
        self.pipe = None
        self._initialize_pipeline()

    def _initialize_pipeline(self):
        """Initialize the diffusion pipeline."""
        try:
            # Load pipeline with safety checker disabled to prevent None returns
            self.pipe = StableDiffusionPipeline.from_pretrained(
                self.model_id,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                safety_checker=None,
                feature_extractor=None,
                requires_safety_checker=False
            )

            self.pipe = self.pipe.to(self.device)

            if self.device == "cuda":
                try:
                    self.pipe.enable_attention_slicing()
                except:
                    pass

            print(f"Successfully initialized Diffusers pipeline with model: {self.model_id}")

        except Exception as e:
            print(f"Error initializing Diffusers pipeline: {e}")
            raise

    def generate_image(self,
                       prompt: str,
                       output_dir: str,
                       image_name: str,
                       num_inference_steps: int = 50,
                       guidance_scale: float = 7.5,
                       height: int = 512,
                       width: int = 512) -> str:
        """
        Generate an image using the diffusion pipeline.

        Args:
            prompt: Text prompt for image generation (max 77 tokens)
            output_dir: Directory to save the generated image
            image_name: Name for the output image file
            num_inference_steps: Number of denoising steps
            guidance_scale: How closely to follow the prompt
            height: Image height in pixels
            width: Image width in pixels

        Returns:
            str: Path to the saved image file
        """
        if self.pipe is None:
            raise RuntimeError("Pipeline not initialized.")

        # Ensure output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        try:
            print(f"Generating image with prompt: '{prompt}'\n")

            # Generate the image
            with torch.no_grad():
                result = self.pipe(
                    prompt=prompt,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    height=height,
                    width=width
                )

            # Extract the image from the result
            if hasattr(result, 'images') and result.images and result.images[0] is not None:
                image = result.images[0]
            else:
                raise RuntimeError("Pipeline returned no images or None image.")

            # Save the image
            if not image_name.endswith('.png'):
                image_name += '.png'

            image_path = output_path / image_name
            image.save(image_path)

            print(f"Successfully generated and saved image to: {image_path}")
            return str(image_path)

        except Exception as e:
            print(f"Error generating image: {e}")
            raise

    def clear_cache(self):
        """Clear GPU cache to free memory."""
        if self.device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()

    def __del__(self):
        """Cleanup when object is destroyed."""
        self.clear_cache()

# Clean image_generation_strategies_impl.py - Complete Solution
import os
import gc
import torch
import numpy as np
from io import BytesIO
from pathlib import Path
from PIL import Image
from typing import Any, Dict, Optional

from image_generation_strategies import ImageGeneratorStrategy

# Optional imports for Diffusers - will be checked at runtime
try:
    from diffusers import DiffusionPipeline, AutoPipelineForText2Image, AutoencoderKL

    DIFFUSERS_AVAILABLE = True
except ImportError:
    DIFFUSERS_AVAILABLE = False

# Optional import for Replicate
try:
    import replicate

    REPLICATE_AVAILABLE = True
except ImportError:
    REPLICATE_AVAILABLE = False


class ReplicateImageGenerator(ImageGeneratorStrategy):
    def __init__(self, global_config: Any, strategy_specific_config: Dict):
        print("[DEBUG ReplicateImageGenerator] __init__ called")
        super().__init__(global_config, strategy_specific_config)
        print("[DEBUG ReplicateImageGenerator] super().__init__ finished")

    def _initialize_client_if_needed(self):
        if not REPLICATE_AVAILABLE:
            raise ImportError("Replicate library is not installed. Please install it with: pip install replicate")

        print("[DEBUG ReplicateImageGenerator] _initialize_client_if_needed called")
        api_key = self.global_config.get_api_key("replicate")
        print(f"[DEBUG ReplicateImageGenerator] API key from config: {api_key}")
        if not api_key:
            raise ValueError("Replicate API key not found in settings.json.")
        os.environ["REPLICATE_API_TOKEN"] = api_key
        print(f"[DEBUG ReplicateImageGenerator] REPLICATE_API_TOKEN set to: {os.environ.get('REPLICATE_API_TOKEN')}")

    def generate_image(self, art_prompt: str, card: Any, output_dir: Path, image_name: str) -> str:
        selected_model_type = self.strategy_config.get("selected_model_type", "flux")
        model_info = self.strategy_config.get("models", {}).get(selected_model_type)

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
            api_params["aspect_ratio"] = model_params_config.get("aspect_ratio_saga", "9:16")
        else:
            api_params["aspect_ratio"] = model_params_config.get("aspect_ratio_standard", "5:4")

        # Add other specific params from config
        for key, value in model_params_config.items():
            if key not in ["aspect_ratio_standard", "aspect_ratio_saga"]:
                api_params[key] = value

        print(f"Generating image with Replicate model: {model_id}, params: {api_params}")

        try:
            image_response_url = replicate.run(model_id, input=api_params)

            if not image_response_url:
                raise Exception("Replicate returned an empty response.")

            # Handle list response
            if isinstance(image_response_url, list):
                if not image_response_url:
                    raise Exception("Replicate returned an empty list of images.")
                image_response_url = image_response_url[0]

            import requests
            image_data = requests.get(image_response_url).content

            # Apply cropping if configured
            final_image_data = self._apply_cropping(image_data, card, is_saga)

            # Save the image
            image_file_path = self._get_image_save_path(output_dir, image_name)
            self._ensure_output_dir_exists(image_file_path)

            with open(image_file_path, "wb") as f:
                f.write(final_image_data)

            print(f"Image saved to {image_file_path}")
            return str(image_file_path)

        except Exception as e:
            print(f"Error generating image with Replicate: {e}")
            raise

    def _apply_cropping(self, image_data: bytes, card: Any, is_saga: bool) -> bytes:
        """Apply cropping based on configuration."""
        cropping_config = self.strategy_config.get("cropping", {})

        pil_image = Image.open(BytesIO(image_data))
        original_width, original_height = pil_image.size

        # Determine target aspect ratio for potential cropping
        target_ratio_val = None
        if is_saga and cropping_config.get("crop_to_4x5_saga"):
            target_ratio_val = 4 / 5
        elif not is_saga and cropping_config.get("crop_to_5x4_standard"):
            target_ratio_val = 5 / 4

        if target_ratio_val:
            current_ratio = original_width / original_height
            if abs(current_ratio - target_ratio_val) > 0.01:
                if current_ratio > target_ratio_val:  # Image is wider than target
                    new_width = int(original_height * target_ratio_val)
                    left = (original_width - new_width) // 2
                    pil_image = pil_image.crop((left, 0, left + new_width, original_height))
                else:  # Image is taller than target
                    new_height = int(original_width / target_ratio_val)
                    top = (original_height - new_height) // 2
                    pil_image = pil_image.crop((0, top, original_width, top + new_height))

                output_bytes = BytesIO()
                pil_image.save(output_bytes, format=pil_image.format or 'PNG')
                print(f"Cropped image to target aspect ratio: {'4:5' if is_saga else '5:4'}")
                return output_bytes.getvalue()

        return image_data

    def _get_image_save_path(self, output_dir: Path, image_name: str) -> Path:
        """Get the full path where the image should be saved."""
        image_subdir = self.global_config.get_image_generation_config().get("default_output_dir_name", "card_images")
        return output_dir / image_subdir / image_name


class HuggingFaceDiffusersImageGenerator(ImageGeneratorStrategy):
    def __init__(self, global_config: Any, strategy_specific_config: Dict):
        # Store strategy config early
        self.strategy_config = strategy_specific_config

        # Initialize basic attributes
        self.pipeline = None
        self.device = self._get_optimal_device()
        self.dtype = self._get_optimal_dtype()

        # Call parent constructor
        super().__init__(global_config, strategy_specific_config)
        print(f"Diffusers generator initialized - Device: {self.device}, Dtype: {self.dtype}")

    def _get_optimal_device(self) -> str:
        """Determine the best device to use."""
        device_config = self.strategy_config.get("device", "auto")

        if device_config == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        else:
            return device_config

    def _get_optimal_dtype(self) -> torch.dtype:
        """Determine the best dtype to use."""
        dtype_config = self.strategy_config.get("dtype", "auto")

        if dtype_config == "float32":
            return torch.float32
        elif dtype_config == "float16":
            return torch.float16
        elif dtype_config == "auto":
            # For maximum compatibility, use float32 by default
            # This prevents most dtype mismatch issues
            return torch.float32
        else:
            return torch.float32

    def _initialize_client_if_needed(self):
        """Initialize the Diffusers pipeline with proper dtype consistency."""
        if not DIFFUSERS_AVAILABLE:
            raise ImportError(
                "Diffusers library is not installed. Please install it with: "
                "pip install diffusers[torch] transformers scipy ftfy accelerate"
            )

        model_id = self.strategy_config.get("model_id", "runwayml/stable-diffusion-v1-5")

        try:
            print(f"Loading Diffusers model: {model_id}")
            print(f"Using dtype: {self.dtype}")

            # Strategy 1: Load everything in the same dtype for consistency
            if self.dtype == torch.float32:
                # Load everything in FP32 for maximum stability
                self.pipeline = DiffusionPipeline.from_pretrained(
                    model_id,
                    torch_dtype=torch.float32,
                    use_safetensors=True,
                )
                print("Loaded pipeline in FP32")

            else:
                # Load in FP16 but with safety measures
                try:
                    self.pipeline = DiffusionPipeline.from_pretrained(
                        model_id,
                        torch_dtype=torch.float16,
                        use_safetensors=True,
                        variant="fp16"
                    )
                    print("Loaded pipeline in FP16 with variant")
                except:
                    # Fallback: load in FP16 without variant
                    print("FP16 variant not available, loading default model in FP16")
                    self.pipeline = DiffusionPipeline.from_pretrained(
                        model_id,
                        torch_dtype=torch.float16,
                        use_safetensors=True,
                    )

            # Disable safety checker
            if hasattr(self.pipeline, 'safety_checker'):
                self.pipeline.safety_checker = None
            if hasattr(self.pipeline, 'requires_safety_checker'):
                self.pipeline.requires_safety_checker = False

            # Move entire pipeline to device with consistent dtype
            self.pipeline = self.pipeline.to(self.device, dtype=self.dtype)
            print(f"Pipeline moved to {self.device} with dtype {self.dtype}")

            # Enable memory optimizations
            if hasattr(self.pipeline, 'enable_attention_slicing'):
                self.pipeline.enable_attention_slicing()
                print("Attention slicing enabled")

            # Enable memory efficient attention if available
            try:
                self.pipeline.enable_xformers_memory_efficient_attention()
                print("xFormers memory efficient attention enabled")
            except:
                print("xFormers not available, skipping")

            # For low memory systems, enable CPU offload
            enable_cpu_offload = self.strategy_config.get("enable_cpu_offload", False)
            if enable_cpu_offload and hasattr(self.pipeline, 'enable_model_cpu_offload'):
                self.pipeline.enable_model_cpu_offload()
                print("Model CPU offload enabled")

            # For very low memory systems, enable sequential CPU offload
            enable_sequential = self.strategy_config.get("enable_sequential_cpu_offload", False)
            if enable_sequential and hasattr(self.pipeline, 'enable_sequential_cpu_offload'):
                self.pipeline.enable_sequential_cpu_offload()
                print("Sequential CPU offload enabled")

            print("Pipeline initialization successful")

        except Exception as e:
            print(f"Error loading Diffusers model: {e}")
            raise

    def generate_image(self, art_prompt: str, card: Any, output_dir: Path, image_name: str) -> str:
        """Generate an image using the Diffusers pipeline."""
        if self.pipeline is None:
            raise RuntimeError("Pipeline not initialized")

        # Get generation parameters
        params = self._get_generation_params(card)
        params["prompt"] = art_prompt

        print(f"Generating image with Diffusers...")
        print(f"Prompt: {art_prompt[:100]}...")
        print(f"Parameters: {params}")

        try:
            with torch.inference_mode():
                # Generate image
                result = self.pipeline(**params)

            # Extract image from result
            if hasattr(result, 'images') and result.images:
                image = result.images[0]
            elif isinstance(result, list) and len(result) > 0:
                image = result[0]
            else:
                raise RuntimeError("Pipeline returned unexpected result format")

            # Verify image is valid
            if image is None:
                raise RuntimeError("Pipeline returned None image")

            # Check if image is black (common sign of generation issues)
            if isinstance(image, Image.Image):
                img_array = np.array(image)
                if np.all(img_array == 0):
                    print("Warning: Generated image is completely black")
                    # Create a simple gray placeholder
                    width = params.get("width", 512)
                    height = params.get("height", 512)
                    image = Image.new('RGB', (width, height), color=(128, 128, 128))
                    print("Created gray placeholder image")

            # Save the image
            image_file_path = self._get_image_save_path(output_dir, image_name)
            self._ensure_output_dir_exists(image_file_path)

            image.save(image_file_path, "PNG", optimize=True)
            print(f"Image saved to {image_file_path}")

            # Clean up memory
            if self.device != "cpu":
                torch.cuda.empty_cache()
                gc.collect()

            return str(image_file_path)

        except Exception as e:
            print(f"Error generating image with Diffusers: {e}")
            # Clean up on error
            if self.device != "cpu":
                torch.cuda.empty_cache()
                gc.collect()
            raise

    def _get_generation_params(self, card: Any) -> Dict[str, Any]:
        """Get parameters for image generation."""
        params = self.strategy_config.get("params", {}).copy()
        dimensions_config = self.strategy_config.get("dimensions", {})

        is_saga = "Saga" in card.type

        # Set dimensions
        if is_saga:
            params["width"] = dimensions_config.get("saga_width", 512)
            params["height"] = dimensions_config.get("saga_height", 768)
        else:
            params["width"] = dimensions_config.get("standard_width", 512)
            params["height"] = dimensions_config.get("standard_height", 512)

        # Ensure dimensions are multiples of 8
        params["width"] = (params["width"] // 8) * 8
        params["height"] = (params["height"] // 8) * 8

        # Set default parameters
        params.setdefault("num_inference_steps", 20)
        params.setdefault("guidance_scale", 7.5)
        params.setdefault("negative_prompt", "blurry, low quality, distorted, deformed")

        # Handle generator for reproducibility
        if "seed" in params:
            generator = torch.Generator(device=self.device).manual_seed(params.pop("seed"))
            params["generator"] = generator

        return params

    def _get_image_save_path(self, output_dir: Path, image_name: str) -> Path:
        """Get the full path where the image should be saved."""
        image_subdir = self.global_config.get_image_generation_config().get("default_output_dir_name", "card_images")
        return output_dir / image_subdir / image_name

    def __del__(self):
        """Cleanup when destroyed."""
        if hasattr(self, 'pipeline') and self.pipeline is not None:
            del self.pipeline
            if hasattr(self, 'device') and self.device != "cpu":
                torch.cuda.empty_cache()
                gc.collect()
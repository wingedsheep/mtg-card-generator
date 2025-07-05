import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the Python path to allow importing the tool
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock torch and diffusers before attempting to import the tool
# This is necessary because these libraries are not installed in the test environment
mock_torch = MagicMock()
sys.modules['torch'] = mock_torch
sys.modules['torch.cuda'] = MagicMock()
mock_torch.cuda.is_available = MagicMock(return_value=False) # Simulate no CUDA

mock_diffusers = MagicMock()
sys.modules['diffusers'] = mock_diffusers
mock_pipeline = MagicMock()
mock_diffusers.StableDiffusionPipeline.from_pretrained = MagicMock(return_value=mock_pipeline)
mock_image = MagicMock()
mock_pipeline.return_value.images = [mock_image]


from tools.huggingface_diffusers_tool import HuggingFaceDiffusersTool

class TestHuggingFaceDiffusersTool(unittest.TestCase):

    @patch('tools.huggingface_diffusers_tool.StableDiffusionPipeline.from_pretrained')
    @patch('tools.huggingface_diffusers_tool.torch.cuda.is_available', return_value=False) # Ensure CPU is chosen
    def test_initialization_cpu(self, mock_cuda_available, mock_from_pretrained):
        """Test tool initialization on CPU."""
        mock_pipe_instance = MagicMock()
        mock_from_pretrained.return_value = mock_pipe_instance

        tool = HuggingFaceDiffusersTool(model_id="test-model-cpu", device="cpu")

        mock_from_pretrained.assert_called_once_with("test-model-cpu")
        mock_pipe_instance.to.assert_called_once_with("cpu")
        self.assertEqual(tool.device, "cpu")
        print("TestHuggingFaceDiffusersTool: test_initialization_cpu passed.")

    @patch('tools.huggingface_diffusers_tool.StableDiffusionPipeline.from_pretrained')
    @patch('tools.huggingface_diffusers_tool.torch.cuda.is_available', return_value=True) # Simulate CUDA available
    def test_initialization_cuda(self, mock_cuda_available, mock_from_pretrained):
        """Test tool initialization on CUDA."""
        mock_pipe_instance = MagicMock()
        mock_from_pretrained.return_value = mock_pipe_instance

        tool = HuggingFaceDiffusersTool(model_id="test-model-cuda", device="cuda")

        mock_from_pretrained.assert_called_once_with("test-model-cuda")
        mock_pipe_instance.to.assert_called_once_with("cuda")
        self.assertEqual(tool.device, "cuda")
        print("TestHuggingFaceDiffusersTool: test_initialization_cuda passed.")

    @patch('tools.huggingface_diffusers_tool.torch.cuda.is_available', return_value=False)
    @patch('tools.huggingface_diffusers_tool.StableDiffusionPipeline.from_pretrained')
    @patch('os.makedirs')
    @patch('PIL.Image.Image') # Mock the Image class from PIL
    def test_generate_image(self, MockPILImage, mock_makedirs, mock_from_pretrained, mock_cuda_available):
        """Test image generation functionality."""
        # Setup mock pipeline and image
        mock_pipe_instance = MagicMock()
        mock_generated_image = MockPILImage() # Instance of the mocked Image class
        mock_pipe_instance.return_value.images = [mock_generated_image]
        mock_from_pretrained.return_value = mock_pipe_instance

        tool = HuggingFaceDiffusersTool(device="cpu") # Force CPU due to mock
        tool.pipe = mock_pipe_instance # Assign the callable mock directly

        prompt = "A test prompt"
        output_dir = "test_output"
        image_name = "test_image.png"

        expected_path = os.path.join(output_dir, image_name)

        # Call the method
        actual_path = tool.generate_image(prompt, output_dir, image_name)

        # Assertions
        mock_makedirs.assert_called_once_with(output_dir)
        tool.pipe.assert_called_once_with(
            prompt,
            num_inference_steps=50,
            guidance_scale=7.5,
            height=512,
            width=512
        )
        mock_generated_image.save.assert_called_once_with(expected_path)
        self.assertEqual(actual_path, expected_path)
        print("TestHuggingFaceDiffusersTool: test_generate_image passed.")

    @patch('tools.huggingface_diffusers_tool.torch.cuda.is_available', return_value=False)
    @patch('tools.huggingface_diffusers_tool.StableDiffusionPipeline.from_pretrained')
    def test_initialization_cuda_fallback_to_cpu(self, mock_from_pretrained, mock_cuda_available):
        """Test fallback to CPU if CUDA is specified but not available."""
        mock_pipe_instance = MagicMock()
        mock_from_pretrained.return_value = mock_pipe_instance

        # mock_cuda_available is already set to False for this test method
        tool = HuggingFaceDiffusersTool(model_id="test-model-fallback", device="cuda")

        mock_from_pretrained.assert_called_once_with("test-model-fallback")
        mock_pipe_instance.to.assert_called_once_with("cpu") # Should fall back to CPU
        self.assertEqual(tool.device, "cpu")
        print("TestHuggingFaceDiffusersTool: test_initialization_cuda_fallback_to_cpu passed.")

if __name__ == '__main__':
    # Pre-mock modules before any potential import by test discovery or runner
    sys.modules['torch'] = mock_torch
    sys.modules['diffusers'] = mock_diffusers
    print("Running HuggingFaceDiffusersTool tests...")
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    print("HuggingFaceDiffusersTool tests finished.")

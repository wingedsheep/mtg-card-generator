import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock ollama before attempting to import the tool
mock_ollama = MagicMock()
sys.modules['ollama'] = mock_ollama

from tools.ollama_tool import OllamaTool

class TestOllamaTool(unittest.TestCase):

    @patch('tools.ollama_tool.ollama.Client')
    def test_initialization(self, MockClient):
        """Test OllamaTool initialization."""
        mock_client_instance = MockClient.return_value
        tool = OllamaTool(host="http://localhost:11434")

        MockClient.assert_called_once_with(host="http://localhost:11434")
        self.assertIsNotNone(tool.client)
        self.assertEqual(tool.client, mock_client_instance)
        print("TestOllamaTool: test_initialization passed.")

    @patch('tools.ollama_tool.ollama.Client')
    def test_list_models_success(self, MockClient):
        """Test listing models successfully."""
        mock_client_instance = MockClient.return_value
        mock_client_instance.list.return_value = {
            'models': [
                {'name': 'llama2:latest', 'size': 12345},
                {'name': 'mistral:latest', 'size': 67890}
            ]
        }
        tool = OllamaTool()
        tool.client = mock_client_instance # Ensure our mock is used

        models = tool.list_models()

        mock_client_instance.list.assert_called_once()
        self.assertEqual(len(models), 2)
        self.assertEqual(models[0]['name'], 'llama2:latest')
        print("TestOllamaTool: test_list_models_success passed.")

    @patch('tools.ollama_tool.ollama.Client')
    def test_list_models_failure(self, MockClient):
        """Test listing models when an exception occurs."""
        mock_client_instance = MockClient.return_value
        mock_client_instance.list.side_effect = Exception("Ollama not running")
        tool = OllamaTool()
        tool.client = mock_client_instance

        models = tool.list_models()

        mock_client_instance.list.assert_called_once()
        self.assertEqual(models, [])
        print("TestOllamaTool: test_list_models_failure passed.")

    @patch('tools.ollama_tool.ollama.Client')
    def test_generate_text_non_streaming(self, MockClient):
        """Test generating text in non-streaming mode."""
        mock_client_instance = MockClient.return_value
        expected_response = {
            'model': 'test-model',
            'created_at': '2023-01-01T00:00:00Z',
            'message': {'role': 'assistant', 'content': 'Generated text here.'},
            'done': True
        }
        mock_client_instance.chat.return_value = expected_response
        tool = OllamaTool()
        tool.client = mock_client_instance

        model_name = "test-model"
        prompt = "Hello, Ollama!"
        system_prompt = "You are a test assistant."

        response = tool.generate_text(model_name, prompt, system_prompt=system_prompt, stream=False)

        mock_client_instance.chat.assert_called_once_with(
            model=model_name,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt}
            ],
            stream=False
        )
        self.assertEqual(response, expected_response)
        print("TestOllamaTool: test_generate_text_non_streaming passed.")

    @patch('tools.ollama_tool.ollama.Client')
    def test_generate_text_streaming(self, MockClient):
        """Test generating text in streaming mode."""
        mock_client_instance = MockClient.return_value

        # Simulate a stream of chunks
        stream_chunks = [
            {'message': {'content': 'Hel'}, 'done': False},
            {'message': {'content': 'lo!'}, 'done': False},
            {'message': {'content': ''}, 'done': True} # Final chunk
        ]
        mock_client_instance.chat.return_value = iter(stream_chunks) # Return an iterator

        tool = OllamaTool()
        tool.client = mock_client_instance

        model_name = "test-stream-model"
        prompt = "Stream this for me."

        response_iterator = tool.generate_text(model_name, prompt, stream=True)

        mock_client_instance.chat.assert_called_once_with(
            model=model_name,
            messages=[{'role': 'user', 'content': prompt}],
            stream=True
        )

        self.assertTrue(hasattr(response_iterator, '__iter__'))
        collected_chunks = list(response_iterator)
        self.assertEqual(len(collected_chunks), 3)
        self.assertEqual(collected_chunks[0]['message']['content'], 'Hel')
        self.assertEqual(collected_chunks[1]['message']['content'], 'lo!')
        print("TestOllamaTool: test_generate_text_streaming passed.")

    @patch('tools.ollama_tool.ollama.Client')
    def test_generate_text_api_error(self, MockClient):
        """Test error handling when Ollama API call fails."""
        mock_client_instance = MockClient.return_value
        mock_client_instance.chat.side_effect = Exception("Model not found")
        tool = OllamaTool()
        tool.client = mock_client_instance

        response = tool.generate_text("nonexistent-model", "A prompt")

        self.assertIsNone(response)
        print("TestOllamaTool: test_generate_text_api_error passed.")


if __name__ == '__main__':
    # Pre-mock 'ollama' before unittest discovery tries to import it
    sys.modules['ollama'] = mock_ollama
    print("Running OllamaTool tests...")
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    print("OllamaTool tests finished.")

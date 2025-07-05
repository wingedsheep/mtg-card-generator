import unittest
from unittest.mock import patch, MagicMock, mock_open
import json

import sys
import os # Added os
from pathlib import Path

# Add card-generator directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from language_model_strategies_impl import OpenRouterLanguageModel, OllamaLanguageModel
from models import Config

# Mock the OllamaTool used by the Ollama strategy
mock_ollama_tool_instance = MagicMock()
mock_ollama_tool_module = MagicMock()
mock_ollama_tool_module.OllamaTool = MagicMock(return_value=mock_ollama_tool_instance)
if 'tools.ollama_tool' not in sys.modules:
    sys.modules['tools.ollama_tool'] = mock_ollama_tool_module

# Mock OpenAI client for OpenRouter
mock_openai_client_instance = MagicMock()
mock_openai_module = MagicMock()
mock_openai_module.OpenAI = MagicMock(return_value=mock_openai_client_instance)
# We need to handle the try-except import in language_model_strategies_impl.py
# One way is to ensure 'openai' is in sys.modules BEFORE OpenRouterLanguageModel is imported by the test
sys.modules['openai'] = mock_openai_module


class TestLanguageModelStrategies(unittest.TestCase):

    def setUp(self):
        self.mock_global_config = MagicMock(spec=Config)
        self.mock_global_config.get_api_key = MagicMock(return_value="dummy_or_key")
        self.mock_global_config.get_api_headers = MagicMock(return_value={"X-Test": "header"})

    @patch.object(mock_openai_client_instance.chat.completions, 'create')
    def test_openrouter_generate_text(self, mock_openai_create):
        """Test OpenRouterLanguageModel generate_text."""
        mock_openai_create.return_value.choices = [MagicMock(message=MagicMock(content="OpenRouter response"))]

        strategy_config = {
            "base_url": "https://openrouter.test/api/v1",
            "models": {"default_main": "or/main-model"},
            "params": {"temperature": 0.5}
        }
        or_strategy = OpenRouterLanguageModel(self.mock_global_config, strategy_config)

        prompt = "Test prompt"
        system_prompt = "System message"
        response = or_strategy.generate_text(prompt, system_prompt=system_prompt, model_key="default_main", custom_arg=1)

        self.assertEqual(response, "OpenRouter response")
        mock_openai_create.assert_called_once_with(
            model="or/main-model",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            extra_headers={"X-Test": "header"},
            temperature=0.5, # From strategy_config.params
            custom_arg=1     # From **kwargs
        )

    @patch.object(mock_openai_client_instance.chat.completions, 'create')
    def test_openrouter_generate_json_response_success(self, mock_openai_create):
        """Test OpenRouterLanguageModel generate_json_response successful parsing."""
        json_string = '{"key": "value", "number": 123}'
        mock_openai_create.return_value.choices = [MagicMock(message=MagicMock(content=f"```json\n{json_string}\n```"))]

        strategy_config = {
            "models": {"default_json": "or/json-model"},
            "json_params": {"temperature": 0.1} # Specific params for JSON
        }
        or_strategy = OpenRouterLanguageModel(self.mock_global_config, strategy_config)

        response = or_strategy.generate_json_response("JSON prompt", model_key="default_json")

        self.assertEqual(response, {"key": "value", "number": 123})
        mock_openai_create.assert_called_once() # Arguments checked by generate_text call internally

    @patch.object(mock_openai_client_instance.chat.completions, 'create')
    def test_openrouter_generate_json_response_failure(self, mock_openai_create):
        """Test OpenRouterLanguageModel generate_json_response parsing failure."""
        mock_openai_create.return_value.choices = [MagicMock(message=MagicMock(content="Not a JSON"))]
        strategy_config = {"models": {"default_json": "or/json-model"}}
        or_strategy = OpenRouterLanguageModel(self.mock_global_config, strategy_config)

        with self.assertRaises(json.JSONDecodeError):
            or_strategy.generate_json_response("JSON prompt")

    @patch.object(mock_ollama_tool_instance, 'generate_text')
    def test_ollama_generate_text(self, mock_ollama_generate_text):
        """Test OllamaLanguageModel generate_text."""
        mock_ollama_generate_text.return_value = {"message": {"content": "Ollama response"}}

        strategy_config = {
            "host": "http://ollama.test:11434",
            "models": {"default_main": "ollama/main-model"},
            "params": {"temperature": 0.6}
        }

        # Reset the mock on the class for this specific test's instantiation
        mock_ollama_tool_module.OllamaTool.reset_mock(return_value=True)
        ollama_strategy = OllamaLanguageModel(self.mock_global_config, strategy_config)
        mock_ollama_tool_module.OllamaTool.assert_called_once_with(host="http://ollama.test:11434")

        prompt = "Ollama test prompt"
        response = ollama_strategy.generate_text(prompt, model_key="default_main", custom_ollama_option="set")

        self.assertEqual(response, "Ollama response")
        mock_ollama_generate_text.assert_called_once_with(
            model_name="ollama/main-model",
            prompt=prompt,
            system_prompt=None,
            stream=False, # Default from strategy_config or hardcoded
            options={"temperature": 0.6, "custom_ollama_option": "set"}
        )

    @patch.object(mock_ollama_tool_instance, 'generate_text')
    def test_ollama_generate_json_response_success(self, mock_ollama_generate_text):
        """Test OllamaLanguageModel generate_json_response successful parsing."""
        json_string = '{"data": "ollama_json"}'
        mock_ollama_generate_text.return_value = {"message": {"content": json_string}}

        strategy_config = {
            "models": {"default_json": "ollama/json-model"},
            "json_params": {"temperature": 0.1} # Ollama specific params for JSON tasks
        }
        ollama_strategy = OllamaLanguageModel(self.mock_global_config, strategy_config)

        response = ollama_strategy.generate_json_response("Ollama JSON prompt", model_key="default_json")

        self.assertEqual(response, {"data": "ollama_json"})
        mock_ollama_generate_text.assert_called_once_with(
            model_name="ollama/json-model",
            prompt="Ollama JSON prompt",
            system_prompt="You are a helpful assistant designed to output JSON.",
            stream=False,
            format="json", # Should be forced by generate_json_response
            options={"temperature": 0.1}
        )

if __name__ == '__main__':
    unittest.main()

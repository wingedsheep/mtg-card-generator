import unittest
from unittest.mock import patch, mock_open, MagicMock
import json
from pathlib import Path

import sys
from pathlib import Path
# project_root = Path(__file__).resolve().parents[2] # /app
# card_generator_module_root = Path(__file__).resolve().parents[1] # /app/card_generator
# if str(project_root) not in sys.path: # Add /app
#     sys.path.insert(0, str(project_root))
# if str(card_generator_module_root) not in sys.path: # Add /app/card_generator
#      sys.path.insert(0, str(card_generator_module_root))

import os # Added os
# Add card-generator directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import Config
from image_generation_strategies import ImageGeneratorStrategy
from language_model_strategies import LanguageModelStrategy

# Mock concrete strategy implementations
# Paths are now direct as 'card_generator' is the root for these imports
if 'image_generation_strategies_impl' not in sys.modules:
    sys.modules['image_generation_strategies_impl'] = MagicMock()
if 'language_model_strategies_impl' not in sys.modules:
    sys.modules['language_model_strategies_impl'] = MagicMock()


class TestConfig(unittest.TestCase):

    def _get_default_mock_settings_data(self):
        return {
            "api_keys": {
                "openrouter": "test_openrouter_key",
                "replicate": "test_replicate_key"
            },
            "api_headers": {"X-Test-Header": "true"},
            "output_directory_base": "test_output",
            "image_generation": {
                "strategy": "replicate",
                "replicate": {"selected_model_type": "flux", "models": {"flux": {"id": "flux_id"}}},
                "diffusers": {"model_id": "diffusers_id"}
            },
            "language_model": {
                "strategy": "openrouter",
                "openrouter": {"models": {"default_main": "or_main_id"}},
                "ollama": {"models": {"default_main": "ollama_main_id"}}
            }
        }

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_settings_success_primary_file(self, mock_file_open, mock_path_exists):
        """Test loading settings from primary settings.json successfully."""
        mock_path_exists.return_value = True # Simulate settings.json exists
        mock_settings_content = self._get_default_mock_settings_data()
        mock_file_open.return_value.read.return_value = json.dumps(mock_settings_content)

        config = Config() # __post_init__ calls _load_settings

        mock_file_open.assert_called_once_with("card-generator/settings.json", 'r')
        self.assertEqual(config.settings_data, mock_settings_content)
        self.assertTrue(Path(config.output_dir).name.startswith(datetime.now().strftime("%Y%m%d")))
        self.assertEqual(config.output_dir.parent.name, "test_output")

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_settings_fallback_to_example(self, mock_file_open, mock_path_exists):
        """Test fallback to settings.example.json if primary is not found."""
        # Simulate settings.json does not exist, but settings.example.json does
        mock_path_exists.side_effect = lambda path: "example" in str(path)

        mock_example_content = self._get_default_mock_settings_data()
        mock_example_content["output_directory_base"] = "example_output" # Differentiate

        # Configure mock_open to return different content based on file path
        def open_side_effect(path, mode):
            if "example" in path:
                m = mock_open(read_data=json.dumps(mock_example_content))()
            else: # This case should ideally not be hit if Path.exists is mocked correctly for primary
                raise FileNotFoundError
            return m
        mock_file_open.side_effect = open_side_effect

        config = Config()

        self.assertEqual(config.settings_data, mock_example_content)
        self.assertEqual(config.output_dir.parent.name, "example_output")


    @patch("pathlib.Path.exists", return_value=False) # Neither file exists
    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_load_settings_no_files_found(self, mock_file_open, mock_path_exists):
        """Test behavior when no settings files are found."""
        with patch('builtins.print') as mock_print: # Suppress print warnings during test
            config = Config()
            self.assertEqual(config.settings_data, {}) # Should default to empty dict
            mock_print.assert_any_call("Critical: Example settings file card-generator/settings.example.json also not found. Application may not function correctly without configuration.")


    def test_getters_with_loaded_data(self):
        """Test getter methods with pre-loaded settings data."""
        config = Config() # __post_init__ will run
        mock_data = self._get_default_mock_settings_data()
        config.settings_data = mock_data # Manually set for this test

        self.assertEqual(config.get_api_key("openrouter"), "test_openrouter_key")
        self.assertEqual(config.get_api_key("nonexistent"), None)
        self.assertEqual(config.get_api_headers(), {"X-Test-Header": "true"})
        self.assertEqual(config.get_image_generation_config(), mock_data["image_generation"])
        self.assertEqual(config.get_language_model_config(), mock_data["language_model"])

    @patch('image_generation_strategies_impl.ReplicateImageGenerator') # Corrected path
    def test_create_image_generator_strategy_replicate(self, MockReplicateStrategy):
        """Test creating Replicate image generation strategy."""
        config = Config()
        settings = self._get_default_mock_settings_data()
        settings["image_generation"]["strategy"] = "replicate"
        config.settings_data = settings

        # Mock the concrete class returned by the factory method
        # Config.py imports image_generation_strategies_impl directly, so we mock that path.
        # The @patch decorator handles replacing the class, so sys.modules manipulation here for the class itself is redundant with @patch.
        # sys.modules['image_generation_strategies_impl'].ReplicateImageGenerator = MockReplicateStrategy

        strategy = config.create_image_generator_strategy()
        # Check that the Patched Class (MockReplicateStrategy) was instantiated
        MockReplicateStrategy.assert_called_once_with(
            global_config=config,
            strategy_specific_config=settings["image_generation"]["replicate"]
        )
        # The returned strategy is an instance of the mock.
        self.assertIsInstance(strategy, MagicMock)

    @patch('image_generation_strategies_impl.HuggingFaceDiffusersImageGenerator') # Corrected path
    def test_create_image_generator_strategy_diffusers(self, MockDiffusersStrategy):
        """Test creating Diffusers image generation strategy."""
        config = Config()
        settings = self._get_default_mock_settings_data()
        settings["image_generation"]["strategy"] = "diffusers"
        config.settings_data = settings

        # @patch handles class replacement, sys.modules manipulation for the class is not needed here.
        # sys.modules['image_generation_strategies_impl'].HuggingFaceDiffusersImageGenerator = MockDiffusersStrategy

        strategy = config.create_image_generator_strategy()
        MockDiffusersStrategy.assert_called_once_with(
            global_config=config,
            strategy_specific_config=settings["image_generation"]["diffusers"]
        )
        self.assertIsInstance(strategy, MagicMock) # Strategy is an instance of the mocked class

    @patch('language_model_strategies_impl.OpenRouterLanguageModel') # Corrected path
    def test_create_language_model_strategy_openrouter(self, MockOpenRouterStrategy):
        """Test creating OpenRouter language model strategy."""
        config = Config()
        settings = self._get_default_mock_settings_data()
        settings["language_model"]["strategy"] = "openrouter"
        config.settings_data = settings

        # @patch handles class replacement
        # sys.modules['language_model_strategies_impl'].OpenRouterLanguageModel = MockOpenRouterStrategy

        strategy = config.create_language_model_strategy()
        MockOpenRouterStrategy.assert_called_once_with(
            global_config=config,
            strategy_specific_config=settings["language_model"]["openrouter"]
        )
        self.assertIsInstance(strategy, MagicMock)

    @patch('language_model_strategies_impl.OllamaLanguageModel') # Corrected path
    def test_create_language_model_strategy_ollama(self, MockOllamaStrategy):
        """Test creating Ollama language model strategy."""
        config = Config()
        settings = self._get_default_mock_settings_data()
        settings["language_model"]["strategy"] = "ollama"
        config.settings_data = settings

        # @patch handles class replacement
        # sys.modules['language_model_strategies_impl'].OllamaLanguageModel = MockOllamaStrategy

        strategy = config.create_language_model_strategy()
        MockOllamaStrategy.assert_called_once_with(
            global_config=config,
            strategy_specific_config=settings["language_model"]["ollama"]
        )
        self.assertIsInstance(strategy, MagicMock)

    def test_create_unknown_strategy_raises_error(self):
        config = Config()
        settings = self._get_default_mock_settings_data()
        settings["image_generation"]["strategy"] = "unknown_image_strategy"
        settings["language_model"]["strategy"] = "unknown_lm_strategy"
        config.settings_data = settings

        with self.assertRaises(ValueError):
            config.create_image_generator_strategy()
        with self.assertRaises(ValueError):
            config.create_language_model_strategy()

if __name__ == '__main__':
    # Need to ensure that when tests run, the path is set up for card_generator imports
    # This is often handled by test runners (like pytest with project root) or by adding to sys.path
    # For direct `python test_config.py` from card_generator/tests:
    if str(Path(__file__).parent.parent) not in sys.path:
         sys.path.insert(0, str(Path(__file__).parent.parent)) # Add card_generator directory

    from datetime import datetime # Import here due to usage in default mock data
    unittest.main()

# Need to ensure datetime is available for the default mock data function
from datetime import datetime

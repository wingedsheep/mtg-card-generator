from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class LanguageModelStrategy(ABC):
    def __init__(self, global_config: Any, strategy_specific_config: Dict):
        """
        Initializes the language model strategy.
        Args:
            global_config: The global Config object.
            strategy_specific_config: Dictionary with specific settings for this strategy.
        """
        self.global_config = global_config
        self.strategy_specific_config = strategy_specific_config
        self._initialize_client_if_needed()

    def _initialize_client_if_needed(self):
        """
        A hook for strategies that need to initialize a client.
        Called at the end of __init__.
        """
        pass

    @abstractmethod
    def generate_text(self,
                      prompt: str,
                      system_prompt: Optional[str] = None,
                      model_key: Optional[str] = "default_main",  # Use a key to fetch model_id from strategy_config
                      **kwargs: Any) -> str:
        """
        Generates text based on the given prompt.
        Args:
            prompt (str): The main user prompt.
            system_prompt (str, optional): A system message to guide the model.
            model_key (str, optional): Key to look up the model ID in strategy_config['models'],
                                     e.g., "default_main", "art_prompt_generation".
            **kwargs: Additional model-specific parameters to be passed to the API.
        Returns:
            str: The generated text content.
        Raises:
            Exception: If text generation fails.
        """
        pass

    @abstractmethod
    def generate_json_response(self,
                               prompt: str,
                               system_prompt: Optional[str] = None,
                               model_key: Optional[str] = "default_json",  # Use a key for JSON-specific model
                               **kwargs: Any) -> Any:  # Could be Dict or List
        """
        Generates text expected to be JSON, and attempts to parse it.
        Args:
            prompt (str): The main user prompt.
            system_prompt (str, optional): A system message to guide the model.
            model_key (str, optional): Key to look up the model ID for JSON tasks.
            **kwargs: Additional model-specific parameters.
        Returns:
            Any: The parsed JSON content (typically Dict or List).
        Raises:
            Exception: If generation or JSON parsing fails.
        """
        pass

    def _get_model_id(self, model_key: Optional[str]) -> str:
        """Helper to get model_id from strategy_specific_config based on a key."""
        if not model_key:  # Should not happen if defaults are set
            raise ValueError("model_key cannot be None for _get_model_id")

        models_dict = self.strategy_specific_config.get("models", {})
        model_id = models_dict.get(model_key)

        if not model_id:
            # Fallback if a specific key (e.g. art_prompt_generation) is not defined, try default_main
            model_id = models_dict.get("default_main")
            if not model_id:
                raise ValueError(
                    f"Model ID for key '{model_key}' or fallback 'default_main' not found in strategy configuration.")
        return model_id

    def _get_common_params(self) -> Dict:
        """Helper to get common parameters from strategy_specific_config."""
        return self.strategy_specific_config.get("params", {}).copy()

    def _get_api_headers(self) -> Dict:
        """Helper to get API headers from global_config."""
        if hasattr(self.global_config, 'get_api_headers'):
            return self.global_config.get_api_headers()
        return self.global_config.api_headers if hasattr(self.global_config, 'api_headers') else {}

    def _get_api_key(self, service_name: str) -> Optional[str]:
        """Helper to get API key from global_config."""
        if hasattr(self.global_config, 'get_api_key'):
            return self.global_config.get_api_key(service_name)
        return None

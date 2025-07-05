from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict

# Forward declaration for type hinting if Config and Card are in models.py
# and models.py might import from here, creating a circular dependency.
# A better solution might be to move Card to its own file if it doesn't depend on Config.
# For now, assume they can be imported or use 'Any' if necessary.
# from .models import Card, Config
# Using Any for now to avoid potential circular import issues during initial file creation
from typing import Any

class ImageGeneratorStrategy(ABC):
    # __init__ should not be an abstractmethod if it has a concrete implementation
    def __init__(self, global_config: Any, strategy_specific_config: Dict):
        """
        Initializes the strategy.
        Args:
            global_config: The global Config object.
            strategy_specific_config: A dictionary containing specific settings for this strategy.
        """
        self.global_config = global_config
        self.strategy_config = strategy_specific_config
        self._initialize_client_if_needed()

    def _initialize_client_if_needed(self):
        """
        A hook for strategies that need to initialize a client or environment variable.
        Called at the end of __init__.
        """
        pass

    @abstractmethod
    def generate_image(self, art_prompt: str, card: Any, output_dir: Path, image_name: str) -> str:
        """
        Generates and saves an image based on the art prompt and card data.
        Args:
            art_prompt (str): The detailed prompt for image generation.
            card (Card): The card object for which art is being generated.
            output_dir (Path): The base directory to save the image (usually from global_config.output_dir).
            image_name (str): The desired name for the image file (e.g., "MyCard.png").
        Returns:
            str: Absolute path to the saved image file.
        Raises:
            Exception: If image generation fails.
        """
        pass

    def _ensure_output_dir_exists(self, path: Path):
        """Ensures the directory for the image exists."""
        path.parent.mkdir(parents=True, exist_ok=True)

    def _get_common_params(self, card: Any) -> Dict:
        """
        Helper to get common parameters like adjusted dimensions for Sagas.
        This can be overridden or extended by concrete strategies.
        """
        is_saga = "Saga" in card.type
        # Default to standard, strategies will need to fetch their specific dimension/ratio configs
        return {"is_saga": is_saga}

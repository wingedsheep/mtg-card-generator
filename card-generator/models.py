from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json
import os
# OpenAI import will be handled by strategies if needed, not directly by Config
# from openai import OpenAI

# Assuming card-generator/ is in sys.path, use direct imports
from image_generation_strategies import ImageGeneratorStrategy
from language_model_strategies import LanguageModelStrategy
# Concrete strategies will be imported within methods.


@dataclass
class Config:
    """Configuration for MTG card generation, loading from settings.json."""

    # Operational parameters (can be overridden at runtime or have defaults here)
    csv_file_path: str = "./assets/mtg_cards_english.csv"
    inspiration_cards_count: int = 100
    batches_count: int = 20
    theme_prompt: Optional[str] = None
    complete_theme_override: Optional[str] = None

    # Rarity and color distribution (could also move to settings.json if desired for full external config)
    mythics_per_batch: int = 1
    rares_per_batch: int = 3
    uncommons_per_batch: int = 4
    commons_per_batch: int = 5
    color_distribution: Dict[str, float] = field(default_factory=lambda: {
        "W": 0.2, "U": 0.2, "B": 0.2, "R": 0.2, "G": 0.2
    })

    # Land generation options
    generate_basic_lands: bool = True
    land_variations_per_type: int = 3

    # Internal state, not directly from settings.json for these
    set_id: str = field(init=False)
    output_dir: Path = field(init=False)

    # Loaded settings from settings.json
    settings_data: Dict = field(init=False, default_factory=dict)

    def __post_init__(self):
        self.set_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._load_settings() # Load all settings from settings.json

        base_output_dir = Path(self.settings_data.get('output_directory_base', 'output_sets'))
        self.output_dir = base_output_dir / self.set_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_settings(self, settings_path: str = "card-generator/settings.json"):
        """Load all settings from the primary JSON configuration file."""
        try:
            # Attempt to load user's settings.json first
            with open(settings_path, 'r') as f:
                self.settings_data = json.load(f)
            print(f"Successfully loaded settings from {settings_path}")
        except FileNotFoundError:
            print(f"Warning: {settings_path} not found. Attempting to load settings.example.json.")
            try:
                example_settings_path = "card-generator/settings.example.json"
                with open(example_settings_path, 'r') as f:
                    self.settings_data = json.load(f)
                print(f"Successfully loaded example settings from {example_settings_path}. "
                      f"Please create and configure '{settings_path}'.")
            except FileNotFoundError:
                print(f"Critical: Example settings file {example_settings_path} also not found. "
                      "Application may not function correctly without configuration.")
                self.settings_data = {} # Ensure it's a dict
        except json.JSONDecodeError as e:
            print(f"Critical: Error decoding JSON from {settings_path if Path(settings_path).exists() else example_settings_path}: {e}. "
                  "Application may not function correctly.")
            self.settings_data = {} # Ensure it's a dict


    def get_api_key(self, service_name: str) -> Optional[str]:
        """Get API key for a given service from loaded settings."""
        return self.settings_data.get("api_keys", {}).get(service_name)

    def get_api_headers(self) -> Dict[str, str]:
        """Get global API headers from loaded settings."""
        return self.settings_data.get("api_headers", {})

    def get_image_generation_config(self) -> Dict:
        """Get the image_generation block from loaded settings."""
        return self.settings_data.get("image_generation", {})

    def get_language_model_config(self) -> Dict:
        """Get the language_model block from loaded settings."""
        return self.settings_data.get("language_model", {})

    def get_output_path(self, filename: str) -> Path:
        """Get the full path for an output file within the current set's directory."""
        return self.output_dir / filename

    def create_image_generator_strategy(self) -> ImageGeneratorStrategy:
        """Creates and returns an instance of the configured ImageGeneratorStrategy."""
        # Import concrete strategies here using direct imports
        from image_generation_strategies_impl import ReplicateImageGenerator, HuggingFaceDiffusersImageGenerator

        img_gen_conf = self.get_image_generation_config()
        strategy_name = img_gen_conf.get("strategy", "replicate").lower()
        strategy_specific_conf = img_gen_conf.get(strategy_name, {})

        if strategy_name == "replicate":
            # API key is implicitly handled by ReplicateImageGenerator using get_api_key
            return ReplicateImageGenerator(global_config=self, strategy_specific_config=strategy_specific_conf)
        elif strategy_name == "diffusers":
            return HuggingFaceDiffusersImageGenerator(global_config=self, strategy_specific_config=strategy_specific_conf)
        else:
            raise ValueError(f"Unsupported image generation strategy: {strategy_name}")

    def create_language_model_strategy(self) -> LanguageModelStrategy:
        """Creates and returns an instance of the configured LanguageModelStrategy."""
        # Import concrete strategies here using direct imports
        from language_model_strategies_impl import OpenRouterLanguageModel, OllamaLanguageModel

        lm_conf = self.get_language_model_config()
        strategy_name = lm_conf.get("strategy", "openrouter").lower()
        strategy_specific_conf = lm_conf.get(strategy_name, {})

        if strategy_name == "openrouter":
            # API key is implicitly handled by OpenRouterLanguageModel using get_api_key
            return OpenRouterLanguageModel(global_config=self, strategy_specific_config=strategy_specific_conf)
        elif strategy_name == "ollama":
            return OllamaLanguageModel(global_config=self, strategy_specific_config=strategy_specific_conf)
        else:
            raise ValueError(f"Unsupported language model strategy: {strategy_name}")

@dataclass
class Card:
    """Represents a Magic: The Gathering card."""
    name: str
    mana_cost: str
    type: str
    rarity: str
    text: str
    colors: List[str]
    flavor: Optional[str] = None,
    power: Optional[str] = None
    toughness: Optional[str] = None
    loyalty: Optional[str] = None
    set_name: str = ""
    art_prompt: Optional[str] = None
    image_path: Optional[str] = None
    collector_number: Optional[str] = None
    description: str = ""

    @classmethod
    def from_dict(cls, data: Dict) -> 'Card':
        """Create a Card instance from a dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            mana_cost=data.get("mana_cost", ""),
            type=data.get("type", ""),
            rarity=data.get("rarity", ""),
            power=data.get("power", None),
            toughness=data.get("toughness", None),
            loyalty=data.get("loyalty", None),
            text=data.get("text", ""),
            flavor=data.get("flavor", ""),
            colors=data.get("colors", []),
            set_name=data.get("set_name", ""),
            art_prompt=data.get("art_prompt"),
            image_path=data.get("image_path"),
            collector_number=data.get("collector_number"),
            description=data.get("description", "")
        )

    def to_dict(self) -> Dict:
        """Convert the card to a dictionary."""
        return {
            "name": self.name,
            "mana_cost": self.mana_cost,
            "type": self.type,
            "rarity": self.rarity,
            "power": self.power,
            "toughness": self.toughness,
            "loyalty": self.loyalty,
            "text": self.text,
            "flavor": self.flavor,
            "colors": self.colors,
            "set_name": self.set_name,
            "art_prompt": self.art_prompt,
            "image_path": self.image_path,
            "collector_number": self.collector_number,
            "description": self.description
        }

    def __str__(self) -> str:
        return f"{self.name} ({self.rarity}) - {self.mana_cost}"
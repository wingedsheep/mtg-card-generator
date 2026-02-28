import json
from typing import List
import time

from models import Card, Config
from language_model_strategies import LanguageModelStrategy
from image_generation_strategies import ImageGeneratorStrategy
from prompts import build_art_prompt

MAX_ART_RETRIES = 3
IMAGE_RETRY_DELAY = 5
PROMPT_RETRY_DELAY = 2


class MTGArtGenerator:
    def __init__(self,
                 config: Config,
                 theme: str,
                 language_model_strategy: LanguageModelStrategy,
                 image_generator_strategy: ImageGeneratorStrategy):
        self.config = config
        self.theme = theme
        self.language_model = language_model_strategy
        self.image_generator = image_generator_strategy

    def generate_art_prompt_text(self, card: Card, attempt: int = 0) -> str:
        """Generate an art prompt for a given card using the configured LanguageModelStrategy."""
        image_strategy = self.config.get_image_generation_config().get("strategy", "replicate").lower()
        is_diffusers = image_strategy == "diffusers"

        prompt_content = build_art_prompt(
            card_name=card.name,
            card_type=card.type,
            card_rarity=card.rarity,
            card_text=card.text,
            card_flavor=card.flavor,
            card_colors=card.colors,
            card_power=card.power,
            card_toughness=card.toughness,
            card_description=card.description,
            theme=self.theme,
            is_diffusers=is_diffusers,
            attempt=attempt,
        )

        art_prompt_text = self.language_model.generate_text(
            prompt=prompt_content,
            system_prompt="You are an expert MTG art prompt generator.",
            model_key="art_prompt_generation"
        )
        return art_prompt_text.strip()

    def save_card_json_with_art_details(self, card: Card) -> None:
        """Saves the card data (including art_prompt and image_path) to a JSON file."""
        card_dict = card.to_dict()
        # Ensure the output path uses the global config's output_dir for the set
        # The image_path on the card should already be the final absolute path.
        json_path = self.config.get_output_path(f"{card.name.replace(' ', '_')}.json")

        # The structure for the JSON file seems to be a dict with a "card" key
        output_data = {"card": card_dict}

        json_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)
        print(f"Card data with art details saved to {json_path}")

    def generate_and_save_card_art(self, card: Card, art_prompt: str, max_retries: int = MAX_ART_RETRIES,
                                   retry_delay: int = IMAGE_RETRY_DELAY) -> str:
        """
        Generates image using the configured ImageGeneratorStrategy and saves it.
        Returns the absolute path to the saved image.
        """
        image_name = f"{card.name.replace(' ', '_')}.png"

        for attempt in range(max_retries):
            try:
                # The strategy is responsible for saving the image and returning its path
                # It uses self.config.output_dir (via global_config) and its own configured subdirectories.
                saved_image_path = self.image_generator.generate_image(
                    art_prompt=art_prompt,
                    card=card,
                    output_dir=self.config.output_dir,  # Pass the main set output dir
                    image_name=image_name
                )
                return saved_image_path
            except Exception as e:
                print(f"Error generating image for '{card.name}' (Attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to generate art for {card.name} after {max_retries} attempts.") from e
                time.sleep(retry_delay)
        return ""  # Should not be reached if max_retries > 0

    def process_card(self, card: Card) -> Card:
        """Process a single card: generate art prompt, generate image, update card.

        If card.art_prompt is already set (and not an error string), prompt generation
        is skipped and the existing prompt is used directly for image generation.
        """
        print(f"\nProcessing art for card: {card.name}")

        # Skip prompt generation if the card already has a valid art prompt
        if card.art_prompt and not card.art_prompt.startswith("Error:"):
            art_prompt_text = card.art_prompt
            print(f"Using existing art prompt: {art_prompt_text[:100]}...")
        else:
            art_prompt_text = self._generate_art_prompt_with_retries(card)
            if not art_prompt_text:
                return card
            card.art_prompt = art_prompt_text

        # 2. Generate and Save Image using the strategy
        try:
            saved_image_path_str = self.generate_and_save_card_art(card, art_prompt_text)
            card.image_path = saved_image_path_str
            print(f"Image for {card.name} generated and path set to: {card.image_path}")
        except Exception as e:
            print(f"Failed to generate and save image for {card.name}: {e}")
            card.image_path = None

        # 3. Save/Update Card JSON data (includes art_prompt and image_path)
        self.save_card_json_with_art_details(card)
        return card

    def _generate_art_prompt_with_retries(self, card: Card) -> str:
        """Try to generate an art prompt, retrying on failure. Returns empty string on total failure."""
        art_prompt_text = ""
        for attempt in range(MAX_ART_RETRIES):
            try:
                art_prompt_text = self.generate_art_prompt_text(card, attempt=attempt)

                # Check if we're using diffusers and log the prompt length for debugging
                image_strategy = self.config.get_image_generation_config().get("strategy", "replicate").lower()
                if image_strategy == "diffusers":
                    # Rough token count estimation (words * 1.3 for subword tokens)
                    estimated_tokens = len(art_prompt_text.split()) * 1.3
                    print(
                        f"Generated art prompt for diffusers (~{estimated_tokens:.0f} tokens): {art_prompt_text[:100]}...")
                    if estimated_tokens > 77:
                        print(f"Warning: Prompt may exceed 77-token limit ({estimated_tokens:.0f} estimated tokens)")
                else:
                    print(f"Generated art prompt (attempt {attempt + 1}): {art_prompt_text[:100]}...")

                if art_prompt_text:  # Basic validation
                    break
            except Exception as e:
                print(f"Error generating art prompt for {card.name} (attempt {attempt + 1}): {e}")
                if attempt == MAX_ART_RETRIES - 1:
                    print(f"Failed to generate art prompt for {card.name}. Skipping art.")
                    card.art_prompt = "Error: Failed to generate prompt"
                    self.save_card_json_with_art_details(card)
                    return ""
                time.sleep(PROMPT_RETRY_DELAY)

        if not art_prompt_text:
            print(f"Art prompt generation ultimately failed for {card.name}. Skipping art.")
            card.art_prompt = "Error: Prompt generation failed after retries"
            self.save_card_json_with_art_details(card)
            return ""

        return art_prompt_text

    def process_cards(self, cards: List[Card]) -> List[Card]:
        """Process a list of cards, generating art and saving data for each."""
        processed_cards_with_art = []
        for card_obj in cards:
            # Ensure card_obj is indeed a Card instance
            if not isinstance(card_obj, Card):
                print(f"Warning: Expected a Card object, got {type(card_obj)}. Skipping.")
                continue
            updated_card = self.process_card(card_obj)
            processed_cards_with_art.append(updated_card)
        return processed_cards_with_art

import json
from typing import List
import time

from models import Card, Config
from language_model_strategies import LanguageModelStrategy
from image_generation_strategies import ImageGeneratorStrategy


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
        theme_context = f"""Set Theme Context:
{self.theme}

Consider this theme when creating the art prompt. The art should reflect both the card's individual characteristics and the overall set theme.""" if self.theme else ""

        saga_instructions = ""
        if "Saga" in card.type:
            saga_instructions = """
IMPORTANT: This is a Saga card which requires VERTICAL art composition (portrait orientation). 
The art should be tall rather than wide. Saga cards display art along the right side of the card in a vertical format.
Create a VERTICAL composition that works well with the Saga card layout.
"""

        # Check if we're using the Diffusers strategy and need shorter prompts
        image_strategy = self.config.get_image_generation_config().get("strategy", "replicate").lower()
        is_diffusers_strategy = image_strategy == "diffusers"

        if is_diffusers_strategy:
            length_instructions = """
CRITICAL: This prompt will be used with Hugging Face Diffusers which has a 77-token limit. 
Generate a concise, focused prompt that is MAXIMUM 70 tokens (approximately 50 words).
Focus on the most essential visual elements only. Be concise but vivid.
Prioritize the most important visual aspects of the card.
"""
        else:
            length_instructions = """
- Focus on vivid, detailed scenes reflecting mechanics and flavor.
- Specify composition, lighting, mood, and key details.
"""

        prompt_content = f"""Create a detailed art prompt for a Magic: The Gathering card.
{saga_instructions}
Theme: {theme_context}
Card Name: {card.name}
Type: {card.type}
Rarity: {card.rarity}
Card Text: {card.text}
Flavor Text: {card.flavor}
Colors: {', '.join(card.colors) if card.colors else 'Colorless'}
P/T: {card.power}/{card.toughness} (if applicable)
Description: {card.description}

Instructions for prompt generation:
{length_instructions}
- Start with "Oil on canvas painting. Magic the gathering art. Rough brushstrokes."
- Ensure prompt is safe for work.
- If a character name is present, include their full name.
- Return only the prompt text.
{f"Retry attempt {attempt}: Focus on safety and clarity." if attempt > 0 else ""}
"""

        # Use the language model strategy to generate the art prompt
        art_prompt_text = self.language_model.generate_text(
            prompt=prompt_content,
            system_prompt="You are an expert MTG art prompt generator.",
            model_key="art_prompt_generation"  # Key from language_model settings
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

    def generate_and_save_card_art(self, card: Card, art_prompt: str, max_retries: int = 3,
                                   retry_delay: int = 5) -> str:
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
        """Process a single card: generate art prompt, generate image, update card."""
        print(f"\nProcessing art for card: {card.name}")

        # 1. Generate Art Prompt Text
        # Retry logic for prompt generation can be added here if needed, or assumed to be simpler.
        art_prompt_text = ""
        for attempt in range(3):  # Simple retry for prompt generation
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
                if attempt == 2:
                    print(f"Failed to generate art prompt for {card.name}. Skipping art.")
                    card.art_prompt = "Error: Failed to generate prompt"
                    # card.image_path remains None
                    self.save_card_json_with_art_details(card)  # Save with error state
                    return card  # Return card without art if prompt fails critically
                time.sleep(2)

        if not art_prompt_text:  # If loop finished without a good prompt
            print(f"Art prompt generation ultimately failed for {card.name}. Skipping art.")
            card.art_prompt = "Error: Prompt generation failed after retries"
            self.save_card_json_with_art_details(card)
            return card

        card.art_prompt = art_prompt_text

        # 2. Generate and Save Image using the strategy
        try:
            # The image generation strategy handles its own retries internally if designed so,
            # or we can wrap its call in retries here. The current design implies generate_and_save_card_art handles retries.
            saved_image_path_str = self.generate_and_save_card_art(card, art_prompt_text)
            card.image_path = saved_image_path_str  # Store the absolute path
            print(f"Image for {card.name} generated and path set to: {card.image_path}")
        except Exception as e:
            print(f"Failed to generate and save image for {card.name}: {e}")
            card.image_path = None  # Ensure path is None if art generation fails
            # Art prompt is still saved, image_path indicates failure.

        # 3. Save/Update Card JSON data (includes art_prompt and image_path)
        # This is crucial to do after art generation attempt, regardless of success,
        # to save the art_prompt and the status of image_path.
        self.save_card_json_with_art_details(card)

        return card

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

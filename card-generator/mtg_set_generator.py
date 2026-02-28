import csv
import json
import random
from collections import Counter
from typing import List, Dict, Any

from models import Config, Card
from language_model_strategies import LanguageModelStrategy
from prompts import build_theme_prompt, build_batch_prompt, build_text_to_json_prompt


class MTGSetGenerator:
    def __init__(self, config: Config, language_model_strategy: LanguageModelStrategy):
        self.config = config
        self.language_model = language_model_strategy
        self.inspiration_cards: List[Card] = []
        self.generated_cards: List[Card] = []
        self.set_theme = ""
        self.collector_number_counter = 1

    def load_inspiration_cards(self) -> None:
        """Load random cards from CSV file as inspiration."""
        print("Loading inspiration cards...")

        with open(self.config.csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            all_cards = list(reader)

        sampled_cards = random.sample(all_cards, self.config.inspiration_cards_count)
        self.inspiration_cards = [Card.from_dict(card_data) for card_data in sampled_cards]

        print(f"Loaded {len(self.inspiration_cards)} inspiration cards")

    def generate_set_theme(self) -> None:
        """Generate set theme using OpenRouter API."""
        print("Generating set theme...")

        # Prepare inspiration cards summary
        inspiration_summary = "\n".join([
            f"- {card.name}: {card.type} with abilities: {card.text}"
            for card in self.inspiration_cards
        ])

        prompt_content = self._get_theme_prompt(inspiration_summary)

        self.set_theme = self.language_model.generate_text(
            prompt=prompt_content,
            system_prompt="You are an expert lore writer",
            model_key="theme_generation"
        )
        print("\nGenerated theme:")
        print(self.set_theme)

    def _get_theme_prompt(self, inspiration_summary: str) -> str:
        """Get the prompt for set theme generation."""
        return build_theme_prompt(inspiration_summary, self.config.theme_prompt)

    def convert_text_to_json(self, cards_text: str) -> List[Dict]:
        """Convert card text descriptions to JSON format."""
        prompt = build_text_to_json_prompt(cards_text)
        try:
            # Use the language_model strategy for JSON conversion
            # The specific model (e.g., "json_conversion_from_text") is chosen by the strategy
            # from its config loaded from settings.json
            parsed_json = self.language_model.generate_json_response(
                prompt=prompt,
                system_prompt="You are a JSON converter. Output only the JSON array.",
                model_key="json_conversion_from_text"
            )
            if not isinstance(parsed_json, list):
                # The generate_json_response should ideally return a list based on the prompt.
                # If it's a dict (e.g. if LLM wrapped it in {"cards": [...]}), try to extract.
                if isinstance(parsed_json, dict) and "cards" in parsed_json and isinstance(parsed_json["cards"], list):
                    return parsed_json["cards"]
                print(f"Warning: Expected a list from JSON conversion, got {type(parsed_json)}. Content: {parsed_json}")
                # Depending on strictness, either raise error or try to adapt. For now, returning as is.
                # Consider adding more robust extraction or error handling if LLMs frequently misformat.
                if parsed_json is None: return []  # Handle case where strategy returns None on error
                return parsed_json  # Or raise TypeError if list is strictly expected.

            return parsed_json
        except Exception as e:
            print(f"Error converting card text to JSON using language model: {e}")
            # The strategy's generate_json_response should raise an error if parsing failed,
            # including the raw text in its error message if possible.
            raise  # Re-raise the error from the strategy or a new one.

    def generate_batch(self, batch_number: int) -> List[Dict]:
        """Generate a batch of cards using OpenRouter API with simple continuation handling."""
        print(f"\nGenerating batch {batch_number}/{self.config.batches_count}...")

        # Calculate current color distribution
        color_counts = Counter()
        total_color_weight = 0

        # Calculate weights for existing cards
        for card in self.generated_cards:
            # Count colors in this card
            card_colors = [c for c in card.colors if c in self.config.color_distribution]
            if card_colors:  # If it's a colored card
                weight_per_color = 1.0 / len(card_colors)  # Distribute the weight evenly
                for color in card_colors:
                    color_counts[color] += weight_per_color
                    total_color_weight += weight_per_color

        # Calculate distribution as a percentage of total color weight
        current_distribution = {
            color: count / total_color_weight if total_color_weight > 0 else 0.2
            for color, count in color_counts.items()
        }

        # Ensure all colors are represented in the distribution
        for color in ["W", "U", "B", "R", "G"]:
            if color not in current_distribution:
                current_distribution[color] = 0 if total_color_weight > 0 else 0.2

        # Calculate expected total cards for this batch
        expected_cards = (
                self.config.mythics_per_batch +
                self.config.rares_per_batch +
                self.config.uncommons_per_batch +
                self.config.commons_per_batch
        )

        # Initial generation attempt
        batch_prompt_text = self._get_batch_prompt(current_distribution)

        # Use language model strategy for generating the initial batch of card descriptions
        initial_response_text = self.language_model.generate_text(
            prompt=batch_prompt_text,
            system_prompt="You are an MTG card designer. Follow the batch instructions precisely.",
            model_key="card_batch_generation"  # Key from language_model settings
        )

        try:
            cards_data = self.convert_text_to_json(initial_response_text)
        except Exception as e:
            print(f"Error in initial JSON conversion for batch {batch_number}: {e}")
            print(
                f"Raw initial response for batch {batch_number}: {initial_response_text[:500]}...")  # Log part of the raw response
            cards_data = []

        # If we don't have enough cards, try a simple continuation
        # Note: True conversational continuation is complex. This is a simplified approach.
        # A more robust solution might involve resending the whole context or specific instructions.
        if len(cards_data) < expected_cards:
            print(
                f"Generated {len(cards_data)} cards, expected {expected_cards} for batch {batch_number}. Attempting continuation...")

            continuation_prompt = (
                f"{batch_prompt_text}\n\n"
                f"PREVIOUSLY GENERATED TEXT (may be incomplete or contain errors):\n{initial_response_text}\n\n"
                f"CONTINUATION INSTRUCTION: Please generate the remaining {expected_cards - len(cards_data)} cards, "
                f"ensuring they are distinct from any cards implied in the 'PREVIOUSLY GENERATED TEXT' and adhere to the original batch request. "
                f"Output only the new card descriptions."
            )

            # Using generate_text for continuation, then convert_text_to_json will parse it.
            # The system prompt might need to be adjusted for continuation.
            continued_response_text = self.language_model.generate_text(
                prompt=continuation_prompt,
                system_prompt="You are an MTG card designer completing a batch. Focus on providing only the missing cards.",
                model_key="card_batch_generation"  # Use the same model or a specific continuation model
            )

            try:
                additional_cards_data = self.convert_text_to_json(continued_response_text)
                cards_data.extend(additional_cards_data)
                print(f"Added {len(additional_cards_data)} cards through continuation for batch {batch_number}.")
            except Exception as e:
                print(f"Error in continuation JSON conversion for batch {batch_number}: {e}")
                print(f"Raw continuation response for batch {batch_number}: {continued_response_text[:500]}...")

        # Add collector numbers
        for card_data in cards_data:
            card_data["collector_number"] = str(self.collector_number_counter)
            self.collector_number_counter += 1

        # Final check
        if len(cards_data) != expected_cards:
            print(f"Warning: Generated {len(cards_data)} cards, expected {expected_cards}")

        return cards_data

    def _get_batch_prompt(self, current_distribution: Dict[str, float]) -> str:
        """Get the prompt for batch generation with improved formatting and clarity."""
        inspiration_cards_text = "\n".join([
            f"- {card.name} ({card.rarity}): {card.type} with {card.mana_cost}, {card.text}"
            for card in self.inspiration_cards
        ])

        existing_cards_text = "\n".join([
            f"- {card.name} ({card.rarity}): {card.type} with {card.mana_cost}, {card.text}"
            for card in self.generated_cards
        ])

        return build_batch_prompt(
            inspiration_cards_text=inspiration_cards_text,
            set_theme=self.set_theme,
            existing_cards_text=existing_cards_text,
            current_distribution=current_distribution,
            mythics_per_batch=self.config.mythics_per_batch,
            rares_per_batch=self.config.rares_per_batch,
            uncommons_per_batch=self.config.uncommons_per_batch,
            commons_per_batch=self.config.commons_per_batch,
        )

    def initialize_set(self) -> None:
        """Initialize the set by loading inspiration cards and generating the theme."""
        self.load_inspiration_cards()

        # Check if a complete theme override is provided
        if self.config.complete_theme_override:
            print("Using provided complete theme override instead of generating a new theme")
            self.set_theme = self.config.complete_theme_override
        else:
            # Generate a new theme using the theme prompt
            self.generate_set_theme()

        # Reset collector number counter at the start of set generation
        self.collector_number_counter = 1

    def generate_batch_cards(self, batch_num: int) -> List[Card]:
        """Generate a single batch of cards and return them."""
        card_dicts = self.generate_batch(batch_num)

        # Convert dictionaries to Card objects
        cards = [Card.from_dict(card_data) for card_data in card_dicts]

        # Add to the overall set
        self.generated_cards.extend(cards)

        print(f"Batch {batch_num} generation complete. Total cards: {len(self.generated_cards)}")
        self.save_progress()

        return cards

    def generate_set(self) -> None:
        """Generate complete card set."""
        self.initialize_set()

        for batch_num in range(1, self.config.batches_count + 1):
            self.generate_batch_cards(batch_num)

    def restore_state(self, theme: str, cards: List[Card], collector_number_counter: int) -> None:
        """Restore generator state when resuming an incomplete set."""
        self.set_theme = theme
        self.generated_cards = cards
        self.collector_number_counter = collector_number_counter

        # Load inspiration cards (needed for batch prompts that reference them)
        self.load_inspiration_cards()

        print(f"Restored state: {len(cards)} cards, collector_number at {collector_number_counter}")
        print(f"Theme loaded ({len(theme)} chars)")

    def save_progress(self) -> None:
        """Save current progress to JSON file."""
        output = {
            "theme": self.set_theme,
            "cards": [card.to_dict() for card in self.generated_cards]
        }

        output_path = self.config.get_output_path("mtg_set_output.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)

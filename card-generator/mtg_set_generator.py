import csv
import json
import random
from collections import Counter
from typing import List, Dict, Any

from models import Config, Card
from language_model_strategies import LanguageModelStrategy


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
            system_prompt="You are an expert MTG set theme designer.",
            model_key="theme_generation" # Key from language_model settings in settings.json
            # Potentially add temperature or other params via kwargs if needed
        )
        print("\nGenerated theme:")
        print(self.set_theme)

    def _get_theme_prompt(self, inspiration_summary: str) -> str:
        """Get the prompt for set theme generation."""
        base_prompt = f"""
        Some inspirational cards. These cards are not in the set and not part of the theme. You can just use them to get a feel for the mechanics, types etc.:
        {inspiration_summary}

        Create a detailed theme for a new Magic The Gathering set. Include:
        1. Detailed history and lore of the set, including notable characters/creatures and events
        2. Key factions, locations, events that are a part of this set
        3. A list of creature types that appear in the set (not all, just some examples in the set)
        4. Main mechanical themes and gameplay elements. Don't introduce new mechanics here, just describe how they are used in the set.
        5. Potential synergies between different card types and mechanics
        6. How the theme supports different play styles

        Try to keep the theme broad enough, and add enough complexity to allow for a variety of card types, and keep the color distribution in mind.
        Be as detailed as possible to create a rich and engaging world for the set.

        """

        # If a theme prompt is provided, incorporate it into the base prompt
        if self.config.theme_prompt:
            base_prompt = f"""Base the theme on the following prompt: {self.config.theme_prompt}

{base_prompt}"""

        base_prompt += "\n\nThe theme should be original while maintaining the core elements that make Magic engaging."

        return base_prompt

    def convert_text_to_json(self, cards_text: str) -> List[Dict]:
        """Convert card text descriptions to JSON format."""
        prompt = f"""Convert the following Magic: The Gathering card descriptions into a JSON array.
Each card has the following fields: name, mana_cost, type, rarity, power (null if not creature), 
toughness (null if not creature), loyalty (null if not planeswalker), text, flavor, colors (array of W, U, B, R, G or none if colorless), description.

class Card:
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

Cards to convert:

{cards_text}

Return only the JSON array with no additional text or explanation."""
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
                if parsed_json is None: return [] # Handle case where strategy returns None on error
                return parsed_json # Or raise TypeError if list is strictly expected.

            return parsed_json
        except Exception as e:
            print(f"Error converting card text to JSON using language model: {e}")
            # The strategy's generate_json_response should raise an error if parsing failed,
            # including the raw text in its error message if possible.
            raise # Re-raise the error from the strategy or a new one.

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
            model_key="card_batch_generation" # Key from language_model settings
        )

        try:
            cards_data = self.convert_text_to_json(initial_response_text)
        except Exception as e:
            print(f"Error in initial JSON conversion for batch {batch_number}: {e}")
            print(f"Raw initial response for batch {batch_number}: {initial_response_text[:500]}...") # Log part of the raw response
            cards_data = []

        # If we don't have enough cards, try a simple continuation
        # Note: True conversational continuation is complex. This is a simplified approach.
        # A more robust solution might involve resending the whole context or specific instructions.
        if len(cards_data) < expected_cards:
            print(f"Generated {len(cards_data)} cards, expected {expected_cards} for batch {batch_number}. Attempting continuation...")

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
                model_key="card_batch_generation" # Use the same model or a specific continuation model
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
        # Get inspiration cards formatted string
        inspiration_cards = "\n".join([
            f"- {card.name} ({card.rarity}): {card.type} with {card.mana_cost}, {card.text}"
            for card in self.inspiration_cards
        ])

        # Get existing cards formatted string
        existing_cards = "\n".join([
            f"- {card.name} ({card.rarity}): {card.type} with {card.mana_cost}, {card.text}"
            for card in self.generated_cards
        ])

        def get_representation_level(diff):
            # Since target is 0.2 (20%), calculate percentage relative to target
            percentage_diff = (diff / 0.2) * 100

            if abs(percentage_diff) < 10:  # Less than 10% difference from target
                return "well-balanced"
            elif abs(percentage_diff) < 25:  # 10-25% difference from target
                return "slightly " + ("under" if diff > 0 else "over") + "-represented"
            elif abs(percentage_diff) < 50:  # 25-50% difference from target
                return "significantly " + ("under" if diff > 0 else "over") + "-represented"
            else:  # More than 50% difference from target
                return "severely " + ("under" if diff > 0 else "over") + "-represented"

        cards_per_batch = (self.config.mythics_per_batch +
                           self.config.rares_per_batch +
                           self.config.uncommons_per_batch +
                           self.config.commons_per_batch)

        color_analysis = f"""Color Distribution Analysis:
        - White (W): {abs(0.2 - current_distribution.get('W', 0)) * 100:.1f}% {get_representation_level(0.2 - current_distribution.get('W', 0))}
        - Blue (U): {abs(0.2 - current_distribution.get('U', 0)) * 100:.1f}% {get_representation_level(0.2 - current_distribution.get('U', 0))}
        - Black (B): {abs(0.2 - current_distribution.get('B', 0)) * 100:.1f}% {get_representation_level(0.2 - current_distribution.get('B', 0))}
        - Red (R): {abs(0.2 - current_distribution.get('R', 0)) * 100:.1f}% {get_representation_level(0.2 - current_distribution.get('R', 0))}
        - Green (G): {abs(0.2 - current_distribution.get('G', 0)) * 100:.1f}% {get_representation_level(0.2 - current_distribution.get('G', 0))}

        Priority for upcoming cards:
        1. Colors that are severely under-represented should be highest priority
        2. Colors that are significantly under-represented should be high priority
        3. Colors that are over-represented should be generated less in this batch
        4. Maintain overall color balance"""

        return f"""Based on the following context for a Magic The Gathering set:

        Some inspirational cards. Just use these for mechanics, types etc. These cards are not in the set and not part of the theme:
        {inspiration_cards}

        Theme:
        {self.set_theme}

        # Card Rarity Guidelines

        ## Common
        - Simple, vanilla effects that work in multiples
        - Basic creature types and spells
        - Usually clean, short rules text, or no rules at all
        - Foundation of gameplay mechanics

        ## Uncommon
        - Moderately complex abilities
        - Support for specific strategies
        - Clear synergies with other cards

        ## Rare
        - Format-defining effects
        - Important characters or spells
        - Unique mechanics
        - Can shape deck strategies

        ## Mythic Rare
        - Game-changing effects
        - Major characters
        - Splashy, memorable designs
        - Build-around centerpieces

        Existing cards in the set:
        {existing_cards}

        Color analysis:
        {color_analysis}

        Instructions:

        - Create a batch of new cards that fit into the theme of the set.
        - Think of how this batch adds to the existing cards in the set.
        - Make sure this batch has some memorable cards.
        - Ensure that these cards are different enough from the cards already in the set. They should add to the variety and depth of the set.
        - Think about already existing cards, and how the cards in this batch complement those cards.
        - Cards in this batch are varied and different enough from the existing cards in the set.
        - Think about the color distribution analysis above and prioritize underrepresented colors.
        - Try to keep card types in the set well-balanced. Also, make sure the color distribution in the whole set is balanced. Artifacts and colorless cards are also important, if they fit the theme.
        - Make sure the color distribution in the whole set is balanced. Artifacts and colorless cards are also important, if they fit the theme.
        - ALWAYS include an explanation between brackets for less common mechanics.
        Well known mechanics like flying, haste, etc. do not need explanations.
        - Think about synergy in the set.
        - Look at the rarity instructions.
        - Multi color cards are fine, but they appear less frequently than mono color cards.\
        - No dual sided cards

        First make a plan for the rare and mythic cards of this batch, what are they going to be? (notable characters described in the theme are fine as long as they are not already in the set).
        Then think of what would be a good addition to add some variety to the set and make it more interesting. What could we add to the uncommon and common cards?
        Keeping in mind the number of rarities in this batch. These could inspire the cards in the batch.
        Make a short plan for the batch, write it down, and then start creating the cards.

        Then generate {cards_per_batch} new cards, fitting the theme, with the following rarity distribution:
        - {self.config.mythics_per_batch} Mythic Rare
        - {self.config.rares_per_batch} Rare
        - {self.config.uncommons_per_batch} Uncommon
        - {self.config.commons_per_batch} Common

        For each card, provide a complete description in this format:
        Card Name (Rarity)
        Mana Cost: [cost]
        Type: [type]
        Power/Toughness: [P/T] (if creature)
        Loyalty: [loyalty] (if planeswalker)
        Rules Text: [text]
        Flavor Text: [flavor]
        Colors: [colors]
        Description: [short lore + visual description]"""

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

    def save_progress(self) -> None:
        """Save current progress to JSON file."""
        output = {
            "theme": self.set_theme,
            "cards": [card.to_dict() for card in self.generated_cards]
        }

        output_path = self.config.get_output_path("mtg_set_output.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
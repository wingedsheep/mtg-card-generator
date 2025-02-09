import csv
import json
import random
from collections import Counter
from openai import OpenAI
from typing import List, Dict
from models import Config, Card


class MTGSetGenerator:
    def __init__(self, config: Config):
        self.config = config
        self.inspiration_cards: List[Card] = []
        self.generated_cards: List[Card] = []
        self.set_theme = ""
        self.collector_number_counter = 1  # Initialize counter at 1

        # Load API key and initialize client
        self.client = self._initialize_client()

    def _initialize_client(self) -> OpenAI:
        """Initialize the OpenAI client with OpenRouter configuration."""
        with open("settings.json") as f:
            settings = json.load(f)
            openrouter_api_key = settings["openrouter"]["apiKey"]

        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
        )

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

        prompt = self._get_theme_prompt(inspiration_summary)

        completion = self.client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://example.com",
                "X-Title": "MTG Set Generator"
            },
            model="openai/chatgpt-4o-latest",
            temperature=1.0,
            messages=[{"role": "user", "content": prompt}]
        )

        self.set_theme = completion.choices[0].message.content
        print("\nGenerated theme:")
        print(self.set_theme)

    def _get_theme_prompt(self, inspiration_summary: str) -> str:
        """Get the prompt for set theme generation."""
        base_prompt = f"""
        Some inspirational cards. These cards are not in the set and not part of the theme. You can just use them to get a feel for the mechanics, types etc.:
        {inspiration_summary}
        
        Create a detailed theme for a new Magic The Gathering set. Include:
        1. Overall theme and setting (background story and world building)
        2. Notable factions and characters in the set
        3. Key locations and events
        4. Any new mechanics or keywords (max 2) with a brief explanation. Mention that these should be explained on the cards.
        4. Main mechanical themes and gameplay elements
        5. Potential synergies between different card types and mechanics
        6. How the theme supports different play styles
        
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
Each card should have the following fields: name, mana_cost, type, rarity, power (null if not creature), 
toughness (null if not creature), text, flavor, colors (array of W, U, B, R, G or none if colorless), description.

Cards to convert:

{cards_text}

Return only the JSON array with no additional text or explanation."""

        completion = self.client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://example.com",
                "X-Title": "MTG Set Generator"
            },
            model="openai/chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "You are a JSON converter."},
                {"role": "user", "content": prompt}
            ]
        )

        try:
            response_text = completion.choices[0].message.content
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']')
            if start_idx != -1 and end_idx != -1:
                json_text = response_text[start_idx:end_idx + 1]
                return json.loads(json_text)
            raise ValueError("No valid JSON array found in response")
        except Exception as e:
            print(f"Error converting to JSON: {e}")
            print("Raw response:", response_text)
            raise

    def generate_batch(self, batch_number: int) -> List[Dict]:
        """Generate a batch of cards using OpenRouter API."""
        print(f"\nGenerating batch {batch_number}/{self.config.batches_count}...")

        # Calculate current color distribution
        color_counts = Counter()
        for card in self.generated_cards:
            for color in card.colors:
                if color in self.config.color_distribution:
                    color_counts[color] += 1

        total_cards = len(self.generated_cards)
        current_distribution = {
            color: count / total_cards if total_cards > 0 else 0
            for color, count in color_counts.items()
        }

        # Generate cards
        cards_text = self._get_batch_prompt(current_distribution)
        completion = self.client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://example.com",
                "X-Title": "MTG Set Generator"
            },
            model="openai/chatgpt-4o-latest",
            messages=[{"role": "user", "content": cards_text}]
        )

        cards_data = self.convert_text_to_json(completion.choices[0].message.content)

        # Add collector numbers
        for card_data in cards_data:
            card_data["collector_number"] = str(self.collector_number_counter)
            self.collector_number_counter += 1

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

        cards_per_batch = self.config.mythics_per_batch + self.config.rares_per_batch + self.config.uncommons_per_batch + self.config.commons_per_batch

        return f"""Based on the following context for a Magic The Gathering set:

    Some inspirational cards. Just use these for mechanics, types etc. These cards are not in the set and not part of the theme:
    {inspiration_cards}

    Theme:
    {self.set_theme}

    Existing cards in the set:
    {existing_cards}

    Current color distribution:
    {json.dumps(current_distribution, indent=2)}

    Target color distribution:
    {{
      "W": 0.2,
      "U": 0.2,
      "B": 0.2,
      "R": 0.2,
      "G": 0.2
    }}

    Instructions:

    - Create a batch of new cards that fit seamlessly into the theme, ensuring they are mechanically unique, thematically rich, and synergize well with the existing set.
    - Make sure each batch has some memorable cards.
    - Ensure that these cards are different enough from the cards already in the set. They should add to the variety and depth of the set.
    - Think about already existing cards, and how the cards in this batch complement those cards.
    - Cards in this batch are varied and different enough from the existing cards in the set.
    - Try to keep card types in the set well-balanced.
    - Make sure the color distribution in the whole set is balanced. Artifacts and colorless cards are also important, if they fit the theme.
    - ALWAYS include an explanation between for any new mechanics or keywords introduced in this set between brackets, or for less common mechanics.
    Well known mechanics like flying, haste, etc. do not need explanations.
    - Think about synergy in the set.
    - Look at the rarity instructions.

    First describe few unique characters or events for the theme that are not already in the existing cards (notable characters in theme is fine).
    Keeping in mind the number of rarities in this batch. These could inspire the cards in the batch.

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
    Rules Text: [text]
    Flavor Text: [flavor]
    Colors: [colors]
    Description: [short lore + visual description]"""

    def generate_set(self) -> None:
        """Generate complete card set."""
        self.load_inspiration_cards()
        self.generate_set_theme()

        # Reset collector number counter at the start of set generation
        self.collector_number_counter = 1

        for batch_num in range(1, self.config.batches_count + 1):
            new_cards = self.generate_batch(batch_num)
            self.generated_cards.extend([Card.from_dict(card_data) for card_data in new_cards])

            print(f"Batch {batch_num} complete. Total cards: {len(self.generated_cards)}")
            self.save_progress()

    def save_progress(self) -> None:
        """Save current progress to JSON file."""
        output = {
            "theme": self.set_theme,
            "cards": [card.to_dict() for card in self.generated_cards]
        }

        output_path = self.config.get_output_path("mtg_set_output.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)

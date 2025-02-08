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
            messages=[{"role": "user", "content": prompt}]
        )

        self.set_theme = completion.choices[0].message.content
        print("\nGenerated theme:")
        print(self.set_theme)

    def _get_theme_prompt(self, inspiration_summary: str) -> str:
        """Get the prompt for set theme generation."""
        return f"""Given the following Magic: The Gathering cards as inspiration:

{inspiration_summary}

Create a detailed theme for a new Magic: The Gathering set. Include:
1. Overall theme and setting (background story and worldbuilding, remember to keep it original and true to magic the gathering lore)
2. Main mechanical themes and gameplay elements
3. How the five colors (White, Blue, Black, Red, Green) and optionally artifacts interact and their primary strategies
4. Potential synergies between different card types and mechanics
5. How the theme supports different play styles (aggro, control, midrange, combo)
6. Creature types that are central to the set

The theme should be original while maintaining the core elements that make Magic engaging."""

    def convert_text_to_json(self, cards_text: str) -> List[Dict]:
        """Convert card text descriptions to JSON format."""
        prompt = f"""Convert the following Magic: The Gathering card descriptions into a JSON array.
Each card should have the following fields: name, mana_cost, type, rarity, power (null if not creature), 
toughness (null if not creature), text, flavor, colors (array of W, U, B, R, G or none if colorless).

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
        """Get the prompt for batch generation."""
        all_context_cards = self.inspiration_cards + self.generated_cards
        cards_text = "\n".join([
            f"- {card.name} ({card.rarity}): {card.type} with {card.mana_cost}, {card.text}"
            for card in all_context_cards
        ])

        inspiration_cards = "\n".join([
            f"- {card.name} ({card.rarity}): {card.type} with {card.mana_cost}, {card.text}"
            for card in self.inspiration_cards
        ])

        return f"""Based on the following context for a Magic: The Gathering set:
        
Inspiration cards (not from this set):
{inspiration_cards}

Theme:
{self.set_theme}

Existing cards in the set:
{cards_text}

Current color distribution:
{json.dumps(current_distribution, indent=2)}

Target color distribution:
{json.dumps(self.config.color_distribution, indent=2)}

Generate {self.config.cards_per_batch} new cards with the following rarity distribution:
- {self.config.mythics_per_batch} Mythic Rare
- {self.config.rares_per_batch} Rare
- {self.config.uncommons_per_batch} Uncommon
- {self.config.commons_per_batch} Common

Make sure that the cards in this batch are varied and different enough from the existing cards in the set.
Make sure they supplement the existing cards well.

For each card, provide a complete description in this format:
Card Name (Rarity)
Mana Cost: [cost]
Type: [type]
Power/Toughness: [P/T] (if creature)
Rules Text: [text]
Flavor Text: [flavor]
Colors: [colors]

Always include an explanation between ( ) for any new mechanics or keywords introduced.
Well known mechanics like flying, haste, etc. do not need explanations.

The cards should maintain color balance and have mechanical synergy with existing cards."""

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
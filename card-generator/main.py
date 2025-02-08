import json
import datetime
import os
import asyncio
from pathlib import Path
from typing import Dict, List
from collections import Counter

from models import Config, Card
from mtg_set_generator import MTGSetGenerator
from mtg_art_generator import MTGArtGenerator
from mtg_json_converter import MTGJSONConverter
from mtg_card_renderer import MTGCardRenderer


class MTGGeneratorOrchestrator:
    def __init__(self, config: Config):
        self.config = config
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)

        # Load API tokens
        self._load_api_tokens()

        # Initialize components
        self.set_generator = MTGSetGenerator(config)
        self.art_generator = MTGArtGenerator(config)
        self.json_converter = MTGJSONConverter()
        self.card_renderer = MTGCardRenderer(config)

    def _load_api_tokens(self):
        """Load API tokens from settings.json and set environment variables."""
        with open("settings.json") as f:
            settings = json.load(f)

            # Set Replicate API token as environment variable
            if replicate_token := settings.get("replicate", {}).get("apiKey"):
                os.environ["REPLICATE_API_TOKEN"] = replicate_token
            else:
                raise ValueError("Replicate API token not found in settings.json")

    async def generate_complete_set(self) -> Dict:
        """Generate a complete MTG set including cards, art, and rendered images."""
        print("\n=== Starting MTG Set Generation ===")

        # Step 1: Generate card set
        print("\n--- Generating Card Set ---")
        self.set_generator.generate_set()

        # Step 2: Generate art for all cards
        print("\n--- Generating Card Art ---")
        theme, cards = self._load_generated_cards()
        cards_with_art = self.art_generator.process_cards(cards)

        # Step 3: Compile final data
        print("\n--- Compiling Final Data ---")
        stats = self._calculate_statistics(cards_with_art)
        combined_data = self._create_combined_data(theme, cards_with_art, stats)

        # Step 4: Save final data
        print("\n--- Saving Final Data ---")
        self._save_final_data(combined_data)

        # Step 5: Convert to rendering format
        print("\n--- Converting to Rendering Format ---")
        self._convert_to_rendering_format()

        # Step 6: Render cards as images
        print("\n--- Rendering Cards as Images ---")
        await self.card_renderer.render_cards()

        # Print final statistics
        self._print_statistics(stats)

        return combined_data

    def _load_generated_cards(self) -> tuple[str, List[Card]]:
        """Load the generated card set."""
        output_path = self.config.get_output_path("mtg_set_output.json")
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            theme = data["theme"]
            cards = [Card.from_dict(card_data) for card_data in data["cards"]]
        return theme, cards

    def _save_final_data(self, data: Dict) -> None:
        """Save the final combined data."""
        output_path = self.config.get_output_path("mtg_set_complete.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\nComplete set data saved to {output_path}")

    def _convert_to_rendering_format(self) -> None:
        """Convert all cards to rendering format."""
        try:
            self.json_converter.convert_directory(
                input_dir=self.config.output_dir,
                output_dir=self.config.output_dir,
                max_retries=3
            )
            print("Successfully converted cards to rendering format")
        except Exception as e:
            print(f"Error during conversion to rendering format: {e}")

    def _calculate_statistics(self, cards: List[Card]) -> Dict:
        """Calculate set statistics."""
        rarity_counts = Counter(card.rarity for card in cards)
        color_counts = Counter()
        for card in cards:
            for color in card.colors:
                color_counts[color] += 1

        return {
            "card_count": len(cards),
            "rarity_distribution": {
                "mythic": rarity_counts["Mythic Rare"],
                "rare": rarity_counts["Rare"],
                "uncommon": rarity_counts["Uncommon"],
                "common": rarity_counts["Common"]
            },
            "color_distribution": {
                "W": color_counts["W"],
                "U": color_counts["U"],
                "B": color_counts["B"],
                "R": color_counts["R"],
                "G": color_counts["G"],
                "colorless": len([card for card in cards if not card.colors])
            }
        }

    def _create_combined_data(self, theme: str, cards: List[Card], stats: Dict) -> Dict:
        """Create the final combined data structure."""
        return {
            "set_info": {
                "theme": theme,
                "generation_date": datetime.datetime.now().isoformat(),
                "config": {
                    "inspiration_cards_count": self.config.inspiration_cards_count,
                    "total_cards": self.config.batches_count * self.config.cards_per_batch,
                    "rarity_distribution": {
                        "mythic_per_batch": self.config.mythics_per_batch,
                        "rare_per_batch": self.config.rares_per_batch,
                        "uncommon_per_batch": self.config.uncommons_per_batch,
                        "common_per_batch": self.config.commons_per_batch
                    },
                    "target_color_distribution": self.config.color_distribution
                },
                **stats
            },
            "cards": [card.to_dict() for card in cards]
        }

    def _print_statistics(self, stats: Dict) -> None:
        """Print set statistics."""
        print("\n=== Set Statistics ===")
        print(f"Total cards: {stats['card_count']}")

        print("\nRarity Distribution:")
        for rarity, count in stats['rarity_distribution'].items():
            print(f"- {rarity.capitalize()}: {count}")

        print("\nColor Distribution:")
        for color, count in stats['color_distribution'].items():
            print(f"- {color}: {count}")


async def main():
    # Set configuration
    config = Config(
        csv_file_path="./assets/mtg_cards_english.csv",
        inspiration_cards_count=100,  # Number of cards to use as inspiration
        batches_count=20,  # Number of batches to generate, 20 batches gives you a full set of 260 cards
        cards_per_batch=13,  # Cards per batch

        # Rarity distribution per batch
        mythics_per_batch=1,
        rares_per_batch=3,
        uncommons_per_batch=4,
        commons_per_batch=5,

        # Color balance target (percentage)
        color_distribution={
            "W": 0.2,  # White
            "U": 0.2,  # Blue
            "B": 0.2,  # Black
            "R": 0.2,  # Red
            "G": 0.2  # Green
        }
    )

    # Create and run orchestrator
    orchestrator = MTGGeneratorOrchestrator(config)
    await orchestrator.generate_complete_set()


if __name__ == "__main__":
    asyncio.run(main())

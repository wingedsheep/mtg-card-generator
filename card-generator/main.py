import json
import datetime
import asyncio
from typing import Dict, List
from collections import Counter

from models import Config, Card
# Strategies will be created via Config object
# from mtg_set_generator import MTGSetGenerator # Will be initialized with strategies
# from mtg_art_generator import MTGArtGenerator
# from mtg_json_converter import MTGJSONConverter
from mtg_card_renderer import MTGCardRenderer # Assuming this doesn't need LM/Image strategies for now
from mtg_land_generator import MTGLandGenerator # Assuming this primarily uses MTGArtGenerator


class MTGGeneratorOrchestrator:
    def __init__(self, config: Config):
        self.config = config # Config object now handles strategy creation

        # Create strategies via the Config object
        self.language_model_strategy = self.config.create_language_model_strategy()
        self.image_generator_strategy = self.config.create_image_generator_strategy()

        # Initialize components, passing the strategies to them
        # Need to import the classes here or ensure they are available
        from mtg_set_generator import MTGSetGenerator
        from mtg_json_converter import MTGJSONConverter

        self.set_generator = MTGSetGenerator(config, self.language_model_strategy)
        self.json_converter = MTGJSONConverter(config, self.language_model_strategy)
        self.card_renderer = MTGCardRenderer(config) # Renderer might not directly use these strategies

        # Art generator will be initialized after we have the theme, and will need both strategies
        self.art_generator = None

        # Track the collector number counter to pass to land generator
        self.collector_number_counter = 1

    async def generate_complete_set(self) -> Dict:
        """Generate a complete MTG set including cards, art, and rendered images.
        Process each batch completely (cards, art, rendering) before moving to the next batch."""
        print("\n=== Starting MTG Set Generation ===")

        from mtg_art_generator import MTGArtGenerator # Import here for late initialization

        # Initialize the set (load inspiration cards and generate theme using LM strategy)
        print("\n--- Initializing Set ---")
        self.set_generator.initialize_set() # This now uses the LM strategy for theme

        # Get the theme for art generation
        theme = self.set_generator.set_theme

        # Initialize art generator with theme and strategies
        self.art_generator = MTGArtGenerator(
            self.config,
            theme,
            self.language_model_strategy, # For art prompts
            self.image_generator_strategy  # For image generation
        )

        # Process each batch completely
        all_processed_cards = []

        for batch_num in range(1, self.config.batches_count + 1):
            print(f"\n=== Processing Batch {batch_num}/{self.config.batches_count} ===")

            # Step 1: Generate batch of cards
            print(f"\n--- Generating Cards for Batch {batch_num} ---")
            batch_cards = self.set_generator.generate_batch_cards(batch_num)

            # Step 2: Generate art for this batch
            print(f"\n--- Generating Art for Batch {batch_num} ---")
            cards_with_art = self.art_generator.process_cards(batch_cards)
            all_processed_cards.extend(cards_with_art)

            # Step 3: Convert this batch to rendering format
            print(f"\n--- Converting Batch {batch_num} to Rendering Format ---")
            render_json_paths = self.json_converter.convert_cards(
                cards_with_art,
                self.config.output_dir
            )

            # Step 4: Render cards from this batch as images
            print(f"\n--- Rendering Cards for Batch {batch_num} ---")
            await self.card_renderer.render_card_files(render_json_paths)

            # Save intermediate progress after each batch
            print(f"\n--- Saving Progress for Batch {batch_num} ---")
            stats = self._calculate_statistics(all_processed_cards)
            combined_data = self._create_combined_data(theme, all_processed_cards, stats)
            self._save_batch_data(combined_data, batch_num)

            # Print statistics for this batch
            print(f"\n--- Statistics after Batch {batch_num} ---")
            self._print_statistics(stats)

            # Update collector number counter for lands
            if batch_cards:
                # Find the highest collector number in the set so far
                max_collector_num = max(
                    int(card.collector_number) if card.collector_number.isdigit() else 0
                    for card in all_processed_cards
                )
                self.collector_number_counter = max_collector_num + 1

        # Generate basic lands if enabled
        if self.config.generate_basic_lands:
            print("\n=== Generating Basic Lands ===")
            # Pass the current collector number to continue from where we left off
            land_generator = MTGLandGenerator(self.config, theme, self.collector_number_counter)
            land_cards = land_generator.generate_basic_lands()

            # Add lands to the processed cards
            all_processed_cards.extend(land_cards)

            # Convert lands to rendering format
            print("\n--- Converting Lands to Rendering Format ---")
            land_render_paths = self.json_converter.convert_cards(
                land_cards,
                self.config.output_dir
            )

            # Render land cards
            print("\n--- Rendering Land Cards ---")
            await self.card_renderer.render_card_files(land_render_paths)

        # Compile and save final complete set data
        print("\n=== Finalizing Set ===")
        final_stats = self._calculate_statistics(all_processed_cards)
        final_data = self._create_combined_data(theme, all_processed_cards, final_stats)
        self._save_final_data(final_data)

        print("\n=== Set Generation Complete ===")
        print(f"Total cards: {len(all_processed_cards)}")

        return final_data

    def _load_generated_cards(self) -> tuple[str, List[Card]]:
        """Load the generated card set."""
        output_path = self.config.get_output_path("mtg_set_output.json")
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            theme = data["theme"]
            cards = [Card.from_dict(card_data) for card_data in data["cards"]]
        return theme, cards

    def _save_batch_data(self, data: Dict, batch_num: int) -> None:
        """Save the data for a specific batch."""
        output_path = self.config.get_output_path(f"mtg_set_batch_{batch_num}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\nBatch {batch_num} data saved to {output_path}")

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
                "mythic": rarity_counts.get("Mythic Rare", 0),
                "rare": rarity_counts.get("Rare", 0),
                "uncommon": rarity_counts.get("Uncommon", 0),
                "common": rarity_counts.get("Common", 0)
            },
            "color_distribution": {
                "W": color_counts.get("W", 0),
                "U": color_counts.get("U", 0),
                "B": color_counts.get("B", 0),
                "R": color_counts.get("R", 0),
                "G": color_counts.get("G", 0),
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
                    "total_cards": self.config.batches_count * (
                            self.config.mythics_per_batch + self.config.rares_per_batch + self.config.uncommons_per_batch + self.config.commons_per_batch),
                    "theme_prompt": self.config.theme_prompt,
                    "rarity_distribution": {
                        "mythic_per_batch": self.config.mythics_per_batch,
                        "rare_per_batch": self.config.rares_per_batch,
                        "uncommon_per_batch": self.config.uncommons_per_batch,
                        "common_per_batch": self.config.commons_per_batch
                    },
                    "target_color_distribution": self.config.color_distribution,
                    "models": {
                        "main": self.config.main_model,
                        "json": self.config.json_model,
                        "image": self.config.image_model
                    },
                    "basic_lands": {
                        "enabled": self.config.generate_basic_lands,
                        "variations_per_type": self.config.land_variations_per_type
                    }
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
    # Example complete theme override (you can pass your own theme text here)
    complete_theme = """
    # The Shattered Realms of Eltarion

    ## World Description
    Eltarion was once a harmonious world where five elemental planes intersected in perfect balance. A cataclysmic event called the Convergence shattered this unity, creating unstable overlapping zones where the elemental powers chaotically blend. The denizens of each realm now struggle to survive in this fractured landscape, forming uneasy alliances or waging territorial wars.

    ## Key Factions
    - The Luminari Conclave (White): Scholars and mages who seek to restore balance through knowledge and order
    - The Tidecallers (Blue): Adaptable mystics who harness the unpredictable flow of mana through the shattered realms
    - The Shadowbond Covenant (Black): Opportunists who believe only the strongest should survive and rule the new world
    - The Volcanic Warband (Red): Passionate warriors embracing the chaos as a path to freedom and self-expression
    - The Wildgrowth Collective (Green): Druids and beasts attempting to heal the natural order through aggressive restoration

    ## Creature Types
    The set prominently features Elementals, Wizards, Warriors, Spirits, Beasts, Angels, Demons, Dragons, Merfolk, and Elves, with many creatures exhibiting hybrid characteristics from the blending of realms.

    ## Mechanical Themes
    - "Convergence" cards that gain additional effects when you control lands of different types
    - Multicolor emphasis reflecting the blending of elemental powers
    - Land transformation and land-matters mechanics
    - Tribal elements for the major factions
    - Exile and return mechanics representing the unstable nature of reality

    ## Synergies
    - Land-based ramp strategies that power multicolor threats
    - Faction-based tribal synergies with cross-faction hybrid creatures
    - Control strategies using reality-warping exile effects
    - Aggressive decks exploiting elemental chaos effects

    ## Play Styles
    The set supports aggressive tribal strategies, midrange value-generating decks, controlling reality-manipulation decks, and five-color convergence ramp decks.
    """

    # Set configuration
    config = Config(
        csv_file_path="./assets/mtg_cards_english.csv",
        inspiration_cards_count=50,  # Number of cards to use as inspiration
        batches_count=20,  # Number of batches to generate

        # Optional theme prompt (will be ignored if complete_theme_override is provided)
        theme_prompt="Varied set with many of the creature types from MTG included, don't include anything with time or dimensions in the theme",

        # Uncomment the line below to use a complete theme override instead of generating one
        # complete_theme_override=complete_theme,

        # Basic land generation
        generate_basic_lands=True,
        land_variations_per_type=3,

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
        },

        # Image generation model and language model choices are now primarily in settings.json
        # The `image_model` field in Config is removed; strategy is chosen from settings.
        # `main_model` and `json_model` in Config are also removed.
    )

    # Create and run orchestrator
    # The Config object will load settings from "card-generator/settings.json" (or example)
    # and will be used to create the appropriate strategies.
    orchestrator = MTGGeneratorOrchestrator(config)
    await orchestrator.generate_complete_set()


if __name__ == "__main__":
    # Ensure settings.json exists or copy from settings.example.json
    # This is a good place for a small check or instruction to the user.
    import pathlib
    settings_file = pathlib.Path("card-generator/settings.json")
    example_settings_file = pathlib.Path("card-generator/settings.example.json")
    if not settings_file.exists() and example_settings_file.exists():
        print(f"'{settings_file}' not found. Please copy '{example_settings_file}' to '{settings_file}' "
              "and configure your API keys and model preferences.")
        # For automated environments or first run, you might choose to auto-copy:
        # import shutil
        # shutil.copy(example_settings_file, settings_file)
        # print(f"Copied example settings to '{settings_file}'. Please review and configure.")

    asyncio.run(main())

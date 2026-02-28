from typing import List
from models import Card, Config
from language_model_strategies import LanguageModelStrategy
from prompts import build_land_art_prompt


class MTGLandGenerator:
    def __init__(self, config: Config, theme: str, start_collector_number: int = None,
                 language_model_strategy: LanguageModelStrategy = None,
                 image_generator_strategy=None,
                 art_generator=None):
        self.config = config
        self.theme = theme

        self.language_model = language_model_strategy or config.create_language_model_strategy()

        # Prefer using the shared art generator when provided
        self.art_generator = art_generator

        # Fall back to creating an image generator directly (legacy path)
        if self.art_generator is None and image_generator_strategy is not None:
            self._image_generator = image_generator_strategy
        elif self.art_generator is None:
            self._image_generator = config.create_image_generator_strategy()
        else:
            self._image_generator = None

        self.land_types = ["Plains", "Island", "Swamp", "Mountain", "Forest"]
        self.land_colors = {"Plains": "W", "Island": "U", "Swamp": "B", "Mountain": "R", "Forest": "G"}
        # Use the passed collector number if provided, otherwise default to 500
        self.collector_number_counter = start_collector_number if start_collector_number is not None else 500

    def generate_land_prompt(self, land_type: str) -> str:
        """Generate a unique art prompt for a basic land."""
        prompt = build_land_art_prompt(land_type, self.theme)
        return self.language_model.generate_text(
            prompt=prompt,
            system_prompt="You are an expert MTG art prompt generator.",
            model_key="art_prompt_generation"
        )

    def generate_land_card(self, land_type: str, variation: int) -> Card:
        """Create a Card object for a basic land."""
        card = Card(
            name=f"{land_type} {variation}",
            mana_cost="",
            type=f"Basic Land — {land_type}",
            rarity="Common",
            text="",
            flavor="",
            colors=[self.land_colors.get(land_type, "")],
            power=None,
            toughness=None,
            loyalty=None,
            set_name="",
            art_prompt=None,
            image_path=None,
            collector_number=str(self.collector_number_counter),
            description=f"A {land_type.lower()} from which {self.land_colors.get(land_type, '')} mana can be drawn. Variation {variation}."
        )
        self.collector_number_counter += 1
        return card

    def _process_land_art(self, land_card: Card) -> None:
        """Generate art and save card data, delegating to art_generator when available."""
        if self.art_generator is not None:
            # Delegate to the shared art generator — it will see that art_prompt is
            # already set and skip prompt generation, going straight to image generation.
            self.art_generator.process_card(land_card)
        else:
            # Legacy path: use the image generator directly
            try:
                print(f"Generating art for {land_card.name} using image strategy...")
                image_name = f"{land_card.name.replace(' ', '_')}.png"
                saved_image_path = self._image_generator.generate_image(
                    art_prompt=land_card.art_prompt,
                    card=land_card,
                    output_dir=self.config.output_dir,
                    image_name=image_name,
                )
                if saved_image_path:
                    land_card.image_path = saved_image_path
                    print(f"  Saved image to {saved_image_path}")
                else:
                    print(f"  Warning: Failed to generate image for {land_card.name}")
            except Exception as e:
                print(f"Failed to generate land art for {land_card.name}: {str(e)}")

            # Save card JSON (art generator does this automatically when used)
            self.art_generator_save_card(land_card)

    def art_generator_save_card(self, card: Card) -> None:
        """Save land card data to a JSON file (used in legacy path only)."""
        import json
        card_dict = card.to_dict()
        json_path = self.config.get_output_path(f"{card.name.replace(' ', '_')}.json")
        card_data = {"card": card_dict}
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(card_data, f, indent=2)

    def generate_basic_lands(self) -> List[Card]:
        """Generate all basic land variations for the set."""
        print("\n=== Generating Basic Lands ===")
        all_lands = []

        for land_type in self.land_types:
            print(f"\nGenerating {self.config.land_variations_per_type} variations of {land_type}")

            for variation in range(1, self.config.land_variations_per_type + 1):
                print(f"  Processing {land_type} variation {variation}...")

                # Create the land card with variation number
                land_card = self.generate_land_card(land_type, variation)

                # Generate the specialized land art prompt
                art_prompt = self.generate_land_prompt(land_type)
                land_card.art_prompt = art_prompt
                print(f"  Generated art prompt for {land_card.name}")

                # Generate art and save card data
                self._process_land_art(land_card)

                all_lands.append(land_card)

        print(f"\nGenerated {len(all_lands)} basic land variations")
        return all_lands

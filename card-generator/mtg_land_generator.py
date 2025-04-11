import json
from pathlib import Path
import replicate
from typing import List, Dict
from models import Card, Config


class MTGLandGenerator:
    def __init__(self, config: Config, theme: str):
        self.config = config
        self.theme = theme
        self.client = config.openai_client
        self.land_types = ["Plains", "Island", "Swamp", "Mountain", "Forest"]
        self.land_colors = {"Plains": "W", "Island": "U", "Swamp": "B", "Mountain": "R", "Forest": "G"}
        self.collector_number_counter = 500  # Start land collection numbers at 500

    def generate_land_prompt(self, land_type: str, variation_number: int) -> str:
        """Generate a unique art prompt for a basic land."""
        prompt = f"""Create a detailed art prompt for a {land_type} basic land card in Magic: The Gathering.

Set Theme Context:
{self.theme}

This is variation #{variation_number} of the {land_type} for this set. Make it unique and distinct from other variations while still fitting the overall set theme.

Create a vivid, detailed scene that captures the essence of a {land_type}. The art should reflect the color identity and mana characteristics of this land type, while incorporating elements from the set's theme.

The prompt should begin with "Oil on canvas painting. Magic the gathering art. Detailed landscape." and should include elements that make this land distinctly a {land_type} while fitting the theme.

Focus on:
- The landscape features typical of a {land_type}
- The mood and atmosphere that reflects the land's color identity
- How this landscape connects to the set's theme
- What makes this variation unique from other versions of the same land type
- Environmental details, weather conditions, time of day, and lighting that create a distinctive scene
- Any characteristic flora, fauna, or geographical elements associated with this land type

Example land art prompts:

Example 1 (Mountain): "Oil on canvas painting. Magic the gathering art. Detailed landscape. Jagged crimson peaks emerging from mist, with streams of molten lava creating veins of orange light down their faces. The mountain range extends into the distance, with storm clouds gathering above. Lightning strikes illuminate the rugged terrain, revealing ancient dwarven ruins carved into the cliffs. Towering obsidian formations jut from the mountainside, their surfaces reflecting the red glow of sunrise. Small geysers of steam and fire erupt periodically across the mountain face."

Example 2 (Island): "Oil on canvas painting. Magic the gathering art. Detailed landscape. A secluded cove surrounded by towering blue-crystal formations that rise from turquoise waters. Spiral-shaped coral formations emit an ethereal blue glow beneath the water's surface. A small rocky island at the center features a twisted, wind-sculpted tree with luminescent blue leaves. Mist hangs over the waters, creating an otherworldly atmosphere. The sky above displays unusual cloud formations that mirror the spiral patterns in the water below, with a faint blue sun visible through the haze."

Return only the art prompt text with no additional explanation."""

        completion = self.client.chat.completions.create(
            extra_headers=self.config.api_headers,
            model=self.config.main_model,
            messages=[{"role": "user", "content": prompt}]
        )

        return completion.choices[0].message.content

    def generate_land_card(self, land_type: str, variation_number: int) -> Card:
        """Create a Card object for a basic land."""
        card = Card(
            name=f"{land_type} {variation_number}",
            mana_cost="",
            type=f"Basic Land — {land_type}",
            rarity="Common",
            text="",
            flavor="",
            colors=[self.land_colors.get(land_type, "")],
            power=None,
            toughness=None,
            authority=None,
            set_name="",
            art_prompt=None,
            image_path=None,
            collector_number=str(self.collector_number_counter),
            description=f"A {land_type.lower()} from which {self.land_colors.get(land_type, '')} mana can be drawn."
        )
        self.collector_number_counter += 1
        return card

    def generate_land_art(self, card: Card, art_prompt: str) -> bytes:
        """Generate art for a land card using Replicate."""
        try:
            # Generate image using the prompt with Replicate model
            image_response = replicate.run(
                self.config.replicate_model,
                input={
                    "prompt": art_prompt,
                    "aspect_ratio": "5:4",
                    "safety_tolerance": 6,
                    "prompt_upsampling": True
                }
            )

            return image_response
        except Exception as e:
            print(f"Failed to generate land art: {str(e)}")
            return b""

    def save_land_card(self, card: Card) -> Path:
        """Save land card data to a JSON file and return the path."""
        card_dict = card.to_dict()
        json_path = self.config.get_output_path(f"{card.name.replace(' ', '_')}.json")

        # Wrap the card data in the format expected by the converter
        card_data = {"card": card_dict}

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(card_data, f, indent=2)

        return json_path

    def generate_basic_lands(self) -> List[Card]:
        """Generate all basic land variations for the set."""
        print("\n=== Generating Basic Lands ===")
        all_lands = []

        for land_type in self.land_types:
            print(f"\nGenerating {self.config.land_variations_per_type} variations of {land_type}")

            for variation in range(1, self.config.land_variations_per_type + 1):
                print(f"  Processing {land_type} variation {variation}...")

                # Create the land card
                land_card = self.generate_land_card(land_type, variation)

                # Generate art prompt
                art_prompt = self.generate_land_prompt(land_type, variation)
                land_card.art_prompt = art_prompt
                print(f"  Generated art prompt for {land_card.name}")

                # Generate and save art
                image_data = self.generate_land_art(land_card, art_prompt)

                # Save image if generation was successful
                if image_data:
                    image_path = self.config.get_output_path(f"{land_card.name.replace(' ', '_')}.png")
                    with open(image_path, "wb") as f:
                        f.write(image_data.read())
                    land_card.image_path = str(image_path)
                    print(f"  Saved image to {image_path}")

                # Save land card data
                self.save_land_card(land_card)
                print(f"  Saved land card data for {land_card.name}")

                all_lands.append(land_card)

        print(f"\nGenerated {len(all_lands)} basic land variations")
        return all_lands

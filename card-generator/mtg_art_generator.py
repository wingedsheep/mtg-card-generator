import json
from pathlib import Path
import replicate
from models import Card, Config
from PIL import Image
from io import BytesIO


class MTGArtGenerator:
    def __init__(self, config: Config, theme: str = None):
        self.config = config
        self.theme = theme

        # Use the client from the config
        self.client = config.openai_client

    def generate_art_prompt(self, card: Card, attempt: int = 0) -> str:
        """Generate an art prompt for a given card using OpenRouter API."""
        theme_context = f"""Set Theme Context:
{self.theme}

Consider this theme when creating the art prompt. The art should reflect both the card's individual characteristics and the overall set theme.""" if self.theme else ""

        prompt = f"""Create a detailed art prompt for a Magic: The Gathering card with the following details:

Theme:
{theme_context}

Card Name: {card.name}
Type: {card.type}
Rarity: {card.rarity}
Card Text: {card.text}
Flavor Text: {card.flavor}
Colors: {', '.join(card.colors) if card.colors else 'Colorless'}
Power/Toughness: {card.power}/{card.toughness} (if applicable)
Description: {card.description}

Look at all the details of the card, like the type, rarity, card text, flavor text, colors, and power/toughness when creating the art prompt.

Make sure that the prompt fits the style of Magic: The Gathering art and captures the essence of the card.
Say something about the composition, lighting, mood, and important details in the art prompt.

{f"Please make sure it is a really SAFE prompt! Don't include words that could trigger the NSFW filters. This is crucial." if attempt > 1 else ""} 

The prompt should begin with "Oil on canvas painting. Magic the gathering art. Rough brushstrokes."
Focus on creating a vivid, detailed scene that captures the essence of the card's mechanics and flavor.
The description should be specific about composition, lighting, mood, and important details.
Include details about the art style and technical aspects at the end.

Create something unique, and add a touch of your own creativity to the prompt.

If a character name is present, make sure to include their full name in the prompt.
Make sure the prompt fits the theme context provided above.

Example prompt: 

``` 
Example 1:
Oil on canvas painting. Magic the gathering art. Rough brushstrokes. A wild-eyed goblin wizard perches atop a 
rock formation in his cave laboratory. His unkempt red hair stands on end, burning at the tips with magical fire that 
doesn't harm him. Red mana crackles like lightning around his hands, and his tattered robes smoke from magical 
mishaps. Behind him, a contraption of copper pipes, glass tubes, and crystals spews chaotic flame. Burning spell 
scrolls float around him as he grins with manic glee, his experiment spiraling out of control. The cave walls reflect 
orange-red firelight, and burnt artifacts litter the ground. Small explosions pop like magical fireworks in the 
background. Crisp details emphasize the chaotic energy and magical power, particularly in the interplay of fire and 
magical effects. Wizard. Oil on canvas artwork.

Example 2: Oil on canvas painting. Magic the gathering art. Rough brushstrokes. Ancient forest grove bathed in 
emerald light. Massive moss-covered tree roots form archways over clear pools. Glowing white flowers spiral across 
the forest floor. Ethereal mist and crystal formations weave between towering trunks. Oil on canvas with rough 
brushstrokes, Magic: The Gathering style. Emphasis on natural patterns and dappled light through the canopy. Oil on 
canvas artwork. 
``` 

{f"Don't put any words in the prompt that might be considered harmful by anyone. Make it really safe!" if attempt > 4 else ""}

Return only the prompt text with no additional explanation."""

        completion = self.client.chat.completions.create(
            extra_headers=self.config.api_headers,
            model=self.config.main_model,
            messages=[{"role": "user", "content": prompt}]
        )

        return completion.choices[0].message.content

    def save_card_data(self, card: Card, prompt: str, image_path: Path) -> None:
        """Save card data and prompt to JSON."""
        # Get card data as dictionary
        card_dict = card.to_dict()

        # Wrap the card data in the format expected by the converter
        # This matches the format used in mtg_land_generator.py
        output_data = {"card": card_dict}

        json_path = self.config.get_output_path(f"{card.name.replace(' ', '_')}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)

    def crop_to_5x4_ratio(self, image_data):
        """Crop an image to 5:4 aspect ratio, keeping the center portion.

        Args:
            image_data: Image data as bytes

        Returns:
            bytes: The cropped image data
        """
        # Open the image using PIL
        image = Image.open(BytesIO(image_data))
        width, height = image.size

        # Calculate current aspect ratio
        current_ratio = width / height
        target_ratio = 5 / 4

        if abs(current_ratio - target_ratio) < 0.01:
            # Already close enough to 5:4, return as-is
            return image_data

        # Calculate new dimensions
        if current_ratio > target_ratio:
            # Image is too wide - crop width
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            right = left + new_width
            cropped_image = image.crop((left, 0, right, height))
        else:
            # Image is too tall - crop height
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            bottom = top + new_height
            cropped_image = image.crop((0, top, width, bottom))

        # Convert back to bytes
        output = BytesIO()
        cropped_image.save(output, format=image.format or 'PNG')
        return output.getvalue()

    def generate_card_art(self, card: Card, max_retries: int = 5, retry_delay: int = 3) -> tuple[str, bytes]:
        """Generate both art prompt and image for a card with retry logic.

        Args:
            card: The card to generate art for
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Delay between retries in seconds (default: 5)

        Returns:
            tuple[str, bytes]: The successful art prompt and image data

        Raises:
            Exception: If all retry attempts fail
        """
        import time

        for attempt in range(max_retries):
            try:
                # Generate art prompt
                art_prompt = self.generate_art_prompt(card, attempt)
                print(f"Generated art prompt (attempt {attempt + 1}): {art_prompt}...")

                # Get the active Replicate model
                active_model = self.config.get_active_replicate_model()
                print(f"Using image model: {active_model}")

                # Configure model-specific parameters
                model_params = self._get_model_params(art_prompt)

                # Keep track of the original aspect ratio for later processing
                original_aspect_ratio = model_params.get("aspect_ratio", "5:4")

                # Generate image using the prompt with selected Replicate model
                image_response = replicate.run(
                    active_model,
                    input=model_params
                )

                # Convert response to bytes
                if hasattr(image_response, 'read'):
                    image_data = image_response.read()
                else:
                    # If it's a URL or other format
                    import requests
                    image_data = requests.get(image_response).content

                # Check if we need to crop (only if aspect ratio != 5:4)
                if original_aspect_ratio != "5:4":
                    print(f"Cropping image from {original_aspect_ratio} to 5:4...")
                    image_data = self.crop_to_5x4_ratio(image_data)

                # Create a BytesIO object that behaves like a file
                return art_prompt, BytesIO(image_data)

            except Exception as e:
                if attempt == max_retries - 1:  # Last attempt
                    print(f"Failed to generate art after {max_retries} attempts: {str(e)}")
                    return "", BytesIO(b"")
                else:
                    print(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)

    def _get_model_params(self, prompt: str) -> dict:
        """Get model-specific parameters based on the selected image model."""
        active_model_name = self.config.image_model

        if active_model_name == "flux":
            return {
                "prompt": prompt,
                "aspect_ratio": "5:4",
                "safety_tolerance": 6,
                "prompt_upsampling": True
            }
        elif active_model_name == "imagen":
            return {
                "prompt": prompt,
                "aspect_ratio": "4:3",  # Keep original aspect ratio for generation
                "safety_filter_level": "block_only_high"
            }
        else:
            # Default to Flux parameters
            return {
                "prompt": prompt,
                "aspect_ratio": "5:4",
                "safety_tolerance": 6,
                "prompt_upsampling": True
            }

    def process_card(self, card: Card) -> Card:
        """Process a single card, generating art and saving data."""
        print(f"\nProcessing card: {card.name}")

        # Generate art prompt and image
        print("Generating art and image...")
        art_prompt, image_response = self.generate_card_art(card)

        # Save image
        image_path = self.config.get_output_path(f"{card.name.replace(' ', '_')}.png")
        with open(image_path, "wb") as f:
            f.write(image_response.read())
        print(f"Image saved to {image_path}")

        # Update card with art data
        card.art_prompt = art_prompt
        card.image_path = str(image_path)

        # Save card data
        self.save_card_data(card, art_prompt, image_path)
        print(f"Card data saved")

        return card

    def process_cards(self, cards: list[Card]) -> list[Card]:
        """Process a list of cards, generating art and saving data."""
        processed_cards = []
        for card in cards:
            processed_card = self.process_card(card)
            processed_cards.append(processed_card)
        return processed_cards

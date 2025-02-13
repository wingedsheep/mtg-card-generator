import json
from pathlib import Path
from openai import OpenAI
import replicate
from models import Card, Config


class MTGArtGenerator:
    def __init__(self, config: Config, theme: str = None):
        self.config = config
        self.theme = theme
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

    def _initialize_output_dir(self) -> Path:
        """Initialize and return the output directory."""
        output_dir = Path("./output")
        output_dir.mkdir(exist_ok=True)
        return output_dir

    def generate_art_prompt(self, card: Card, attempt: int = 0) -> str:
        """Generate an art prompt for a given card using OpenRouter."""
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
            extra_headers={
                "HTTP-Referer": "https://example.com",
                "X-Title": "MTG Art Generator"
            },
            model="openai/chatgpt-4o-latest",
            messages=[{"role": "user", "content": prompt}]
        )

        return completion.choices[0].message.content

    def save_card_data(self, card: Card, prompt: str, image_path: Path) -> None:
        """Save card data and prompt to JSON."""
        output_data = {
            "card": card.to_dict(),
            "art_prompt": prompt,
            "image_path": str(image_path)
        }

        json_path = self.config.get_output_path(f"{card.name.replace(' ', '_')}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)

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
                print(f"Generated art prompt (attempt {attempt + 1}): {art_prompt[:100]}...")

                # Generate image using the prompt
                image_response = replicate.run(
                    "black-forest-labs/flux-1.1-pro",
                    input={
                        "prompt": art_prompt,
                        "aspect_ratio": "5:4",
                        "safety_tolerance": 6,
                        "prompt_upsampling": True
                    }
                )

                return art_prompt, image_response

            except Exception as e:
                if attempt == max_retries - 1:  # Last attempt
                    print(f"Failed to generate art after {max_retries} attempts: {str(e)}")
                    return "", b""
                else:
                    print(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)

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
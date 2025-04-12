from pathlib import Path
import json
import asyncio
from playwright.async_api import async_playwright
from models import Config


class MTGCardRenderer:
    def __init__(self, config: Config):
        self.config = config
        self.renderer_path = Path("../card-rendering")
        self.complete_html_path = self.renderer_path / "index.html"

    async def render_cards(self):
        """Render all cards in the render_format directory to PNG images."""
        print("\n=== Rendering Cards as Images ===")

        # Get path to render format directory
        render_dir = self.config.output_dir / "render_format"
        if not render_dir.exists():
            raise FileNotFoundError(f"Render format directory not found at {render_dir}")

        # Gather all render JSON files
        json_files = list(render_dir.glob("*_render.json"))
        return await self.render_card_files(json_files)

    async def render_card_files(self, json_files):
        """Render a list of specific card JSON files."""
        if not json_files:
            print("No card files to render")
            return []

        rendered_images = []

        async with async_playwright() as p:
            # Launch browser with a larger viewport
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={'width': 1600, 'height': 2400})

            # Load the renderer page
            await page.goto(f"file://{self.complete_html_path.absolute()}")

            # Process each JSON file
            for json_file in json_files:
                print(f"\nRendering {json_file.stem}...")

                try:
                    # Reload the page before processing each card
                    await page.reload()
                    await page.wait_for_load_state('networkidle')

                    # Load and parse the card JSON
                    with open(json_file, 'r', encoding='utf-8') as f:
                        card_data = json.load(f)

                    # Fill the textarea with the card JSON
                    await page.fill('#card-json', json.dumps(card_data, indent=2))

                    # Allow a short delay for the content to be processed
                    await page.wait_for_timeout(500)

                    # Click the render button
                    await page.click('#render-button')

                    # Wait for the card element to render
                    await page.wait_for_selector('.mtg-card')

                    # Apply a CSS transform to scale the .mtg-card element by 4
                    await page.evaluate('''
                        () => {
                            const card = document.querySelector('.mtg-card');
                            if (card) {
                                card.style.transform = 'scale(4)';
                                card.style.transformOrigin = 'top left';
                            }
                        }
                    ''')

                    # Wait a short moment to allow the transform to take effect
                    await page.wait_for_timeout(500)

                    # Retrieve the .mtg-card element
                    card_element = await page.query_selector('.mtg-card')
                    if card_element:
                        # Create images directory if it doesn't exist
                        images_dir = self.config.output_dir / "card_images"
                        images_dir.mkdir(exist_ok=True)

                        # Define output image path - Use original_name if it exists, otherwise use name
                        # This ensures basic land variations get unique filenames
                        if "original_name" in card_data:
                            output_filename = card_data["original_name"].replace(' ', '_')
                        else:
                            output_filename = card_data["name"].replace(' ', '_')

                        output_path = images_dir / f"{output_filename}.png"

                        # Get the original bounding box of the element
                        box = await card_element.bounding_box()
                        if box:
                            clip_region = {
                                "x": box["x"],
                                "y": box["y"],
                                "width": box["width"],
                                "height": box["height"],
                            }
                            await page.screenshot(
                                path=str(output_path),
                                clip=clip_region,
                                type='png',
                                omit_background=True,
                                animations='disabled'
                            )
                            print(f"Saved high-quality card image to {output_path}")
                            rendered_images.append(output_path)
                        else:
                            print(f"Error: Could not retrieve bounding box for {json_file.name}")
                    else:
                        print(f"Error: Could not find rendered card element for {json_file.name}")

                except Exception as e:
                    print(f"Error rendering {json_file.name}: {str(e)}")

            await browser.close()

        return rendered_images

    @staticmethod
    async def render_cards_main(config: Config):
        """Static method to create and run the renderer."""
        renderer = MTGCardRenderer(config)
        await renderer.render_cards()


# Example usage if run directly to render from a json to a png
if __name__ == "__main__":
    json_example = {
        "name": "Calaveth, Shifting Pariah",
        "layout": "normal",
        "collector_number": "5",
        "image_uris": {
            "art_crop": "../card-generator/output/20250213_213401/Calaveth,_Shifting_Pariah.png"
        },
        "mana_cost": "{1}{U}{R}",
        "type_line": "Legendary Creature - Human Shapeshifter",
        "oracle_text": "Prowess\n\n{R}, Exile Calaveth: Return it to the battlefield at the beginning of the next end step.\n\nWhenever Calaveth returns from exile, it gains your choice of first strike, menace, or flying until end of turn.",
        "colors": [
            "UR"
        ],
        "set": "thb",
        "rarity": "uncommon",
        "artist": "Vincent Bons",
        "power": "3",
        "toughness": "3",
        "flavor_text": "\"I never lose. I just leave before I get caught.\""
    }

    config_example = Config()
    config_example.output_dir = Path("output/example_set")
    config_example.output_dir.mkdir(exist_ok=True)
    render_format_dir = config_example.output_dir / "render_format"
    render_format_dir.mkdir(exist_ok=True)
    with open(render_format_dir / "example_render.json", "w", encoding="utf-8") as f:
        json.dump(json_example, f, indent=2)

    mtg_card_renderer = MTGCardRenderer(config_example)
    asyncio.run(mtg_card_renderer.render_cards_main(config_example))

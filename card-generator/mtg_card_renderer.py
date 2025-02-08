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

        async with async_playwright() as p:
            # Launch browser with a larger viewport
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={'width': 1600, 'height': 2400})

            # Load the renderer page
            await page.goto(f"file://{self.complete_html_path.absolute()}")

            # Process each JSON file in the render format directory
            for json_file in render_dir.glob("*_render.json"):
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
                    await page.wait_for_timeout(1000)

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

                        # Define output image path
                        output_path = images_dir / f"{card_data['name'].replace(' ', '_')}.png"

                        # Get the original bounding box of the element
                        box = await card_element.bounding_box()
                        if box:
                            # Adjust the bounding box to account for the CSS scale transform (scale factor of 4)
                            clip_region = {
                                "x": box["x"],
                                "y": box["y"],
                                "width": box["width"] * 4,
                                "height": box["height"] * 4,
                            }
                            await page.screenshot(
                                path=str(output_path),
                                clip=clip_region,
                                type='png',
                                omit_background=True,
                                animations='disabled'
                            )
                            print(f"Saved high-quality card image to {output_path}")
                        else:
                            print(f"Error: Could not retrieve bounding box for {json_file.name}")
                    else:
                        print(f"Error: Could not find rendered card element for {json_file.name}")

                except Exception as e:
                    print(f"Error rendering {json_file.name}: {str(e)}")

            await browser.close()

    @staticmethod
    async def render_cards_main(config: Config):
        """Static method to create and run the renderer."""
        renderer = MTGCardRenderer(config)
        await renderer.render_cards()


# Example usage if run directly
if __name__ == "__main__":
    from main import Config

    config = Config(
        csv_file_path="./assets/mtg_cards_english.csv",
        inspiration_cards_count=50,
        batches_count=1,
        cards_per_batch=13,
        mythics_per_batch=1,
        rares_per_batch=3,
        uncommons_per_batch=4,
        commons_per_batch=5,
        color_distribution={
            "W": 0.2, "U": 0.2, "B": 0.2, "R": 0.2, "G": 0.2
        }
    )
    asyncio.run(MTGCardRenderer.render_cards_main(config))

#!/usr/bin/env python
import asyncio
from pathlib import Path
import os
import sys
import tkinter as tk
from tkinter import filedialog
import argparse
from typing import List, Optional

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the necessary modules
from models import Config
from mtg_card_renderer import MTGCardRenderer


async def rerender_cards(folder_path: str, renderer_path: str = None) -> List[Path]:
    """
    Re-render all MTG cards from JSON files in the render_format subfolder to the card_images subfolder.

    Args:
        folder_path: Path to the folder containing the render_format subfolder
        renderer_path: Optional path to the card-rendering directory

    Returns:
        List of paths to the rendered images
    """
    # Convert string path to Path object
    folder_path = Path(folder_path).resolve()

    print(f"Processing cards in folder: {folder_path}")

    # Check if the folder exists
    if not folder_path.exists() or not folder_path.is_dir():
        print(f"Error: {folder_path} is not a valid directory")
        return []

    # Check if render_format subfolder exists
    render_format_dir = folder_path / "render_format"
    if not render_format_dir.exists() or not render_format_dir.is_dir():
        print(f"Error: Could not find render_format directory in {folder_path}")
        return []

    # Create card_images subdirectory if it doesn't exist
    card_images_dir = folder_path / "card_images"
    card_images_dir.mkdir(exist_ok=True)

    # Find all render JSON files
    json_files = list(render_format_dir.glob("*_render.json"))
    if not json_files:
        print(f"No render JSON files found in {render_format_dir}")
        return []

    print(f"Found {len(json_files)} render JSON files")

    # Create a minimal config object with just the necessary settings
    config = Config()
    config.output_dir = folder_path

    # Create renderer
    renderer = MTGCardRenderer(config)

    # Override renderer path if provided, otherwise look in standard location
    if renderer_path:
        renderer_path = Path(renderer_path).resolve()
    else:
        # Try to locate the renderer in the expected relative path
        script_dir = Path(__file__).resolve().parent
        parent_dir = script_dir.parent
        standard_renderer_path = parent_dir.parent / "card-rendering"
        if standard_renderer_path.exists() and (standard_renderer_path / "index.html").exists():
            renderer_path = standard_renderer_path
        else:
            # Try one level up if not found
            alternative_renderer_path = parent_dir / "card-rendering"
            if alternative_renderer_path.exists() and (alternative_renderer_path / "index.html").exists():
                renderer_path = alternative_renderer_path

    # Set the renderer path if found
    if renderer_path:
        renderer.renderer_path = renderer_path
        renderer.complete_html_path = renderer.renderer_path / "index.html"

    # Check if renderer HTML exists
    if not renderer.complete_html_path.exists():
        print(f"Error: Renderer HTML not found at {renderer.complete_html_path}")
        print("Please provide the correct renderer path using the --renderer argument")
        return []

    print(f"Using renderer at: {renderer.complete_html_path}")

    # Render the cards
    rendered_images = await renderer.render_card_files(json_files)

    if rendered_images:
        print(f"\nSuccessfully rendered {len(rendered_images)} card images to {card_images_dir}")
    else:
        print("\nNo images were rendered. Check for errors above.")

    return rendered_images


def select_folder() -> Optional[str]:
    """
    Open a folder selection dialog and return the selected folder path.

    Returns:
        Optional[str]: Selected folder path or None if canceled
    """
    # Create a root window and hide it
    root = tk.Tk()
    root.withdraw()

    # Open folder selection dialog
    folder_path = filedialog.askdirectory(
        title="Select folder containing MTG card data",
        mustexist=True
    )

    # Destroy the root window
    root.destroy()

    return folder_path if folder_path else None


async def main():
    """Run the re-renderer with folder selection dialog."""
    # Parse command line arguments for optional renderer path
    parser = argparse.ArgumentParser(description="Re-render MTG card images from JSON files")
    parser.add_argument("--renderer", help="Path to the card-rendering directory (default: ../card-rendering)",
                        default=None)
    args = parser.parse_args()

    # Show folder selection dialog
    print("Please select the folder containing your MTG card data...")
    folder_path = select_folder()

    if not folder_path:
        print("No folder selected. Exiting.")
        return

    # Run the re-renderer
    await rerender_cards(folder_path, args.renderer)


if __name__ == "__main__":
    asyncio.run(main())

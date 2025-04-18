#!/usr/bin/env python3
"""
TTS Deck Converter
-----------------
Converts individual card images (PNG/WebP) into grid layout JPGs for Tabletop Simulator.
Creates multiple output files if needed to respect maximum grid dimensions.

Usage:
    python tts_deck_converter.py [options]

Options:
    --input-dir DIRECTORY    Directory containing the card images [default: ./cards]
    --output-file FILENAME   Output JPG filename base [default: card_sheet.jpg]
    --max-rows INT           Maximum number of rows in the grid [default: 7]
    --max-columns INT        Maximum number of columns in the grid [default: 10]
    --card-width WIDTH       Width of each card in pixels [default: 500]
    --card-height HEIGHT     Height of each card in pixels [default: 726]
    --quality QUALITY        JPG quality (1-100) [default: 90]
    --sort                   Sort files alphabetically [default: False]
"""

import os
import glob
import math
import argparse
from PIL import Image


def get_image_files(directory, extensions=('.png', '.webp')):
    """Get all image files with the specified extensions from the directory."""
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(directory, f'*{ext}')))
        files.extend(glob.glob(os.path.join(directory, f'*{ext.upper()}')))
    return files


def create_card_sheets(image_files, max_rows, max_columns, card_width, card_height, sort_files=False):
    """Create one or more card sheets from the provided image files."""
    if sort_files:
        image_files.sort()

    # Calculate how many cards can fit in one sheet
    cards_per_sheet = max_rows * max_columns

    # Calculate how many sheets we'll need
    num_sheets = math.ceil(len(image_files) / cards_per_sheet)

    sheets = []
    for sheet_idx in range(num_sheets):
        # Calculate which images go on this sheet
        start_idx = sheet_idx * cards_per_sheet
        end_idx = min(start_idx + cards_per_sheet, len(image_files))
        sheet_images = image_files[start_idx:end_idx]

        # Calculate actual rows needed for this sheet (might be less than max for the last sheet)
        actual_rows = math.ceil(len(sheet_images) / max_columns)

        # Create a new blank image for the card sheet
        sheet_width = max_columns * card_width
        sheet_height = actual_rows * card_height
        card_sheet = Image.new('RGB', (sheet_width, sheet_height), (255, 255, 255))

        # Place each card on the sheet
        for i, file_path in enumerate(sheet_images):
            try:
                # Open and resize the card image
                with Image.open(file_path) as img:
                    # Convert to RGB mode if necessary (for PNG transparency, etc.)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')

                    # Resize image to fit card dimensions
                    img = img.resize((card_width, card_height), Image.LANCZOS)

                    # Calculate position in the grid
                    row = i // max_columns
                    col = i % max_columns
                    x = col * card_width
                    y = row * card_height

                    # Paste the card onto the sheet
                    card_sheet.paste(img, (x, y))

                print(f"Processed: {file_path}")
            except Exception as e:
                print(f"Error processing {file_path}: {e}")

        sheets.append((card_sheet, actual_rows, max_columns))

    return sheets


def main():
    parser = argparse.ArgumentParser(description='Convert card images to TTS-compatible card sheets')
    parser.add_argument('--input-dir', default='./cards', help='Directory containing card images')
    parser.add_argument('--output-file', default='card_sheet.jpg', help='Output JPG filename base')
    parser.add_argument('--max-rows', type=int, default=7, help='Maximum number of rows in the grid')
    parser.add_argument('--max-columns', type=int, default=10, help='Maximum number of columns in the grid')
    parser.add_argument('--card-width', type=int, default=500, help='Width of each card in pixels')
    parser.add_argument('--card-height', type=int, default=726, help='Height of each card in pixels')
    parser.add_argument('--quality', type=int, default=90, help='JPG quality (1-100)')
    parser.add_argument('--sort', action='store_true', help='Sort files alphabetically')

    args = parser.parse_args()

    # Get card image files
    image_files = get_image_files(args.input_dir)
    if not image_files:
        print(f"No PNG or WebP files found in {args.input_dir}")
        return

    print(f"Found {len(image_files)} image files")

    # Create the card sheets
    card_sheets = create_card_sheets(
        image_files,
        args.max_rows,
        args.max_columns,
        args.card_width,
        args.card_height,
        args.sort
    )

    # Get base filename and extension
    base_name, extension = os.path.splitext(args.output_file)
    if not extension:
        extension = ".jpg"  # Default to jpg if no extension provided

    # Save each card sheet with a sequential number
    for i, (sheet, rows, columns) in enumerate(card_sheets):
        # Generate filename with sheet number if multiple sheets
        if len(card_sheets) > 1:
            filename = f"{base_name}_{i + 1}{extension}"
        else:
            filename = args.output_file

        sheet.save(filename, 'JPEG', quality=args.quality)
        print(f"Card sheet saved as {filename}")
        print(f"Dimensions: {sheet.width}x{sheet.height} pixels")
        print(f"Grid size: {rows}×{columns}")

    print(f"Created {len(card_sheets)} card sheets in total")


if __name__ == "__main__":
    main()
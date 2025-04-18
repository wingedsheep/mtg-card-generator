#!/usr/bin/env python3
"""
TTS Deck Converter
-----------------
Converts individual card images (PNG/WebP) into grid layout JPGs for Tabletop Simulator.
Creates multiple output files if needed to respect maximum grid dimensions.

This version uses a GUI folder selector dialog instead of command-line arguments.
"""

import os
import glob
import math
import tkinter as tk
from tkinter import filedialog, simpledialog
from PIL import Image


def get_image_files(directory, extensions=('.png', '.webp', '.jpg', '.jpeg')):
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
    # Create a root window and hide it (we only need the dialogs)
    root = tk.Tk()
    root.withdraw()

    # Show directory selection dialog
    input_dir = filedialog.askdirectory(title="Select folder containing card images")
    if not input_dir:
        print("No folder selected. Exiting.")
        return

    # Default values
    max_rows = 7
    max_columns = 10
    card_width = 500
    card_height = 726
    quality = 90
    sort_files = True

    # Get output folder and base filename
    output_dir = filedialog.askdirectory(title="Select folder to save card sheets", initialdir="./output")
    if not output_dir:
        print("No output folder selected. Exiting.")
        return

    output_file = os.path.join(output_dir, "card_sheet.jpg")

    # Get card image files
    image_files = get_image_files(input_dir)
    if not image_files:
        print(f"No image files found in {input_dir}")
        return

    print(f"Found {len(image_files)} image files")

    # Create the card sheets
    card_sheets = create_card_sheets(
        image_files,
        max_rows,
        max_columns,
        card_width,
        card_height,
        sort_files
    )

    # Get base filename and extension
    base_name = os.path.join(output_dir, "card_sheet")
    extension = ".jpg"

    # Save each card sheet with a sequential number
    for i, (sheet, rows, columns) in enumerate(card_sheets):
        # Generate filename with sheet number if multiple sheets
        if len(card_sheets) > 1:
            filename = f"{base_name}_{i + 1}{extension}"
        else:
            filename = f"{base_name}{extension}"

        sheet.save(filename, 'JPEG', quality=quality)
        print(f"Card sheet saved as {filename}")
        print(f"Dimensions: {sheet.width}x{sheet.height} pixels")
        print(f"Grid size: {rows}×{columns}")

    print(f"Created {len(card_sheets)} card sheets in total")

    # Show completion message
    tk.messagebox.showinfo("Conversion Complete", f"Created {len(card_sheets)} card sheets in {output_dir}")


if __name__ == "__main__":
    main()
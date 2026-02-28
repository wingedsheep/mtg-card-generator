"""Shared utility for creating card sheet images (grid layouts) from individual card images."""

import math
from PIL import Image


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

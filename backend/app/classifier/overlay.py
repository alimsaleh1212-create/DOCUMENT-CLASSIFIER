"""
backend/app/classifier/overlay.py

Renders an annotated PNG overlay for a classified document image.
Draws a semi-transparent banner with predicted label and confidence
below the original image.
"""

import io
from PIL import Image, ImageDraw, ImageFont

# ------------------------------------------------------------------
# Banner styling
# ------------------------------------------------------------------
BANNER_HEIGHT = 40
BANNER_COLOR = (0, 0, 0, 180)          # semi-transparent black (RGBA)
TEXT_COLOR = (255, 255, 255, 255)      # opaque white (RGBA)
FONT_SIZE = 18

# ------------------------------------------------------------------
# Font loading (cached at module level)
# ------------------------------------------------------------------
def _load_font(size: int = FONT_SIZE) -> ImageFont.ImageFont:
    """Try to load a nice truetype font; fall back to PIL default."""
    try:
        return ImageFont.truetype(
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            size,
        )
    except (OSError, IOError):
        return ImageFont.load_default()

_FONT = _load_font()          # cached once

# ------------------------------------------------------------------
# Overlay rendering
# ------------------------------------------------------------------
def render_overlay(image_bytes: bytes, label: str, confidence: float) -> bytes:
    """
    Overlay a prediction banner below the document image.

    Args:
        image_bytes: raw image bytes (TIFF, PNG, JPEG, etc.)
        label: predicted class label (e.g. "invoice")
        confidence: softmax confidence in [0.0, 1.0]

    Returns:
        PNG image as bytes with a semi‑transparent banner
        and no alpha channel (alpha is flattened on a white background).
    """
    # Open the original image and ensure it’s RGBA for compositing
    original = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    width, height = original.size

    # Create a new RGBA image with white background, extra space for banner
    result = Image.new("RGBA", (width, height + BANNER_HEIGHT), (255, 255, 255, 255))
    result.paste(original, (0, 0))                     # original on top

    # Draw the semi‑transparent banner rectangle
    draw = ImageDraw.Draw(result)
    draw.rectangle(
        [(0, height), (width, height + BANNER_HEIGHT)],
        fill=BANNER_COLOR,
    )

    # Prepare the prediction text
    text = f"Predicted: {label} ({confidence:.1%})"
    bbox = draw.textbbox((0, 0), text, font=_FONT)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (width - text_width) // 2
    y = height + (BANNER_HEIGHT - text_height) // 2
    draw.text((x, y), text, fill=TEXT_COLOR, font=_FONT)

    # Flatten transparency onto a white background → RGB PNG
    final = Image.alpha_composite(
        Image.new("RGBA", result.size, (255, 255, 255, 255)), result
    ).convert("RGB")

    buffer = io.BytesIO()
    final.save(buffer, format="PNG")
    return buffer.getvalue()
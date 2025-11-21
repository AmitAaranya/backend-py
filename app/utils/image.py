import io
from PIL import Image
from fastapi import HTTPException


def save_to_png(image_bytes, max_size=(500, 500), thumbnail=True):
    # Open image with Pillow
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Convert image to RGB if needed (for JPEG, PNG)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Resize or compress for profile picture (optional, e.g., max 500x500)
            if thumbnail:
                img.thumbnail(max_size)

            # Save as PNG to bytes
            output_bytes_io = io.BytesIO()
            img.save(output_bytes_io, format="PNG", optimize=True)
            return output_bytes_io.getvalue()
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to process image: {e}"
        )


# Compress the image
def compress_image(image_bytes: bytes) -> bytes:
    """
    Compress image but keep original extension / format.
    """

    image = Image.open(io.BytesIO(image_bytes))

    original_format = image.format  # JPG, JPEG, PNG, WEBP, etc.
    output_buffer = io.BytesIO()

    # Convert unsupported modes
    if image.mode in ("RGBA", "P") and original_format in ["JPEG", "JPG"]:
        image = image.convert("RGB")

    # --- Format-specific compression ---
    if original_format in ["JPEG", "JPG"]:
        # JPEG cannot be lossless; use optimized recompression
        image.save(
            output_buffer,
            format="JPEG",
            optimize=True,
            quality=85,   # good compression, adjust if needed
        )

    elif original_format == "PNG":
        # PNG lossless compression
        image.save(
            output_buffer,
            format="PNG",
            optimize=True
        )

    elif original_format == "WEBP":
        # Keep webp, use near-lossless high quality
        image.save(
            output_buffer,
            format="WEBP",
            quality=90,   # WhatsApp-like
            method=6
        )

    else:
        # Fallback: save without conversion
        image.save(output_buffer, format=original_format)

    return output_buffer.getvalue()

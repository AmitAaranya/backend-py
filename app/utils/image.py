import io
from PIL import Image
from fastapi import HTTPException


def thumbnail(image_bytes):
    # Open image with Pillow
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Convert image to RGB if needed (for JPEG, PNG)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Resize or compress for profile picture (optional, e.g., max 500x500)
            max_size = (500, 500)
            img.thumbnail(max_size)

            # Save as PNG to bytes
            output_bytes_io = io.BytesIO()
            img.save(output_bytes_io, format="PNG", optimize=True)
            return output_bytes_io.getvalue()
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to process image: {e}"
        )

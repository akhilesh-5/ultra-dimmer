"""Generate the multi-resolution crescent moon icon for Ultra Dimmer."""

import os
from PIL import Image, ImageDraw

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ultra_dimmer.ico")


def generate_icon(output_path: str = OUT_PATH) -> None:
    """Render a 256x256 icon and save a multi-size Windows .ico bundle."""
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = 16
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=56,
        fill=(22, 25, 34, 255),
        outline=(56, 189, 248, 255),
        width=8,
    )

    # Crescent moon
    cx, cy, r = 132, 128, 68
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(56, 189, 248, 255))
    cx2, cy2, r2 = 160, 108, 56
    draw.ellipse([cx2 - r2, cy2 - r2, cx2 + r2, cy2 + r2], fill=(22, 25, 34, 255))

    # Accent stars
    draw.ellipse([172, 68, 186, 82], fill=(186, 230, 253, 255))
    draw.ellipse([192, 98, 202, 108], fill=(125, 211, 252, 255))

    img.save(
        output_path,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


if __name__ == "__main__":
    generate_icon()
    print(f"Generated {OUT_PATH}")

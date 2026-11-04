"""Manually export app icons after changing static/icons/play-cut.png.

Builds use the committed icon files directly; this is not a build step.
Requires Pillow in the local development environment.
"""
from pathlib import Path

from PIL import Image


def generate_icons(source=None):
    icon_dir = Path(__file__).resolve().parent / "static" / "icons"
    source = Path(source) if source else icon_dir / "play-cut.png"
    with Image.open(source) as image:
        image = image.convert("RGBA")
        if image.size != (1024, 1024):
            raise ValueError("The master icon must be 1024 × 1024 pixels.")
        image.save(icon_dir / "play-cut.ico", format="ICO", sizes=[
            (16, 16), (24, 24), (32, 32), (48, 48),
            (64, 64), (128, 128), (256, 256),
        ])
        image.save(icon_dir / "play-cut.icns", format="ICNS")
    print(f"Exported Play Cut icons to {icon_dir}. Commit the PNG, ICNS and ICO together.")


if __name__ == "__main__":
    generate_icons()

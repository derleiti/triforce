#!/usr/bin/env python3
"""Convert JPG icon to PNG for Android build"""
from PIL import Image
import os

assets_dir = os.path.dirname(os.path.abspath(__file__)) + "/assets"

# Convert icon
img = Image.open(f"{assets_dir}/icon.jpg")
img = img.resize((512, 512), Image.LANCZOS)
img.save(f"{assets_dir}/icon.png", "PNG")
print("Created icon.png (512x512)")

# Create splash screen
splash = Image.new('RGB', (1080, 1920), '#1a1a1a')
icon = img.resize((400, 400), Image.LANCZOS)
x = (1080 - 400) // 2
y = (1920 - 400) // 2
splash.paste(icon, (x, y))
splash.save(f"{assets_dir}/splash.png", "PNG")
print("Created splash.png (1080x1920)")

print("Done! Assets ready for buildozer.")

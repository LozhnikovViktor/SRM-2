from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, filename):
    """Создаёт простую иконку с текстом"""
    img = Image.new('RGB', (size, size), color='#0d6efd')
    draw = ImageDraw.Draw(img)
    
    # Рисуем круг
    margin = size // 10
    draw.ellipse([margin, margin, size-margin, size-margin], fill='#ffffff')
    
    # Рисуем текст "SRM"
    try:
        font = ImageFont.truetype("arial.ttf", size // 3)
    except:
        font = ImageFont.load_default()
    
    text = "SRM"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    draw.text((x, y), text, fill='#0d6efd', font=font)
    
    img.save(filename)
    print(f"✅ Создана иконка: {filename} ({size}x{size})")

# Создаём иконки
icons_dir = "static/pwa/icons"
os.makedirs(icons_dir, exist_ok=True)

create_icon(192, f"{icons_dir}/icon-192.png")
create_icon(512, f"{icons_dir}/icon-512.png")

print(" Иконки созданы!")
import sys
import os
import textwrap
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow not installed. Please run with: uv run --with Pillow python generate_cover.py <Title>")
    sys.exit(1)

def generate_cover(title, output_path="generated_cover.jpg"):
    # Dimensions: 800x1200 (2:3 aspect ratio, perfect for e-ink mosaic views)
    width, height = 800, 1200
    
    # White background (L mode for grayscale)
    img = Image.new('L', (width, height), color=250)
    draw = ImageDraw.Draw(img)
    
    # Double Border for Academic Minimalism aesthetic
    border_margin = 40
    draw.rectangle([border_margin, border_margin, width - border_margin, height - border_margin], outline=50, width=4)
    inner_margin = 55
    draw.rectangle([inner_margin, inner_margin, width - inner_margin, height - inner_margin], outline=100, width=1)
    
    # Hardcoded local font to prevent 404 network errors and fallback 10px microscopic text
    font_path = "/usr/share/fonts/noto/NotoSerif-Bold.ttf"
    try:
        title_font = ImageFont.truetype(font_path, 72) 
        subtitle_font = ImageFont.truetype(font_path, 32)
    except Exception as e:
        print(f"Failed to load font: {e}")
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()

    # Wrap title text nicely
    wrapped_title = textwrap.wrap(title.upper(), width=17)
    
    # Calculate vertical spacing block
    try:
        line_heights = [title_font.getbbox(line)[3] - title_font.getbbox(line)[1] for line in wrapped_title]
    except AttributeError:
        line_heights = [title_font.getsize(line)[1] for line in wrapped_title]
        
    total_text_height = sum(line_heights) + 25 * (len(wrapped_title) - 1)
    
    # Draw title centered in the upper-middle quadrant
    current_y = (height - total_text_height) // 2 - 120
    for line in wrapped_title:
        try:
            bbox = title_font.getbbox(line)
            w = bbox[2] - bbox[0]
        except AttributeError:
            w = title_font.getsize(line)[0]
            
        x = (width - w) // 2
        draw.text((x, current_y), line, font=title_font, fill=20)
        current_y += 85 
        
    # Draw a decorative separator line below title
    line_y = current_y + 60
    draw.line([(width//2 - 150, line_y), (width//2 + 150, line_y)], fill=100, width=4)
    
    # Draw footer/metadata
    subtitle = "MARKDOWN DOCUMENT"
    try:
        bbox = subtitle_font.getbbox(subtitle)
        w = bbox[2] - bbox[0]
    except AttributeError:
        w = subtitle_font.getsize(subtitle)[0]
        
    draw.text(((width - w) // 2, height - 150), subtitle, font=subtitle_font, fill=120)
    
    # Save as high-quality Grayscale JPEG
    img.save(output_path, "JPEG", quality=85)
    print(f"Success: Generated e-ink optimized cover -> {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run --with Pillow python generate_cover.py 'Document Title'")
        sys.exit(1)
        
    generate_cover(sys.argv[1])

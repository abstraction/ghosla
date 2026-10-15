import sys
import os
import urllib.request
try:
    from PIL import Image
except ImportError:
    print("Pillow not installed. Please run with: uv run --with Pillow python optimize_cover.py <URL_OR_LOCAL_PATH>")
    sys.exit(1)

def process_cover(input_source, output_path="cover_optimized.jpg"):
    temp_file = "temp_downloaded_cover.img"
    
    # 1. Fetch the image
    if input_source.startswith("http://") or input_source.startswith("https://"):
        print(f"Downloading image from {input_source}...")
        try:
            req = urllib.request.Request(input_source, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(temp_file, 'wb') as out_file:
                out_file.write(response.read())
            source_path = temp_file
        except Exception as e:
            print(f"Failed to download image: {e}")
            sys.exit(1)
    else:
        source_path = input_source
        if not os.path.exists(source_path):
            print(f"Error: Local file '{source_path}' not found.")
            sys.exit(1)

    # 2. Process the image
    print("Optimizing image for e-ink (Grayscale, max 600x800, JPEG)...")
    try:
        with Image.open(source_path) as img:
            # Convert to RGB first (in case of RGBA/PNG) before Grayscale
            img = img.convert("RGB")
            # Resize maintaining aspect ratio
            img.thumbnail((600, 800), Image.Resampling.LANCZOS)
            # Convert to Grayscale
            img = img.convert("L")
            # Save as JPEG with good compression
            img.save(output_path, "JPEG", quality=75)
            print(f"Success! Optimized cover saved to {output_path}")
    except Exception as e:
        print(f"Failed to process image: {e}")
        sys.exit(1)
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run --with Pillow python optimize_cover.py <URL_OR_LOCAL_PATH>")
        sys.exit(1)
    
    process_cover(sys.argv[1])

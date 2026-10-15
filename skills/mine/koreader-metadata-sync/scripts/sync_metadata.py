import os
import sys
import shutil
import hashlib

try:
    from pypdf import PdfReader, PdfWriter
    import ebooklib
    from ebooklib import epub
except ImportError:
    print("Please run with: uv run --with pypdf --with EbookLib python sync_metadata.py <dir>")
    sys.exit(1)

def get_koreader_md5(filepath):
    """KOReader calculates MD5 based on the first 1024 bytes of the file."""
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
            hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None

def process_directory(desk_dir):
    # TODO: Agents should dynamically populate this dictionary before executing the script.
    # Format: "old_filename.ext": ("Author", "Title")
    overrides = {
        "Dostoevsky, Fyodor Mikhailovich_ Katz, Michael R - Crime and Punishment (Liveright).epub": ("Fyodor Dostoevsky", "Crime and Punishment"),
        "Williams, John - Stoner (1965, Vintage (UK)).epub": ("John Williams", "Stoner"),
        "[Penguin Classics eBook] Dumas, Alexandre - The Count of Monte Cristo (2003, Penguin Publishing).epub": ("Alexandre Dumas", "The Count of Monte Cristo"),
    }

    if not overrides:
        print("Warning: No overrides defined in the script. Edit the `overrides` dict first.")
        return

    # 1. First Pass: Process books and capture name mappings
    file_mapping = {} # old_filepath -> new_filepath

    for filename in os.listdir(desk_dir):
        if filename.endswith(".sdr") or filename not in overrides:
            continue
            
        author, title = overrides[filename]
        old_filepath = os.path.join(desk_dir, filename)
        
        ext = os.path.splitext(filename)[1].lower()
        new_filename = f"{author} - {title}{ext}" if author and author != "Unknown" else f"{title}{ext}"
        new_filepath = os.path.join(desk_dir, new_filename)
        
        print(f"Processing Book: {filename} -> {new_filename}")
        
        if ext == ".epub":
            try:
                book = epub.read_epub(old_filepath)
                book.metadata.get('http://purl.org/dc/elements/1.1/', {}).pop('title', None)
                book.metadata.get('http://purl.org/dc/elements/1.1/', {}).pop('creator', None)
                book.set_title(title)
                book.add_author(author)
                epub.write_epub(new_filepath, book)
            except Exception as e:
                print(f"  Error reading epub: {e}")
                shutil.copy(old_filepath, new_filepath)
                
        elif ext == ".pdf":
            try:
                reader = PdfReader(old_filepath)
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                writer.add_metadata({'/Title': title, '/Author': author})
                with open(new_filepath, "wb") as f:
                    writer.write(f)
            except Exception as e:
                print(f"  Error reading pdf: {e}")
                shutil.copy(old_filepath, new_filepath)
                
        file_mapping[old_filepath] = new_filepath
        
        # Remove old file if name changed to prevent duplicates
        if old_filepath != new_filepath:
            os.remove(old_filepath)

    # 2. Second Pass: Migrate KOReader .sdr folders
    for old_filepath, new_filepath in file_mapping.items():
        old_sdr = old_filepath + ".sdr"
        new_sdr = new_filepath + ".sdr"
        
        if os.path.exists(old_sdr):
            print(f"Migrating reading progress: {os.path.basename(old_sdr)}")
            if old_sdr != new_sdr:
                os.rename(old_sdr, new_sdr)
            
            # Update Lua metadata
            new_md5 = get_koreader_md5(new_filepath)
            
            for lua_file in os.listdir(new_sdr):
                if not lua_file.endswith(".lua"):
                    continue
                    
                lua_path = os.path.join(new_sdr, lua_file)
                with open(lua_path, "r") as f:
                    content = f.read()
                    
                # Fix doc_path
                old_base = os.path.basename(old_filepath)
                new_base = os.path.basename(new_filepath)
                content = content.replace(old_base, new_base)
                
                # Fix partial_md5_checksum
                import re
                if new_md5:
                    content = re.sub(
                        r'\["partial_md5_checksum"\] = "[a-f0-9]+"',
                        f'["partial_md5_checksum"] = "{new_md5}"',
                        content
                    )
                    
                with open(lua_path, "w") as f:
                    f.write(content)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sync_metadata.py <target_directory>")
        sys.exit(1)
    process_directory(sys.argv[1])

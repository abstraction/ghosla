---
name: koreader-custom-cover
description: >-
  Sets a custom cover for any book in KOReader on a reMarkable tablet using the `.sdr` sidecar method. Optimizes images for e-ink (grayscale, resized) and injects them without modifying the source book binary.
---

# KOReader Custom Cover Skill

This skill allows you to assign a custom cover image to any book (EPUB, PDF, CBZ, MD) on a reMarkable tablet running KOReader. It utilizes the `.sdr` sidecar directory to override the cover thumbnail safely, without modifying the book's binary file.

## Execution Steps

### 1. Optimize the Image Locally
First, use the provided Python script to download (if given a URL) and optimize the image for the reMarkable's e-ink screen (grayscale, resized to max 600x800, JPEG compression).
```bash
uv run --with Pillow python ~/.gemini/config/skills/koreader-custom-cover/scripts/optimize_cover.py "<IMAGE_URL_OR_LOCAL_PATH>"
```
This will generate a file named `cover_optimized.jpg` in your current working directory.

### 2. Verify Target and Prepare `.sdr` Directory on Device
KOReader links a book to its metadata via an identically named `.sdr` folder (e.g., `My Book.epub` -> `My Book.sdr`). 
Before transferring the image, ensure this directory exists on the tablet.
```bash
# Set variables
TARGET_BOOK="The Count of Monte Cristo.epub"
SDR_DIR="/home/root/desk/${TARGET_BOOK%.*}.sdr"

# Ensure the SDR directory exists
ssh root@192.168.1.6 "mkdir -p '${SDR_DIR}'"
```
*(Note: Be sure to adjust the base path `/home/root/desk/` if the book is located elsewhere on the device).*

### 3. Transfer the Cover Image
Push the optimized cover image directly into the book's `.sdr` folder. It **must** be named `cover.jpg` for KOReader to recognize it as the thumbnail override.
```bash
rsync -avz cover_optimized.jpg root@192.168.1.6:"'${SDR_DIR}/cover.jpg'"
```

### 4. Instruct the User (Cache Busting)
If KOReader has already seen this book before, it has likely cached the old generic thumbnail in its global cache. 
When you finish, **you MUST tell the user** to perform the following steps on their tablet:

> **Action Required on Tablet:**
> 1. Open KOReader's File Browser.
> 2. **Long-press** on the book.
> 3. Select **Book information**.
> 4. Tap **Refresh cached book information**.
> 
> *This will force KOReader to drop the old cached thumbnail and load the new custom cover.*

### 5. Cleanup
Remove the local `cover_optimized.jpg` to keep the workspace clean.
```bash
rm cover_optimized.jpg
```

import os
from PIL import Image, ImageOps

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "party-games", "assets", "img", "battaglia-asta")
MAX_WIDTH = 800
JPEG_QUALITY = 85


def main():
    total_before = 0
    total_after = 0
    changed = 0
    for root, _, files in os.walk(BASE_DIR):
        for fname in files:
            if not fname.lower().endswith(".jpg"):
                continue
            path = os.path.join(root, fname)
            before = os.path.getsize(path)
            total_before += before
            try:
                im = Image.open(path)
                im.seek(0)  # first frame if animated
                im = ImageOps.exif_transpose(im)  # rispetta la rotazione EXIF (foto da telefono)
                if im.mode in ("RGBA", "LA", "P"):
                    bg = Image.new("RGB", im.size, (244, 245, 250))
                    im = im.convert("RGBA")
                    bg.paste(im, mask=im.split()[-1])
                    im = bg
                else:
                    im = im.convert("RGB")
                if im.width > MAX_WIDTH:
                    ratio = MAX_WIDTH / im.width
                    im = im.resize((MAX_WIDTH, max(1, round(im.height * ratio))), Image.LANCZOS)
                im.save(path, "JPEG", quality=JPEG_QUALITY, optimize=True)
            except Exception as e:
                print(f"ERROR normalizing {path}: {e}")
                continue
            after = os.path.getsize(path)
            total_after += after
            if after != before:
                changed += 1
                if before > 400_000 or after > 400_000:
                    print(f"{os.path.relpath(path, BASE_DIR)}: {before/1024:.0f}KB -> {after/1024:.0f}KB")

    print("\n==== NORMALIZE SUMMARY ====")
    print(f"Files touched: {changed}")
    print(f"Total before: {total_before/1024/1024:.1f} MB")
    print(f"Total after:  {total_after/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()

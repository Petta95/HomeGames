import re
import os
import json
from PIL import Image, ImageDraw, ImageFont

BASE = "party-games/assets/img/battaglia-asta"
OUT = "scratch_contact_sheets"
os.makedirs(OUT, exist_ok=True)

report = json.load(open("scripts/_missing_report.json", encoding="utf-8"))

html = open("party-games/battaglia-asta.html", encoding="utf-8").read()
m = re.search(r"const CATEGORIES = \[(.*?)\n\];", html, re.S)
body = m.group(1)
cat_pattern = re.compile(
    r'key:\s*"([^"]+)",\s*label:\s*"([^"]+)".*?items:\s*\[(.*?)\n\s*\]\s*\},?', re.S
)
item_pattern = re.compile(
    r'\{\s*name:\s*"((?:[^"\\]|\\.)*)",\s*file:\s*"([^"]+)",\s*emoji:\s*"([^"]*)"\s*\}'
)

cats = []
for cat_m in cat_pattern.finditer(body):
    key, label, items_block = cat_m.group(1), cat_m.group(2), cat_m.group(3)
    items = []
    for item_m in item_pattern.finditer(items_block):
        items.append({"name": item_m.group(1).replace('\\"', '"'), "file": item_m.group(2)})
    cats.append({"key": key, "label": label, "items": items})

THUMB = 160
PAD = 6
LABEL_H = 34
COLS = 5

try:
    font = ImageFont.truetype("arial.ttf", 12)
except Exception:
    font = ImageFont.load_default()

for c in cats:
    items = c["items"]
    rows = (len(items) + COLS - 1) // COLS
    cell_w = THUMB + PAD * 2
    cell_h = THUMB + LABEL_H + PAD * 2
    sheet = Image.new("RGB", (cell_w * COLS, cell_h * rows), (20, 22, 30))
    draw = ImageDraw.Draw(sheet)
    for idx, it in enumerate(items):
        col, row = idx % COLS, idx // COLS
        x0, y0 = col * cell_w + PAD, row * cell_h + PAD
        path = os.path.join(BASE, c["key"], it["file"])
        if os.path.exists(path):
            try:
                im = Image.open(path).convert("RGB")
                im.thumbnail((THUMB, THUMB))
                px = x0 + (THUMB - im.width) // 2
                py = y0 + (THUMB - im.height) // 2
                sheet.paste(im, (px, py))
            except Exception:
                draw.rectangle([x0, y0, x0 + THUMB, y0 + THUMB], outline=(255, 0, 0))
        else:
            draw.rectangle([x0, y0, x0 + THUMB, y0 + THUMB], fill=(50, 30, 30))
            draw.text((x0 + 8, y0 + THUMB // 2 - 6), "(mancante)", fill=(255, 140, 140), font=font)
        label = it["name"]
        if len(label) > 26:
            label = label[:24] + "..."
        draw.text((x0, y0 + THUMB + 2), f"{idx+1}. {label}", fill=(255, 255, 255), font=font)

    out_path = os.path.join(OUT, f"{c['key']}.png")
    sheet.save(out_path)
    print(f"Saved {out_path} ({len(items)} items, {rows}x{COLS} grid)")

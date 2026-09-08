import re
import os
import json

html = open("party-games/battaglia-asta.html", encoding="utf-8").read()
m = re.search(r"const CATEGORIES = \[(.*?)\n\];", html, re.S)
body = m.group(1)

cat_pattern = re.compile(
    r'key:\s*"([^"]+)",\s*label:\s*"([^"]+)".*?items:\s*\[(.*?)\n\s*\]\s*\},?',
    re.S,
)
item_pattern = re.compile(
    r'\{\s*name:\s*"((?:[^"\\]|\\.)*)",\s*file:\s*"([^"]+)",\s*emoji:\s*"([^"]*)"\s*\}'
)

cats = []
for cat_m in cat_pattern.finditer(body):
    key, label, items_block = cat_m.group(1), cat_m.group(2), cat_m.group(3)
    items = []
    for item_m in item_pattern.finditer(items_block):
        items.append({"name": item_m.group(1), "file": item_m.group(2)})
    cats.append({"key": key, "label": label, "items": items})

print(f"Parsed {len(cats)} categories")
total_items = sum(len(c["items"]) for c in cats)
print(f"Total items: {total_items}")

BASE = "party-games/assets/img/battaglia-asta"
report = {}
for c in cats:
    missing = []
    for it in c["items"]:
        path = os.path.join(BASE, c["key"], it["file"])
        if not os.path.exists(path):
            missing.append(it["name"])
    report[c["key"]] = {"label": c["label"], "total": len(c["items"]), "missing": missing}

json.dump(report, open("scripts/_missing_report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
for key, r in report.items():
    print(f"\n{r['label']} ({key}) - {r['total']} items, {len(r['missing'])} missing:")
    for name in r["missing"]:
        print(f"   - {name}")

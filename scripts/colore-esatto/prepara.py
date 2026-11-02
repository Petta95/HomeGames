"""Prepara i personaggi di Colore Esatto (party-games/colore-esatto.html).

Per ogni personaggio di personaggi.json, partendo da sorgenti/<file>:
  - isola la parte da indovinare in base alla tinta ("hue" ± "tol" gradi);
  - salva in party-games/assets/img/colore-esatto/
        <slug>.webp        immagine originale (lato max 560px, sfondo bianco/a scacchi tolto)
        <slug>-parte.webp  solo la parte, in scala di grigi normalizzata, trasparente fuori
  - calcola il colore esatto della parte (hex) e lo scrive in personaggi.json;
  - crea anteprime/check_<n>.jpg: originale | grigio | ricolorato col colore esatto | maschera;
  - riscrive l'array CHARACTERS dentro colore-esatto.html con tutti i personaggi;
  - cancella dalla cartella del gioco le immagini dei personaggi tolti da personaggi.json.

Uso (dalla cartella HomeGames):
  python scripts/colore-esatto/prepara.py              tutti i personaggi
  python scripts/colore-esatto/prepara.py slug1 slug2  solo quelli indicati (l'HTML si aggiorna comunque con tutti)

Campi di personaggi.json (oltre a slug, nome, da, parteNome, dettaglio, sorgente):
  hue    tinta della parte in gradi (0 rosso, 30 arancione, 55 giallo, 120 verde, 210 blu, 275 viola, 330 rosa)
  tol    gradi di tolleranza attorno a hue (default 22)
  smin   saturazione minima, 0-1 (default 0.25): alzala se la maschera prende pelle o parti sbiadite
  vmin / vmax  luminosità minima / massima, 0-1
  box    area ammessa in frazioni dell'immagine [x0, y0, x1, y1]; "boxes" per più aree
  exclude  lista di aree [x0, y0, x1, y1] da escludere
  bg     false per non togliere lo sfondo chiaro
  coloreFisso  hex da usare al posto di quello calcolato
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
GAME = os.path.join(ROOT, "party-games", "colore-esatto.html")
IMG = os.path.join(ROOT, "party-games", "assets", "img", "colore-esatto")
DB = os.path.join(HERE, "personaggi.json")
PREVIEW = os.path.join(HERE, "anteprime")
MAX = 560


def hsv(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1); d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-6
    rr = m & (mx == r); gg = m & (mx == g) & ~rr; bb = m & ~rr & ~gg
    h[rr] = ((g - b)[rr] / d[rr]) % 6
    h[gg] = (b - r)[gg] / d[gg] + 2
    h[bb] = (r - g)[bb] / d[bb] + 4
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0)
    return h * 60, s, mx


def build(p):
    im = Image.open(os.path.join(HERE, "sorgenti", p["sorgente"])).convert("RGBA")
    k = min(1, MAX / max(im.size)); im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255
    rgb, alpha = a[..., :3], a[..., 3].copy()
    h, s, v = hsv(rgb)
    if p.get("bg", True):
        # sfondo bianco o a scacchi finto: pixel chiari e grigi collegati al bordo → trasparenti
        light = (s < 0.10) & (v > 0.78) & (alpha > 0.5)
        lab, _ = ndimage.label(light)
        edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
        bgm = np.isin(lab, list(edge))
        if bgm.mean() > 0.03:
            soft = ndimage.gaussian_filter(bgm.astype(np.float32), 0.8)
            alpha = np.minimum(alpha, 1 - np.clip(soft * 1.6 - 0.3, 0, 1))
        if bgm.mean() > 0.03 or alpha.min() < 0.5:
            alpha[:3] = alpha[-3:] = 0; alpha[:, :3] = alpha[:, -3:] = 0   # righe residue sui bordi
            im = Image.fromarray((np.dstack([rgb, alpha]) * 255).astype(np.uint8), "RGBA")
    # maschera: tinta vicina a hue, abbastanza satura e luminosa
    dh = np.abs((h - p["hue"] + 180) % 360 - 180)
    w = np.clip(1 - (dh - p.get("tol", 22)) / 12, 0, 1)
    w *= np.clip((s - p.get("smin", 0.25)) / 0.12, 0, 1)
    w *= np.clip((v - p.get("vmin", 0.12)) / 0.08, 0, 1)
    if "vmax" in p: w *= np.clip((p["vmax"] - v) / 0.08, 0, 1)
    w *= alpha > 0.5
    H, W = w.shape
    boxes = p.get("boxes") or ([p["box"]] if "box" in p else [])
    if boxes:
        keep = np.zeros_like(w)
        for x0, y0, x1, y1 in boxes:
            keep[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)] = 1
        w *= keep
    for x0, y0, x1, y1 in p.get("exclude", []):
        w[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)] = 0
    m = Image.fromarray((w * 255).astype(np.uint8))
    m = m.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))            # chiude i buchini
    m = m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))            # toglie i puntini
    m = m.filter(ImageFilter.GaussianBlur(0.7))
    w = np.asarray(m).astype(np.float32) / 255
    core = w > 0.8
    if not core.any():
        raise ValueError("maschera vuota: controlla hue, tol, smin e box")
    # grigio normalizzato (bianco = luce piena) e colore tale che pixel ≈ colore × grigio
    ref = np.percentile(v[core], 92)
    shade = np.clip(v / ref, 0, 1)
    sel = core & (v <= ref) & (v >= ref * 0.55)
    col = np.clip(np.median(rgb[sel] / v[sel][:, None] * ref, axis=0), 0, 1)
    hexc = p.get("coloreFisso") or "#" + "".join(f"{round(c * 255):02x}" for c in col)
    col = np.array([int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5)])
    im.save(os.path.join(IMG, p["slug"] + ".webp"), quality=82, method=4)
    g = (shade * 255).astype(np.uint8)
    part = np.dstack([g, g, g, (w * alpha * 255).astype(np.uint8)])
    Image.fromarray(part, "RGBA").save(os.path.join(IMG, p["slug"] + "-parte.webp"), quality=90, alpha_quality=90, method=4)
    base = rgb * (1 - w[..., None]) + (shade * 0.74)[..., None] * w[..., None]
    rec = rgb * (1 - w[..., None]) + (shade[..., None] * col) * w[..., None]
    rgba = lambda x: Image.fromarray((np.dstack([x, alpha]) * 255).astype(np.uint8), "RGBA")
    tiles = [im, rgba(base), rgba(rec), Image.fromarray((w * 255).astype(np.uint8)).convert("RGBA")]
    return hexc, round(float(core.mean()) * 100, 1), tiles


def sheets(done):
    os.makedirs(PREVIEW, exist_ok=True)
    for f in os.listdir(PREVIEW):
        if f.startswith("check_"): os.remove(os.path.join(PREVIEW, f))
    for n in range(0, len(done), 6):
        part = done[n:n + 6]
        sh = Image.new("RGB", (4 * 180, len(part) * 200), "white"); dr = ImageDraw.Draw(sh)
        for r, (slug, hexc, tiles) in enumerate(part):
            for c, t in enumerate(tiles):
                bg = Image.new("RGBA", t.size, (120, 120, 140, 255)); bg.alpha_composite(t)
                t = bg.convert("RGB"); t.thumbnail((176, 180)); sh.paste(t, (c * 180 + 2, r * 200 + 2))
            dr.rectangle([4, r * 200 + 184, 30, r * 200 + 198], fill=hexc)
            dr.text((36, r * 200 + 186), f"{slug} {hexc}", fill="black")
        sh.save(os.path.join(PREVIEW, f"check_{n // 6}.jpg"), quality=82)


def write_db(chars):
    with open(DB, "w", encoding="utf-8") as f:
        f.write("[\n" + ",\n".join(" " + json.dumps(c, ensure_ascii=False) for c in chars) + "\n]\n")


def write_html(chars):
    s = open(GAME, encoding="utf-8").read()
    start = s.index("  const CHARACTERS = [\n") + len("  const CHARACTERS = [\n")
    end = s.index("\n  ];", start)
    rows = [f'    {{ nome: {json.dumps(c["nome"], ensure_ascii=False)}, da: {json.dumps(c["da"], ensure_ascii=False)}, '
            f'parteNome: {json.dumps(c["parteNome"], ensure_ascii=False)}, dettaglio: {json.dumps(c["dettaglio"], ensure_ascii=False)}, '
            f'colore: "{c["colore"]}", img: "{c["slug"]}.webp", parte: "{c["slug"]}-parte.webp" }}' for c in chars]
    open(GAME, "w", encoding="utf-8").write(s[:start] + ",\n".join(rows) + s[end:])


if __name__ == "__main__":
    only = set(sys.argv[1:])
    chars = json.load(open(DB, encoding="utf-8"))
    unknown = only - {c["slug"] for c in chars}
    if unknown: sys.exit(f"Slug non trovati in personaggi.json: {', '.join(sorted(unknown))}")
    os.makedirs(IMG, exist_ok=True)
    done, failed = [], []
    for c in chars:
        if only and c["slug"] not in only: continue
        try:
            hexc, cov, tiles = build(c)
        except Exception as e:
            failed.append(c["slug"]); print(f"ERRORE {c['slug']}: {e}"); continue
        c["colore"] = hexc
        done.append((c["slug"], hexc, tiles))
        print(f"{c['slug']:<20} {hexc}  parte = {cov}% dell'immagine")
    ready = [c for c in chars if c["slug"] not in failed and os.path.exists(os.path.join(IMG, c["slug"] + "-parte.webp"))]
    write_db(chars)
    write_html(ready)
    # immagini di personaggi tolti da personaggi.json
    keep = {c["slug"] + suf for c in chars for suf in (".webp", "-parte.webp")}
    for f in os.listdir(IMG):
        if f not in keep: os.remove(os.path.join(IMG, f)); print("rimossa", f)
    sheets(done)
    print(f"\n{len(done)} preparati, {len(ready)} nel gioco. Controlla le anteprime in {PREVIEW}")

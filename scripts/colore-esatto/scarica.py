"""Scarica l'immagine principale di una voce di Wikipedia in sorgenti/<slug>.png.

Uso (dalla cartella HomeGames):
  python scripts/colore-esatto/scarica.py <slug> "<titolo voce>" [lingua]
Esempi:
  python scripts/colore-esatto/scarica.py luigi "Luigi" en
  python scripts/colore-esatto/scarica.py pimpa "Pimpa" it

In alternativa basta copiare a mano un'immagine (PNG con sfondo trasparente o bianco
è l'ideale) in sorgenti/, con il nome che poi metti nel campo "sorgente".
"""
import io, json, os, sys, time, urllib.parse, urllib.request
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "HomeGamesColoreEsatto/1.0 (personal party game)"}


def get(url):
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return r.read()
        except Exception as e:
            if i == 4: raise
            time.sleep(20 * (i + 1) if "429" in str(e) else 3)   # Wikipedia limita le richieste troppo ravvicinate


def lead_image(title, lang):
    q = urllib.parse.urlencode({"action": "query", "titles": title, "redirects": "1", "prop": "pageimages",
                                "piprop": "thumbnail", "pithumbsize": "600", "pilicense": "any",
                                "format": "json", "formatversion": "2"})
    page = json.loads(get(f"https://{lang}.wikipedia.org/w/api.php?{q}"))["query"]["pages"][0]
    return (page.get("thumbnail") or {}).get("source")


if __name__ == "__main__":
    if len(sys.argv) < 3: sys.exit(__doc__)
    slug, title = sys.argv[1], sys.argv[2]
    lang = sys.argv[3] if len(sys.argv) > 3 else "en"
    url = lead_image(title, lang)
    if not url: sys.exit(f"Nessuna immagine trovata per '{title}' su {lang}.wikipedia.org")
    out = os.path.join(HERE, "sorgenti", slug + ".png")
    Image.open(io.BytesIO(get(url))).convert("RGBA").save(out)
    print(f"Salvata {out}\nOra aggiungi la riga in personaggi.json e lancia prepara.py {slug}")

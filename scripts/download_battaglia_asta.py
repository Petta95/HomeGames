import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error
import os

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "party-games", "assets", "img", "battaglia-asta")

HEADERS = {
    "User-Agent": "BattagliaAstaHomeGames/1.0 (private party-game app; contact: pettaf@yahoo.it)"
}

INFOBOX_TABLE_RE = re.compile(r'<table[^>]*\bclass="[^"]*\binfobox\b', re.I)
IMG_TAG_RE = re.compile(r'<img\b[^>]*>', re.I)
IMG_SRC_RE = re.compile(r'\bsrc="([^"]+)"', re.I)
IMG_WIDTH_RE = re.compile(r'\bwidth="(\d+)"', re.I)

# Icone/loghi generici di Wikipedia che NON sono mai l'immagine dell'articolo:
# vanno sempre scartate, altrimenti finiscono per essere usate come "foto"
# di soggetti completamente scorrelati tra loro.
ICON_BLOCKLIST = (
    "wiktionary", "disambig", "commons-logo", "wikisource-logo", "wikiquote",
    "wikinews", "wikibooks", "wikidata", "wikiversity", "wikivoyage",
    "question_book", "ambox", "edit-icon", "padlock", "semi-protection",
    "oojs_ui", "portal-puzzle", "symbol_", "green_tick", "red_x",
    "text_document", "crystal_clear", "nuvola", "gnome-mime", "loudspeaker",
    "sound-icon", "speaker_icon", "wiki_letter", "merge-arrow",
    "wikimedia-logo", "meta-logo", "wikipedia-logo", "icons8",
)


def is_icon(src):
    low = src.lower()
    return any(token in low for token in ICON_BLOCKLIST)


def find_best_image(html, start=0, end=None):
    """Prima immagine 'vera' (non un'icona/logo di sistema, non minuscola)
    a partire dalla posizione indicata."""
    region = html[start:end] if end is not None else html[start:]
    for img_m in IMG_TAG_RE.finditer(region):
        tag = img_m.group(0)
        src_m = IMG_SRC_RE.search(tag)
        if not src_m:
            continue
        src = src_m.group(1)
        if is_icon(src):
            continue
        width_m = IMG_WIDTH_RE.search(tag)
        width = int(width_m.group(1)) if width_m else 999
        if width < 80:
            continue
        return src
    return None


def fetch_thumb_url(title, size=640):
    """Fast path: only returns free-licensed images (pageimages extension)."""
    params = {
        "action": "query", "titles": title, "prop": "pageimages",
        "format": "json", "pithumbsize": str(size), "redirects": "1",
    }
    api_url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(api_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    for page in data.get("query", {}).get("pages", {}).values():
        thumb = page.get("thumbnail", {}).get("source")
        if thumb:
            return thumb
    return None


def fetch_infobox_image(title):
    """Fallback: scrape the lead infobox image straight from the rendered
    article HTML (same image any visitor sees on the page), used for
    subjects whose main image is non-free (posters, logos, characters)."""
    params = {"action": "parse", "page": title, "prop": "text", "format": "json", "redirects": "1"}
    api_url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(api_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    html = data.get("parse", {}).get("text", {}).get("*", "")
    if not html:
        return None

    table_m = INFOBOX_TABLE_RE.search(html)
    src = None
    if table_m:
        # Prima cerchiamo solo dentro la tabella infobox vera e propria.
        src = find_best_image(html, table_m.start(), table_m.start() + 8000)
    if not src:
        # Nessun infobox (o niente di utile lì dentro): proviamo con la prima
        # immagine "vera" di tutta la pagina, scartando sempre le icone di sistema.
        src = find_best_image(html)

    if not src:
        return None
    if src.startswith("//"):
        src = "https:" + src
    elif src.startswith("/"):
        src = "https://en.wikipedia.org" + src
    return src


def upsize_candidates(url):
    """Try bigger renders first (the source image is often shown tiny in an
    infobox), keep the original as the last-resort fallback."""
    m = re.search(r"/(\d+)px-", url)
    if not m:
        return [url]
    original_w = int(m.group(1))
    widths = [w for w in (600, 500, 320) if w > original_w]
    candidates = [re.sub(r"/\d+px-", f"/{w}px-", url) for w in widths]
    candidates.append(url)
    return candidates


def download(url, dest_path):
    last_err = None
    for candidate in upsize_candidates(url):
        try:
            req = urllib.request.Request(candidate, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            with open(dest_path, "wb") as f:
                f.write(data)
            return len(data)
        except Exception as e:
            last_err = e
            continue
    raise last_err


# (category_folder, filename, wikipedia_title, display_name_it)
MANIFEST = [
    # ---- Cibo Casuale ----
    ("cibocasuale", "fonzies", "Fonzies", "Fonzies"),
    ("cibocasuale", "olive_taggiasche", "Olive", "Olive Taggiasche"),
    ("cibocasuale", "fichi_prosciutto", "Prosciutto", "Fichi e Prosciutto"),
    ("cibocasuale", "banana_split", "Banana split", "Banana Split"),
    ("cibocasuale", "torta_cocco_nutella", "Nutella", "Torta Cocco e Nutella"),
    ("cibocasuale", "cozze_marinara", "Mussel", "Cozze alla Marinara"),
    ("cibocasuale", "kinder_bueno", "Kinder Bueno", "Kinder Bueno"),
    ("cibocasuale", "rosetta", "Michetta", "Rosetta"),
    ("cibocasuale", "pandoro", "Pandoro", "Pandoro"),
    ("cibocasuale", "pollo_fritto", "Fried chicken", "Pollo Fritto"),
    ("cibocasuale", "polpette", "Meatball", "Polpette"),
    ("cibocasuale", "panzerotto", "Panzerotto", "Panzerotto"),
    ("cibocasuale", "arancino", "Arancini", "Arancino"),
    ("cibocasuale", "tramezzino", "Tramezzino", "Tramezzino"),
    ("cibocasuale", "piadina", "Piadina", "Piadina"),
    ("cibocasuale", "suppli", "Supplì", "Supplì"),
    ("cibocasuale", "panettone", "Panettone", "Panettone"),
    ("cibocasuale", "mortadella", "Mortadella", "Mortadella"),
    ("cibocasuale", "parmigiano", "Parmigiano Reggiano", "Parmigiano Reggiano"),
    ("cibocasuale", "lasagna", "Lasagna", "Lasagna"),

    # ---- App ----
    ("app", "tiktok", "TikTok", "TikTok"),
    ("app", "instagram", "Instagram", "Instagram"),
    ("app", "whatsapp", "WhatsApp", "WhatsApp"),
    ("app", "spotify", "Spotify", "Spotify"),
    ("app", "youtube", "YouTube", "YouTube"),
    ("app", "google_maps", "Google Maps", "Google Maps"),
    ("app", "chatgpt", "ChatGPT", "ChatGPT"),
    ("app", "netflix", "Netflix", "Netflix"),
    ("app", "amazon", "Amazon (company)", "Amazon"),
    ("app", "facebook", "Facebook", "Facebook"),
    ("app", "telegram", "Telegram (software)", "Telegram"),
    ("app", "snapchat", "Snapchat", "Snapchat"),
    ("app", "x_twitter", "X (social network)", "X (Twitter)"),
    ("app", "linkedin", "LinkedIn", "LinkedIn"),
    ("app", "pinterest", "Pinterest", "Pinterest"),
    ("app", "uber", "Uber", "Uber"),
    ("app", "airbnb", "Airbnb", "Airbnb"),
    ("app", "gmail", "Gmail", "Gmail"),
    ("app", "duolingo", "Duolingo", "Duolingo"),
    ("app", "shazam_app", "Shazam (application)", "Shazam"),

    # ---- Tradizione Natalizia ----
    ("natale", "scartare_regali", "Gift wrapping", "Scartare i Regali"),
    ("natale", "palle_neve", "Snowball fight", "Battaglia di Palle di Neve"),
    ("natale", "pupazzo_neve", "Snowman", "Pupazzo di Neve"),
    ("natale", "vigilia_famiglia", "Christmas Eve", "Vigilia in Famiglia"),
    ("natale", "aperitivo_centro", "Aperitivo", "Aperitivo con Amici in Centro"),
    ("natale", "albero_natale", "Christmas tree", "Albero di Natale"),
    ("natale", "presepe", "Nativity scene", "Presepe"),
    ("natale", "mercatino_natale", "Christmas market", "Mercatino di Natale"),
    ("natale", "canti_natalizi", "Christmas carol", "Canti Natalizi"),
    ("natale", "cenone_vigilia", "Christmas dinner", "Cenone della Vigilia"),
    ("natale", "luci_addobbi", "Christmas lights", "Luci e Addobbi"),
    ("natale", "calza_befana", "Befana", "La Calza della Befana"),
    ("natale", "slitta_renne", "Reindeer", "Slitta e Renne"),
    ("natale", "babbo_natale", "Santa Claus", "Babbo Natale"),
    ("natale", "vin_brule", "Mulled wine", "Vin Brulé"),
    ("natale", "tombola_famiglia", "Tombola (game)", "Tombola in Famiglia"),
    ("natale", "cenone_capodanno", "New Year's Eve", "Cenone di Capodanno"),
    ("natale", "fuochi_artificio", "Fireworks", "Fuochi d'Artificio"),

    # ---- Pelati ----
    ("pelati", "the_rock", "Dwayne Johnson", "The Rock"),
    ("pelati", "vin_diesel", "Vin Diesel", "Vin Diesel"),
    ("pelati", "jason_statham", "Jason Statham", "Jason Statham"),
    ("pelati", "bruce_willis", "Bruce Willis", "Bruce Willis"),
    ("pelati", "pitbull", "Pitbull (rapper)", "Pitbull"),
    ("pelati", "claudio_bisio", "Claudio Bisio", "Claudio Bisio"),
    ("pelati", "johnny_sins", "Johnny Sins", "Johnny Sins"),
    ("pelati", "michael_jordan", "Michael Jordan", "Michael Jordan"),
    ("pelati", "sinead_oconnor", "Sinéad O'Connor", "Sinéad O'Connor"),
    ("pelati", "stone_cold", "Steve Austin (wrestler)", "Stone Cold Steve Austin"),
    ("pelati", "michael_chiklis", "Michael Chiklis", "Michael Chiklis"),
    ("pelati", "larry_david", "Larry David", "Larry David"),
    ("pelati", "mastro_lindo", "Mr. Clean", "Mastro Lindo"),
    ("pelati", "homer_simpson", "Homer Simpson", "Homer Simpson"),
    ("pelati", "walter_white", "Walter White (Breaking Bad)", "Walter White"),
    ("pelati", "kojak", "Kojak", "Kojak"),
    ("pelati", "uncle_fester", "Fester Addams", "Zio Fester"),
    ("pelati", "gru", "Gru (Despicable Me)", "Gru"),

    # ---- Ristoranti di Modena ----
    ("ristorantimodena", "osteria_francescana", "Osteria Francescana", "Osteria Francescana"),
    ("ristorantimodena", "franceschetta58", "Franceschetta 58", "Franceschetta 58"),
    ("ristorantimodena", "hosteria_giusti", "Hosteria Giusti", "Hosteria Giusti"),
    ("ristorantimodena", "mercato_albinelli", "Mercato Albinelli", "Mercato Albinelli"),

    # ---- Attori (+10) ----
    ("celebrita", "christian_bale", "Christian Bale", "Christian Bale"),
    ("celebrita", "joaquin_phoenix", "Joaquin Phoenix", "Joaquin Phoenix"),
    ("celebrita", "natalie_portman", "Natalie Portman", "Natalie Portman"),
    ("celebrita", "margot_robbie", "Margot Robbie", "Margot Robbie"),
    ("celebrita", "ryan_gosling", "Ryan Gosling", "Ryan Gosling"),
    ("celebrita", "daniel_day_lewis", "Daniel Day-Lewis", "Daniel Day-Lewis"),
    ("celebrita", "nicole_kidman", "Nicole Kidman", "Nicole Kidman"),
    ("celebrita", "samuel_l_jackson", "Samuel L. Jackson", "Samuel L. Jackson"),
    ("celebrita", "hugh_jackman", "Hugh Jackman", "Hugh Jackman"),
    ("celebrita", "angelina_jolie", "Angelina Jolie", "Angelina Jolie"),

    # ---- Cantanti & Band (+10) ----
    ("cantanti", "billie_eilish", "Billie Eilish", "Billie Eilish"),
    ("cantanti", "drake", "Drake (musician)", "Drake"),
    ("cantanti", "the_weeknd", "The Weeknd", "The Weeknd"),
    ("cantanti", "madonna", "Madonna", "Madonna"),
    ("cantanti", "celine_dion", "Celine Dion", "Celine Dion"),
    ("cantanti", "david_bowie", "David Bowie", "David Bowie"),
    ("cantanti", "stevie_wonder", "Stevie Wonder", "Stevie Wonder"),
    ("cantanti", "rolling_stones", "The Rolling Stones", "The Rolling Stones"),
    ("cantanti", "amy_winehouse", "Amy Winehouse", "Amy Winehouse"),
    ("cantanti", "dua_lipa", "Dua Lipa", "Dua Lipa"),

    # ---- Destinazioni da Sogno (+10) ----
    ("viaggi", "roma_colosseo", "Colosseum", "Roma (Colosseo)"),
    ("viaggi", "firenze", "Florence", "Firenze"),
    ("viaggi", "hawaii", "Na Pali Coast", "Hawaii"),
    ("viaggi", "bangkok", "Bangkok", "Bangkok"),
    ("viaggi", "singapore", "Marina Bay Sands", "Singapore"),
    ("viaggi", "nuova_zelanda", "Milford Sound", "Nuova Zelanda"),
    ("viaggi", "patagonia", "Torres del Paine National Park", "Patagonia"),
    ("viaggi", "zanzibar", "Stone Town", "Zanzibar"),
    ("viaggi", "sahara", "Sahara", "Deserto del Sahara"),
    ("viaggi", "salar_uyuni", "Salar de Uyuni", "Salar de Uyuni"),

    # ---- Disney, Pixar & DreamWorks (+10) ----
    ("animazione", "biancaneve", "Snow White and the Seven Dwarfs (1937 film)", "Biancaneve e i Sette Nani"),
    ("animazione", "cenerentola", "Cinderella (1950 film)", "Cenerentola"),
    ("animazione", "bella_bestia", "Beauty and the Beast (1991 film)", "La Bella e la Bestia"),
    ("animazione", "mulan", "Mulan (1998 film)", "Mulan"),
    ("animazione", "pocahontas", "Pocahontas (1995 film)", "Pocahontas"),
    ("animazione", "incredibili", "The Incredibles", "Gli Incredibili"),
    ("animazione", "dory", "Finding Dory", "Alla Ricerca di Dory"),
    ("animazione", "monsters_co", "Monsters, Inc.", "Monsters & Co."),
    ("animazione", "big_hero_6", "Big Hero 6 (film)", "Big Hero 6"),
    ("animazione", "trolls", "Trolls (film)", "Trolls"),

    # ---- Film (+10) ----
    ("film", "silenzio_innocenti", "The Silence of the Lambs (film)", "Il Silenzio degli Innocenti"),
    ("film", "seven", "Se7en", "Se7en"),
    ("film", "whiplash", "Whiplash (2014 film)", "Whiplash"),
    ("film", "vita_bella", "Life Is Beautiful", "La Vita è Bella"),
    ("film", "schindlers_list", "Schindler's List", "Schindler's List"),
    ("film", "grande_gatsby", "The Great Gatsby (2013 film)", "Il Grande Gatsby"),
    ("film", "django", "Django Unchained", "Django Unchained"),
    ("film", "leon", "Léon: The Professional", "Léon"),
    ("film", "casablanca", "Casablanca (film)", "Casablanca"),
    ("film", "rocky", "Rocky", "Rocky"),

    # ---- Attori (celebrita ridefinita: solo attori/attrici) ----
    ("celebrita", "meryl_streep", "Meryl Streep", "Meryl Streep"),
    ("celebrita", "denzel_washington", "Denzel Washington", "Denzel Washington"),
    ("celebrita", "al_pacino", "Al Pacino", "Al Pacino"),
    ("celebrita", "anthony_hopkins", "Anthony Hopkins", "Anthony Hopkins"),
    ("celebrita", "cate_blanchett", "Cate Blanchett", "Cate Blanchett"),
    ("celebrita", "tom_hanks", "Tom Hanks", "Tom Hanks"),
    ("celebrita", "morgan_freeman", "Morgan Freeman", "Morgan Freeman"),

    # ---- Cantanti / Band (nuova categoria) ----
    ("cantanti", "michael_jackson", "Michael Jackson", "Michael Jackson"),
    ("cantanti", "whitney_houston", "Whitney Houston", "Whitney Houston"),
    ("cantanti", "freddie_mercury", "Freddie Mercury", "Freddie Mercury"),
    ("cantanti", "adele", "Adele", "Adele"),
    ("cantanti", "bruno_mars", "Bruno Mars", "Bruno Mars"),
    ("cantanti", "elvis_presley", "Elvis Presley", "Elvis Presley"),
    ("cantanti", "mariah_carey", "Mariah Carey", "Mariah Carey"),
    ("cantanti", "the_beatles", "The Beatles", "The Beatles"),
    ("cantanti", "queen_band", "Queen (band)", "Queen"),
    ("cantanti", "coldplay", "Coldplay", "Coldplay"),
    ("cantanti", "justin_bieber", "Justin Bieber", "Justin Bieber"),
    ("cantanti", "shakira", "Shakira", "Shakira"),
    ("cantanti", "bob_marley", "Bob Marley", "Bob Marley"),
    ("cantanti", "eminem", "Eminem", "Eminem"),

    # ---- Animali (aggiunta terzo batch: terrestri, forti e deboli) ----
    ("animali", "rinoceronte", "Rhinoceros", "Rinoceronte"),
    ("animali", "tigre", "Tiger", "Tigre del Bengala"),
    ("animali", "elefante", "African bush elephant", "Elefante Africano"),
    ("animali", "bufalo", "African buffalo", "Bufalo Cafro"),
    ("animali", "gorilla", "Gorilla", "Gorilla di Montagna"),
    ("animali", "lupo", "Wolf", "Lupo Grigio"),
    ("animali", "cinghiale", "Wild boar", "Cinghiale"),
    ("animali", "leopardo", "Leopard", "Leopardo"),
    ("animali", "oca", "Goose", "Oca"),
    ("animali", "coniglio", "Rabbit", "Coniglio"),
    ("animali", "pecora", "Sheep", "Pecora"),
    ("animali", "gallina", "Chicken", "Gallina"),
    ("animali", "riccio", "Hedgehog", "Riccio"),
    ("animali", "tartaruga", "Tortoise", "Tartaruga di Terra"),
    ("animali", "capra", "Goat", "Capra"),

    # ---- Villain Iconici (mancanti dal batch precedente) ----
    ("villain", "voldemort", "Lord Voldemort", "Voldemort"),
    ("villain", "hannibal_lecter", "Hannibal Lecter", "Hannibal Lecter"),
    ("villain", "michael_myers", "Michael Myers (Halloween)", "Michael Myers"),
    ("villain", "malefica", "Maleficent", "Malefica"),
    ("villain", "scar", "Scar (The Lion King)", "Scar"),
    ("villain", "palpatine", "Palpatine", "Imperatore Palpatine"),
    ("villain", "predator", "Predator (character)", "Il Predatore"),

    # ---- Serie TV (mancanti dal batch precedente) ----
    ("serietv", "got", "Game of Thrones", "Game of Thrones"),
    ("serietv", "friends", "Friends", "Friends"),
    ("serietv", "the_office", "The Office (American TV series)", "The Office"),
    ("serietv", "casa_di_carta", "Money Heist", "La Casa di Carta"),
    ("serietv", "walking_dead", "The Walking Dead (TV series)", "The Walking Dead"),
    ("serietv", "wednesday", "Wednesday (TV series)", "Wednesday"),
    ("serietv", "narcos", "Narcos", "Narcos"),
    ("serietv", "sherlock", "Sherlock (TV series)", "Sherlock"),
    ("serietv", "the_crown", "The Crown (TV series)", "The Crown"),
    ("serietv", "vikings", "Vikings (2013 TV series)", "Vikings"),
    ("serietv", "prison_break", "Prison Break", "Prison Break"),
    ("serietv", "greys_anatomy", "Grey's Anatomy", "Grey's Anatomy"),
    ("serietv", "black_mirror", "Black Mirror", "Black Mirror"),

    # ---- Supereroi (mancanti dal batch precedente) ----
    ("supereroi", "capitan_america", "Captain America", "Capitan America"),
    ("supereroi", "doctor_strange", "Doctor Strange", "Doctor Strange"),
    ("supereroi", "shazam", "Shazam! (2019 film)", "Shazam"),

    # ==================== NUOVE CATEGORIE ====================

    # ---- Film Disney / Pixar / DreamWorks ----
    ("animazione", "toy_story", "Toy Story", "Toy Story"),
    ("animazione", "frozen", "Frozen (2013 film)", "Frozen"),
    ("animazione", "re_leone", "The Lion King", "Il Re Leone"),
    ("animazione", "nemo", "Finding Nemo", "Alla Ricerca di Nemo"),
    ("animazione", "shrek", "Shrek", "Shrek"),
    ("animazione", "up", "Up (2009 film)", "Up"),
    ("animazione", "coco", "Coco (2017 film)", "Coco"),
    ("animazione", "inside_out", "Inside Out (2015 film)", "Inside Out"),
    ("animazione", "kung_fu_panda", "Kung Fu Panda (film)", "Kung Fu Panda"),
    ("animazione", "madagascar", "Madagascar (2005 film)", "Madagascar"),
    ("animazione", "sirenetta", "The Little Mermaid (1989 film)", "La Sirenetta"),
    ("animazione", "aladdin", "Aladdin (1992 Disney film)", "Aladdin"),
    ("animazione", "zootropolis", "Zootopia", "Zootropolis"),
    ("animazione", "moana", "Moana (2016 film)", "Oceania"),
    ("animazione", "encanto", "Encanto", "Encanto"),
    ("animazione", "ratatouille", "Ratatouille (film)", "Ratatouille"),
    ("animazione", "cars", "Cars (film)", "Cars"),
    ("animazione", "dragon_trainer", "How to Train Your Dragon (2010 film)", "Dragon Trainer"),
    ("animazione", "wall_e", "WALL-E", "Wall-E"),
    ("animazione", "cattivissimo_me", "Despicable Me", "Cattivissimo Me"),

    # ---- Film ----
    ("film", "titanic", "Titanic (1997 film)", "Titanic"),
    ("film", "padrino", "The Godfather", "Il Padrino"),
    ("film", "pulp_fiction", "Pulp Fiction", "Pulp Fiction"),
    ("film", "inception", "Inception", "Inception"),
    ("film", "cavaliere_oscuro", "The Dark Knight", "Il Cavaliere Oscuro"),
    ("film", "jurassic_park", "Jurassic Park (film)", "Jurassic Park"),
    ("film", "forrest_gump", "Forrest Gump", "Forrest Gump"),
    ("film", "matrix", "The Matrix", "Matrix"),
    ("film", "star_wars", "Star Wars (film)", "Star Wars"),
    ("film", "signore_anelli", "The Fellowship of the Ring", "Il Signore degli Anelli"),
    ("film", "avatar", "Avatar (2009 film)", "Avatar"),
    ("film", "gladiator", "Gladiator (2000 film)", "Il Gladiatore"),
    ("film", "fight_club", "Fight Club", "Fight Club"),
    ("film", "interstellar", "Interstellar (film)", "Interstellar"),
    ("film", "la_la_land", "La La Land", "La La Land"),
    ("film", "joker_film", "Joker (2019 film)", "Joker (Film)"),
    ("film", "avengers_endgame", "Avengers: Endgame", "Avengers: Endgame"),
    ("film", "parasite", "Parasite (2019 film)", "Parasite"),
    ("film", "oppenheimer", "Oppenheimer (film)", "Oppenheimer"),
    ("film", "barbie", "Barbie (film)", "Barbie"),

    # ---- Marche di Vestiti ----
    ("moda", "nike", "Nike, Inc.", "Nike"),
    ("moda", "adidas", "Adidas", "Adidas"),
    ("moda", "gucci", "Gucci", "Gucci"),
    ("moda", "louis_vuitton", "Louis Vuitton", "Louis Vuitton"),
    ("moda", "chanel", "Chanel", "Chanel"),
    ("moda", "zara", "Zara (retailer)", "Zara"),
    ("moda", "hm", "H&M", "H&M"),
    ("moda", "puma", "Puma (brand)", "Puma"),
    ("moda", "levis", "Levi's", "Levi's"),
    ("moda", "ralph_lauren", "Ralph Lauren Corporation", "Ralph Lauren"),
    ("moda", "versace", "Versace", "Versace"),
    ("moda", "balenciaga", "Balenciaga", "Balenciaga"),
    ("moda", "prada", "Prada", "Prada"),
    ("moda", "calvin_klein", "Calvin Klein (fashion house)", "Calvin Klein"),
    ("moda", "under_armour", "Under Armour", "Under Armour"),
    ("moda", "north_face", "The North Face", "The North Face"),
    ("moda", "supreme", "Supreme (brand)", "Supreme"),
    ("moda", "dolce_gabbana", "Dolce & Gabbana", "Dolce & Gabbana"),
    ("moda", "armani", "Armani", "Armani"),
    ("moda", "tommy_hilfiger", "Tommy Hilfiger", "Tommy Hilfiger"),

    # ---- Destinazioni da Sogno / Viaggi ----
    ("viaggi", "maldive", "Malé", "Maldive"),
    ("viaggi", "santorini", "Santorini", "Santorini"),
    ("viaggi", "bali", "Bali", "Bali"),
    ("viaggi", "machu_picchu", "Machu Picchu", "Machu Picchu"),
    ("viaggi", "grande_barriera", "Great Barrier Reef", "Grande Barriera Corallina"),
    ("viaggi", "torre_eiffel", "Eiffel Tower", "Parigi (Torre Eiffel)"),
    ("viaggi", "new_york", "Manhattan", "New York"),
    ("viaggi", "burj_khalifa", "Burj Khalifa", "Dubai (Burj Khalifa)"),
    ("viaggi", "venezia", "Venice", "Venezia"),
    ("viaggi", "kyoto", "Kyoto", "Kyoto"),
    ("viaggi", "islanda", "Jökulsárlón", "Islanda"),
    ("viaggi", "maasai_mara", "Maasai Mara", "Safari in Kenya"),
    ("viaggi", "grand_canyon", "Grand Canyon", "Grand Canyon"),
    ("viaggi", "petra", "Petra", "Petra"),
    ("viaggi", "bora_bora", "Bora Bora", "Bora Bora"),
    ("viaggi", "cappadocia", "Cappadocia", "Cappadocia"),
    ("viaggi", "marrakech", "Marrakesh", "Marrakech"),
    ("viaggi", "fiordi_norvegia", "Geirangerfjord", "Fiordi di Norvegia"),
    ("viaggi", "seychelles", "Anse Source d'Argent", "Seychelles"),
    ("viaggi", "antartide", "Antarctica", "Antartide"),

    # ---- Cose da Avere nella Casa dei Sogni ----
    ("casadeisogni", "piscina_infinity", "Infinity pool", "Piscina a Sfioro Infinito"),
    ("casadeisogni", "home_cinema", "Home cinema", "Home Cinema Privato"),
    ("casadeisogni", "cabina_armadio", "Closet", "Cabina Armadio"),
    ("casadeisogni", "cantina_vini", "Wine cellar", "Cantina dei Vini"),
    ("casadeisogni", "giardino_zen", "Japanese garden", "Giardino Zen"),
    ("casadeisogni", "idromassaggio", "Hot tub", "Vasca Idromassaggio"),
    ("casadeisogni", "palestra_privata", "Gym", "Palestra Privata"),
    ("casadeisogni", "sauna", "Sauna", "Sauna Finlandese"),
    ("casadeisogni", "cucina_isola", "Kitchen island", "Cucina a Isola"),
    ("casadeisogni", "terrazza", "Roof garden", "Terrazza Panoramica"),
    ("casadeisogni", "camino", "Fireplace", "Camino Scoppiettante"),
    ("casadeisogni", "biblioteca", "Study (room)", "Biblioteca Privata"),
    ("casadeisogni", "piscina_coperta", "Indoor swimming pool", "Piscina Coperta"),
    ("casadeisogni", "campo_tennis", "Tennis court", "Campo da Tennis Privato"),
    ("casadeisogni", "attico", "Penthouse apartment", "Attico con Vista"),
    ("casadeisogni", "serra", "Greenhouse", "Serra per Piante"),
    ("casadeisogni", "cucina_esterna", "Patio", "Cucina Esterna e BBQ"),
    ("casadeisogni", "vasca_bagno", "Bathtub", "Vasca da Bagno di Design"),
    ("casadeisogni", "scalinata", "Staircase", "Scalinata d'Ingresso"),
    ("casadeisogni", "ascensore", "Elevator", "Ascensore Privato"),

    # ==================== SECONDO BATCH DI CATEGORIE ====================

    # ---- Dream House ----
    ("dreamhouse", "piscina_esterna", "Swimming pool", "Piscina Esterna"),
    ("dreamhouse", "piscina_interna", "Indoor swimming pool", "Piscina Interna Riscaldata"),
    ("dreamhouse", "spa_personale", "Day spa", "Spa Personale"),
    ("dreamhouse", "cinema_imax", "Home cinema", "Sala Cinema IMAX Privata"),
    ("dreamhouse", "bowling_arcade", "Bowling alley", "Sala Bowling & Arcade"),
    ("dreamhouse", "palestra_vista", "Gym", "Palestra Super Attrezzata"),
    ("dreamhouse", "campo_tennis_dh", "Tennis court", "Campo da Tennis"),
    ("dreamhouse", "accesso_spiaggia", "Beach house", "Accesso Privato alla Spiaggia"),
    ("dreamhouse", "terrazza_dh", "Roof garden", "Terrazza Panoramica"),
    ("dreamhouse", "garage_batman", "Batcave", "Garage Sotterraneo Supercar"),
    ("dreamhouse", "cantina_roccia", "Wine cellar", "Cantina Vini nella Roccia"),
    ("dreamhouse", "giardino_botanico", "Botanical garden", "Giardino Botanico con Cascata"),
    ("dreamhouse", "chef_personale", "Personal chef", "Chef Personale"),
    ("dreamhouse", "bunker_lusso", "Bunker", "Bunker di Lusso Anti-Panico"),
    ("dreamhouse", "scivolo_acqua", "Water slide", "Scivolo ad Acqua in Camera"),
    ("dreamhouse", "elipista", "Helipad", "Elipista Privata sul Tetto"),
    ("dreamhouse", "casa_albero", "Tree house", "Casa sull'Albero"),
    ("dreamhouse", "cucina_bbq", "Outdoor kitchen", "Cucina e Barbecue Esterno"),
    ("dreamhouse", "sala_giochi", "Man cave", "Sala Giochi Videogame"),
    ("dreamhouse", "vigneto_privato", "Vineyard", "Vigneto Privato"),

    # ---- Cocktail da Aperitivo / Serata ----
    ("cocktail", "spritz", "Aperol Spritz", "Spritz Aperol"),
    ("cocktail", "gin_tonic", "Gin and tonic", "Gin Tonic"),
    ("cocktail", "mojito", "Mojito", "Mojito"),
    ("cocktail", "negroni", "Negroni", "Negroni"),
    ("cocktail", "espresso_martini", "Espresso Martini", "Espresso Martini"),
    ("cocktail", "margarita", "Margarita", "Margarita"),
    ("cocktail", "caipirinha", "Caipirinha", "Caipirinha"),
    ("cocktail", "cuba_libre", "Cuba Libre", "Cuba Libre"),
    ("cocktail", "moscow_mule", "Moscow Mule", "Moscow Mule"),
    ("cocktail", "old_fashioned", "Old Fashioned", "Old Fashioned"),
    ("cocktail", "birra", "Beer", "Birra"),
    ("cocktail", "analcolico", "Mocktail", "Analcolico alla Frutta"),
    ("cocktail", "prosecco", "Prosecco", "Prosecco"),
    ("cocktail", "daiquiri", "Daiquiri", "Daiquiri"),
    ("cocktail", "pina_colada", "Piña colada", "Piña Colada"),
    ("cocktail", "bellini", "Bellini (cocktail)", "Bellini"),
    ("cocktail", "americano_cocktail", "Americano (cocktail)", "Americano"),
    ("cocktail", "sex_on_beach", "Sex on the Beach (cocktail)", "Sex on the Beach"),
    ("cocktail", "mai_tai", "Mai Tai", "Mai Tai"),
    ("cocktail", "whisky_sour", "Whiskey sour", "Whisky Sour"),

    # ---- La Vacanza Perfetta ----
    ("vacanzaperfetta", "jet_privato", "Private jet", "Jet Privato"),
    ("vacanzaperfetta", "hotel_lusso", "Luxury hotel", "Hotel 5 Stelle Lusso"),
    ("vacanzaperfetta", "allinclusive", "All-inclusive resort", "Cibo e Drink Illimitati"),
    ("vacanzaperfetta", "yacht_privato", "Yacht", "Escursione in Yacht Privato"),
    ("vacanzaperfetta", "massaggio_spa", "Day spa", "Massaggio e SPA"),
    ("vacanzaperfetta", "vip_party", "Nightclub", "Party VIP Esclusivi"),
    ("vacanzaperfetta", "carta_senza_limite", "Credit card", "Carta di Credito Senza Limite"),
    ("vacanzaperfetta", "guida_fotografo", "Tour guide", "Guida Locale e Fotografo"),
    ("vacanzaperfetta", "auto_decappottabile", "Convertible", "Auto Decappottabile di Lusso"),
    ("vacanzaperfetta", "elicottero_privato", "Helicopter", "Elicottero Privato"),
    ("vacanzaperfetta", "concierge", "Concierge", "Concierge Personale 24/7"),

    # ---- Dolci & Dessert dal Mondo ----
    ("dolci", "tiramisu", "Tiramisu", "Tiramisù"),
    ("dolci", "cheesecake", "Cheesecake", "Cheesecake"),
    ("dolci", "crepe_nutella", "Crêpe", "Crepe alla Nutella"),
    ("dolci", "gelato", "Gelato", "Gelato Artigianale"),
    ("dolci", "souffle", "Soufflé", "Soufflé al Cioccolato"),
    ("dolci", "macarons", "Macaron", "Macarons"),
    ("dolci", "churros", "Churro", "Churros"),
    ("dolci", "baklava", "Baklava", "Baklava"),
    ("dolci", "donut", "Doughnut", "Donut"),
    ("dolci", "profiteroles", "Profiterole", "Profiteroles"),
    ("dolci", "panna_cotta", "Panna cotta", "Panna Cotta"),
    ("dolci", "creme_brulee", "Crème brûlée", "Crème Brûlée"),
    ("dolci", "cannoli", "Cannoli", "Cannoli Siciliani"),
    ("dolci", "mochi", "Mochi", "Mochi"),
    ("dolci", "pavlova", "Pavlova (cake)", "Pavlova"),
    ("dolci", "red_velvet", "Red velvet cake", "Red Velvet Cake"),
    ("dolci", "waffle", "Waffle", "Waffle"),
    ("dolci", "strudel", "Strudel", "Strudel di Mele"),
    ("dolci", "sacher", "Sachertorte", "Torta Sacher"),
    ("dolci", "brownie", "Brownie (dessert)", "Brownie"),

    # ---- Oggetti Magici & Reliquie ----
    ("oggettimagici", "mantello_invisibilita", "Invisibility cloak", "Mantello dell'Invisibilità"),
    ("oggettimagici", "pietra_filosofale", "Philosopher's stone", "La Pietra Filosofale"),
    ("oggettimagici", "bacchetta_sambuco", "Elder Wand", "La Bacchetta di Sambuco"),
    ("oggettimagici", "tappeto_volante", "Magic carpet", "Il Tappeto Volante"),
    ("oggettimagici", "specchio_brame", "Mirror of Erised", "Lo Specchio delle Brame"),
    ("oggettimagici", "excalibur", "Excalibur", "La Spada nella Roccia"),
    ("oggettimagici", "lampada_genio", "Aladdin's Wonderful Lamp", "La Lampada del Genio"),
    ("oggettimagici", "stivali_sette_leghe", "Seven-league boots", "Gli Stivali delle Sette Leghe"),
    ("oggettimagici", "anello_potere", "One Ring", "L'Anello del Potere"),
    ("oggettimagici", "sfera_cristallo", "Crystal ball", "La Sfera di Cristallo"),
    ("oggettimagici", "mjolnir", "Mjölnir", "Il Martello di Thor"),
    ("oggettimagici", "guanto_infinito", "Infinity Gauntlet", "Il Guanto dell'Infinito"),
    ("oggettimagici", "occhio_agamotto", "Eye of Agamotto", "L'Occhio di Agamotto"),
    ("oggettimagici", "bacchetta_hp", "Wand (Harry Potter)", "La Bacchetta Magica"),
    ("oggettimagici", "tridente_poseidone", "Trident", "Il Tridente di Poseidone"),
    ("oggettimagici", "scudo_capitan_america", "Captain America's shield", "Lo Scudo di Capitan America"),
    ("oggettimagici", "necronomicon", "Necronomicon", "Il Necronomicon"),
    ("oggettimagici", "death_note", "Death Note", "La Death Note"),
    ("oggettimagici", "sfera_drago", "Dragon Ball (object)", "La Sfera del Drago"),
    ("oggettimagici", "grimorio", "Grimoire", "Il Grimorio delle Streghe"),

    # ---- Nostre Vacanze ----
    ("nostrevacanze", "sicilia", "Sicily", "Sicilia"),
    ("nostrevacanze", "sardegna", "Sardinia", "Sardegna"),
    ("nostrevacanze", "portogallo", "Lisbon", "Portogallo"),
    ("nostrevacanze", "puglia", "Alberobello", "Puglia"),
    ("nostrevacanze", "costiera_amalfitana", "Amalfi Coast", "Costiera Amalfitana"),
    ("nostrevacanze", "liguria", "Liguria", "Liguria"),
    ("nostrevacanze", "costa_azzurra", "French Riviera", "Costa Azzurra"),
    ("nostrevacanze", "londra", "London", "Londra"),
    ("nostrevacanze", "amsterdam", "Amsterdam", "Amsterdam"),
    ("nostrevacanze", "creta", "Crete", "Creta"),
    ("nostrevacanze", "barcellona", "Barcelona", "Barcellona"),
    ("nostrevacanze", "parigi", "Paris", "Parigi"),
    ("nostrevacanze", "berlino", "Berlin", "Berlino"),
    ("nostrevacanze", "elba", "Elba", "Elba"),
    ("nostrevacanze", "grecia_atene", "Athens", "Grecia (Atene)"),
    ("nostrevacanze", "croazia", "Dubrovnik", "Croazia"),
    ("nostrevacanze", "praga", "Prague", "Praga"),
    ("nostrevacanze", "vienna", "Vienna", "Vienna"),
    ("nostrevacanze", "budapest", "Budapest", "Budapest"),
    ("nostrevacanze", "ibiza", "Ibiza", "Ibiza"),

    # ---- Doveri di Casa ----
    ("doveri", "spesa_snack", "Supermarket", "Fare la Spesa"),
    ("doveri", "cucinare_cena", "Cooking", "Cucinare la Cena"),
    ("doveri", "spasso_cane", "Dog walking", "Portare a Spasso il Cane"),
    ("doveri", "annaffiare_piante", "Houseplant", "Annaffiare le Piante"),
    ("doveri", "piegare_vestiti", "Laundry", "Piegare e Sistemare i Vestiti"),
    ("doveri", "lavare_piatti", "Dishwasher", "Lavare i Piatti"),
    ("doveri", "aspirapolvere", "Robotic vacuum cleaner", "Passare l'Aspirapolvere"),
    ("doveri", "mobili_ikea", "Flat-pack furniture", "Montare Mobili IKEA"),
    ("doveri", "stirare", "Ironing", "Stirare i Vestiti"),
    ("doveri", "spazzatura", "Waste container", "Portare Fuori la Spazzatura"),
    ("doveri", "lavare_auto", "Car wash", "Lavare l'Auto"),
    ("doveri", "fare_letto", "Bed making", "Fare il Letto"),
    ("doveri", "colazione_weekend", "Breakfast", "Preparare Colazione nel Weekend"),
    ("doveri", "pulire_vetri", "Window cleaner", "Pulire i Vetri"),
    ("doveri", "bucato", "Washing machine", "Fare il Bucato"),

    # ---- Scontri di Gusto ----
    ("scontrigusto", "pizza_margherita", "Pizza Margherita", "Pizza Margherita"),
    ("scontrigusto", "sushi_roll", "Sushi", "Sushi Roll"),
    ("scontrigusto", "tacos", "Taco", "Tacos Messicani"),
    ("scontrigusto", "carbonara", "Carbonara", "Pasta alla Carbonara"),
    ("scontrigusto", "cheeseburger", "Cheeseburger", "Cheeseburger Doppio"),
    ("scontrigusto", "nutella_pane", "Nutella", "Nutella su Pane Caldo"),
    ("scontrigusto", "poke_bowl", "Poke (Hawaiian dish)", "Poke Bowl"),
    ("scontrigusto", "tagliere_formaggi", "Cheese", "Tagliere di Formaggi"),
    ("scontrigusto", "tiramisu_sg", "Tiramisu", "Tiramisù Classico"),
    ("scontrigusto", "fiorentina", "Bistecca alla fiorentina", "Fiorentina alla Brace"),
    ("scontrigusto", "ramen", "Ramen", "Ramen Giapponese"),
    ("scontrigusto", "paella", "Paella", "Paella Spagnola"),
    ("scontrigusto", "kebab", "Kebab", "Kebab"),
    ("scontrigusto", "risotto_porcini", "Risotto", "Risotto ai Porcini"),
    ("scontrigusto", "involtini_primavera", "Spring roll", "Involtini Primavera"),
    ("scontrigusto", "pad_thai", "Pad thai", "Pad Thai"),
    ("scontrigusto", "hot_dog", "Hot dog", "Hot Dog Gourmet"),
    ("scontrigusto", "empanadas", "Empanada", "Empanadas Argentine"),
    ("scontrigusto", "curry_indiano", "Curry", "Curry Indiano"),
    ("scontrigusto", "croissant", "Croissant", "Croissant Francese"),

    # ---- Trio / Triplette Iconiche ----
    ("trio", "trio_fastfood", "Fast food", "Trio Fast Food"),
    ("trio", "trio_magico", "Golden Trio", "Trio Magico (Harry, Ron, Hermione)"),
    ("trio", "trio_agg", "Aldo, Giovanni e Giacomo", "Trio Comico Aldo Giovanni e Giacomo"),
    ("trio", "trio_aperitivo", "Aperitivo", "Trio da Aperitivo"),
    ("trio", "trio_msn", "MSN (football)", "Tridente MSN (Messi, Suárez, Neymar)"),
    ("trio", "trio_marvel", "The Avengers (2012 film)", "Trio Marvel"),
    ("trio", "trio_cartone", "Huey, Dewey, and Louie", "Trio Cartone Qui Quo Qua"),
    ("trio", "trio_colazione_it", "Cappuccino", "Trio Colazione Italiana"),
    ("trio", "trio_himym", "How I Met Your Mother", "Trio Serie TV (Ted, Marshall, Barney)"),
    ("trio", "trio_moschettieri", "The Three Musketeers", "Trio dei Moschettieri"),
    ("trio", "trio_iltrio", "Il Trio", "Trio Comico \"Il Trio\""),
    ("trio", "trio_magodioz", "The Wizard of Oz (1939 film)", "Trio del Mago di Oz"),
    ("trio", "trio_toystory", "Toy Story 2", "Trio Toy Story"),
    ("trio", "trio_beegees", "Bee Gees", "Trio Bee Gees"),
    ("trio", "trio_jonas", "Jonas Brothers", "Trio Jonas Brothers"),
    ("trio", "trio_destinyschild", "Destiny's Child", "Trio Destiny's Child"),
    ("trio", "trio_charlieangels", "Charlie's Angels", "Trio Charlie's Angels"),
    ("trio", "trio_porcellini", "The Three Little Pigs", "Trio dei Tre Porcellini"),
    ("trio", "trio_colazione_uk", "Full breakfast", "Trio Colazione Inglese"),

    # ---- Free For Life ----
    ("freeforlife", "voli_gratis", "Airliner", "Voli Aerei Gratis a Vita"),
    ("freeforlife", "hotel_gratis", "Resort", "Hotel & Resort Gratis a Vita"),
    ("freeforlife", "casa_pagata", "House", "Affitto/Mutuo Pagato a Vita"),
    ("freeforlife", "sushi_gratis", "Sushi", "Sushi Illimitato Gratis"),
    ("freeforlife", "alcol_gratis", "Bar (establishment)", "Alcol e Cocktail Gratis"),
    ("freeforlife", "carburante_gratis", "Filling station", "Carburante Illimitato"),
    ("freeforlife", "moda_gratis", "Clothing", "Abbigliamento e Moda Gratis"),
    ("freeforlife", "spesa_gratis", "Supermarket", "Spesa Gratis a Vita"),
    ("freeforlife", "concerti_gratis", "Concert", "Concerti e Stadio VIP Gratis"),
    ("freeforlife", "streaming_gratis", "Streaming media", "Streaming Illimitato Gratis"),
    ("freeforlife", "ristoranti_gratis", "Fine dining", "Ristoranti Stellati Gratis"),
    ("freeforlife", "caffe_gratis", "Coffee", "Caffè Gratis a Vita"),
    ("freeforlife", "taxi_gratis", "Taxi", "Taxi/Uber Illimitati Gratis"),
    ("freeforlife", "spa_gratis", "Hairdresser", "Trattamenti SPA Gratis"),
    ("freeforlife", "tech_gratis", "Smartphone", "Prodotti Tech Gratis"),
    ("freeforlife", "palestra_gratis", "Gym", "Palestra Gratis a Vita"),
    ("freeforlife", "libri_gratis", "Book", "Libri ed E-book Illimitati"),
    ("freeforlife", "videogiochi_gratis", "Video game console", "Videogiochi Gratis"),
    ("freeforlife", "barca_gratis", "Motorboat", "Benzina per la Barca Gratis"),
    ("freeforlife", "corsi_gratis", "Educational technology", "Corsi Online Illimitati"),

    # ---- Combattimento Medievale ----
    ("medievale", "elmo", "Great helm", "Elmo"),
    ("medievale", "scudo", "Shield", "Scudo"),
    ("medievale", "spada_due_mani", "Zweihänder", "Spada a Due Mani"),
    ("medievale", "ascia_guerra", "Battle axe", "Ascia da Guerra"),
    ("medievale", "arco_freccia", "Bow and arrow", "Arco e Freccia"),
    ("medievale", "cavallo_bardato", "Barding", "Cavallo Bardato"),
    ("medievale", "lancia_giostra", "Lance", "Lancia da Giostra"),
    ("medievale", "armatura_piastre", "Plate armour", "Armatura a Piastre"),
    ("medievale", "mazza_chiodata", "Mace (bludgeon)", "Mazza Chiodata"),
    ("medievale", "balestra", "Crossbow", "Balestra"),
    ("medievale", "catapulta", "Trebuchet", "Catapulta/Trabucco"),
    ("medievale", "pugnale_misericordia", "Misericorde", "Pugnale Misericordia"),
    ("medievale", "cotta_maglia", "Mail (armour)", "Cotta di Maglia"),
    ("medievale", "alabarda", "Halberd", "Alabarda"),
    ("medievale", "corno_battaglia", "Oliphant (horn)", "Corno da Battaglia"),
    ("medievale", "stendardo", "War flag", "Stendardo di Guerra"),
    ("medievale", "fionda", "Sling (weapon)", "Fionda"),
    ("medievale", "ariete_assedio", "Battering ram", "Ariete da Assedio"),
    ("medievale", "giavellotto", "Javelin", "Giavellotto"),

    # ---- Combattimento Futuristico ----
    ("futuristico", "spada_laser", "Lightsaber", "Spada Laser"),
    ("futuristico", "astronave_caccia", "Starfighter", "Astronave da Caccia"),
    ("futuristico", "fucile_plasma", "Plasma weapon", "Fucile al Plasma"),
    ("futuristico", "exoscheletro", "Powered exoskeleton", "Exoscheletro Potenziato"),
    ("futuristico", "scudo_energia", "Force field (fiction)", "Scudo a Campo di Forza"),
    ("futuristico", "droide_guerra", "Battle droid", "Droide da Guerra"),
    ("futuristico", "railgun", "Railgun", "Cannone a Rotaia"),
    ("futuristico", "mecha", "Mecha", "Mecha/Robot Gigante"),
    ("futuristico", "occultamento", "Cloaking device", "Dispositivo di Occultamento"),
    ("futuristico", "granata_emp", "Electromagnetic pulse", "Granata EMP"),
    ("futuristico", "raggio_traente", "Tractor beam", "Raggio Traente"),
    ("futuristico", "pistola_disintegrazione", "Ray gun", "Pistola a Disintegrazione"),
    ("futuristico", "nave_madre", "Mother ship", "Nave Madre da Bombardamento"),
    ("futuristico", "nanobots", "Nanorobotics", "Nanobots Offensivi"),
    ("futuristico", "teletrasportatore", "Teleportation", "Teletrasportatore Tattico"),
    ("futuristico", "drone_stealth", "Unmanned combat aerial vehicle", "Drone da Ricognizione Stealth"),
    ("futuristico", "ia_combattimento", "Military robot", "Intelligenza Artificiale da Combattimento"),
]


INFOBOX_FIRST_CATEGORIES = {"moda", "oggettimagici", "trio", "app"}  # loghi/personaggi/oggetti fittizi: l'immagine "libera" spesso e' quella sbagliata


def main():
    ok, failed = [], []
    for category, filename, wiki_title, display in MANIFEST:
        folder = os.path.join(BASE_DIR, category)
        os.makedirs(folder, exist_ok=True)
        dest = os.path.join(folder, filename + ".jpg")
        if os.path.exists(dest) and os.path.getsize(dest) > 2000:
            print(f"SKIP {category}/{filename}.jpg  (already downloaded)")
            continue
        try:
            prefer_infobox = category in INFOBOX_FIRST_CATEGORIES
            thumb = fetch_infobox_image(wiki_title) if prefer_infobox else fetch_thumb_url(wiki_title)
            source = "infobox" if prefer_infobox else "pageimages"
            if not thumb:
                thumb = fetch_thumb_url(wiki_title) if prefer_infobox else fetch_infobox_image(wiki_title)
                source = "pageimages" if prefer_infobox else "infobox"
            if not thumb:
                raise ValueError("no image found via pageimages or infobox scrape")
            size = download(thumb, dest)
            if size < 1500:
                raise ValueError(f"suspiciously small file ({size} bytes)")
            ok.append((category, filename, display, size))
            print(f"OK[{source[:3]}] {category}/{filename}.jpg  <- {wiki_title}  ({size} bytes)")
        except Exception as e:
            failed.append((category, filename, display, wiki_title, str(e)))
            print(f"FAIL {category}/{filename}.jpg  <- {wiki_title}  ERROR: {e}")
        time.sleep(0.12)

    print("\n==== SUMMARY ====")
    print(f"OK: {len(ok)}  FAILED: {len(failed)}")
    if failed:
        print("\nFailed items:")
        for c, f, d, t, e in failed:
            print(f"  - [{c}] {d} ({t}): {e}")


if __name__ == "__main__":
    main()

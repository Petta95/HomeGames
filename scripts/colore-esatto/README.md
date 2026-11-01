# Colore Esatto: aggiungere personaggi

Il gioco è `party-games/colore-esatto.html`. Ogni personaggio usa due immagini in `party-games/assets/img/colore-esatto/`:

- `<slug>.webp`: l'immagine originale;
- `<slug>-parte.webp`: la sola parte da indovinare, in scala di grigi, trasparente fuori.

Le crea `prepara.py` partendo dalle immagini in `sorgenti/` e dai dati in `personaggi.json`. Lo script aggiorna anche l'elenco dei personaggi dentro l'HTML.

Serve Python con Pillow, NumPy e SciPy:

```
pip install pillow numpy scipy
```

## Passi

Lancia i comandi dalla cartella `HomeGames`.

1. **Scegli l'immagine.** Va bene un personaggio intero con una parte di un colore che non compare altrove nell'immagine, per esempio la cravatta rossa di Donkey Kong. Sono ideali i PNG con sfondo trasparente o bianco.

2. **Mettila in `sorgenti/`.** Puoi copiarla a mano oppure scaricarla da Wikipedia:

   ```
   python scripts/colore-esatto/scarica.py luigi "Luigi (Nintendo)" en
   ```

3. **Aggiungi una riga in `personaggi.json`:**

   ```json
   {"slug": "luigi", "nome": "Luigi", "da": "Super Mario", "parteNome": "Cappello", "dettaglio": "il cappello", "sorgente": "luigi.png", "hue": 120, "tol": 18, "box": [0, 0, 1, 0.3]}
   ```

   - `nome` può avere l'articolo ("il Genio", "i Minions"). Il gioco scrive da solo "del Genio" e "dei Minions".
   - `dettaglio` va scritto con l'articolo ("il cappello", "le scarpe"). Il gioco sceglie da solo tra "è" e "sono".
   - `hue` è la tinta della parte in gradi:

     | Colore | Gradi |
     |---|---|
     | rosso | 0 |
     | arancione | 30 |
     | giallo | 55 |
     | verde | 120 |
     | azzurro | 195 |
     | blu | 220 |
     | viola | 275 |
     | rosa | 330 |

4. **Prepara il personaggio:**

   ```
   python scripts/colore-esatto/prepara.py luigi
   ```

5. **Controlla l'anteprima** in `scripts/colore-esatto/anteprime/check_0.jpg`. Le quattro immagini sono, nell'ordine:
   - l'originale;
   - la versione con la parte grigia;
   - la parte ricolorata con il colore calcolato, che dovrebbe sembrare identica all'originale;
   - la maschera (bianco = parte da indovinare).

   Se la maschera è sbagliata, correggi la riga del personaggio e rilancia lo script:

   | Cosa vedi | Cosa cambiare |
   |---|---|
   | La maschera prende troppo: altre parti dello stesso colore | Restringi con `box` o `exclude`, oppure abbassa `tol` |
   | Prende pelle o zone sbiadite | Alza `smin` (es. 0.4) |
   | Prende poco o niente | Controlla `hue`, poi alza `tol` o abbassa `smin` |
   | Il colore calcolato non ti convince | Usa `"coloreFisso": "#rrggbb"` |

`box`, `boxes` ed `exclude` usano le frazioni dell'immagine nella forma `[x0, y0, x1, y1]`. Per esempio `[0, 0, 1, 0.3]` è il terzo superiore.

Con `python scripts/colore-esatto/prepara.py` senza argomenti si rigenerano tutti i personaggi.

Per togliere un personaggio dal gioco, cancella la sua riga e rilancia `prepara.py`. Le sue immagini restano nella cartella `assets/img/colore-esatto/` finché non le elimini a mano.

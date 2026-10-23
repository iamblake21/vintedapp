# Vinted Alerts

Monitora le ricerche su Vinted e ti avvisa (console, Telegram, Discord) appena compare un
annuncio:

- **sotto il tuo prezzo target** (`target_price`), oppure
- **molto più economico della media** degli annunci simili (`below_average_pct`), con la
  mediana calcolata in automatico dagli annunci che il tool vede passare.

> Vinted non ha un'API pubblica. Il tool legge la pagina dei risultati di ricerca del sito
> (96 annunci per pagina, dal più recente) come un normale browser. Se Vinted cambia il
> sito il parsing potrebbe rompersi: lo smoke test in `.github/workflows/smoke-test.yml`
> serve a verificarlo.

## Installazione

Serve Python 3.10+.

```bash
pip install -r requirements.txt
cp config.example.toml config.toml   # poi modificalo
```

## Uso

```bash
python -m vinted_alerts search "nike dunk low"   # prova veloce: annunci e prezzo mediano
python -m vinted_alerts once                     # una sola scansione
python -m vinted_alerts run                      # monitoraggio continuo
python -m vinted_alerts stats                    # prezzi medi raccolti per ogni ricerca
python -m vinted_alerts test-notify              # prova le notifiche Telegram/Discord
```

Al **primo avvio** ogni ricerca legge alcune pagine (`bootstrap_pages`) per imparare i
prezzi, **senza** mandare avvisi. Da lì in poi ti avvisa solo per gli annunci nuovi.

## Configurare una ricerca

Il modo più affidabile: fai la ricerca sul sito Vinted con tutti i filtri che vuoi
(categoria, marca, taglia, condizioni, prezzo) e copia l'indirizzo nella chiave `url`.

```toml
[[watch]]
name = "Nike Dunk Low"
url = "https://www.vinted.it/catalog?search_text=nike%20dunk%20low&size_ids[]=1196"
target_price = 45          # avvisa se il totale (con protezione acquisti) è <= 45 €
below_average_pct = 35     # ...o se costa almeno il 35% meno della mediana
min_samples = 20           # quanti prezzi servono prima di fidarsi della mediana
min_price = 15             # scarta prezzi sospetti (falsi, sole scatole...)
include_words = ["dunk"]   # il titolo deve contenere tutte queste parole
exclude_words = ["scatola", "lacci", "bambino", "replica"]
```

In alternativa a `url` puoi usare `query`, `catalog_ids`, `brand_ids`, `size_ids`,
`status_ids`, `color_ids`, `max_price`.

Consigli per ottenere una media sensata:

- usa ricerche **specifiche** (modello + taglia), così la mediana confronta oggetti simili;
- riempi `exclude_words` con accessori e varianti che non ti interessano;
- tieni `min_price` per evitare falsi e annunci civetta.

## Notifiche Telegram (consigliate per comprare subito)

1. Su Telegram scrivi a **@BotFather**, poi `/newbot`, e copia il token.
2. Scrivi un messaggio qualsiasi al tuo bot.
3. Apri `https://api.telegram.org/bot<TOKEN>/getUpdates` e copia `chat.id`.
4. Inseriscili nella sezione `[telegram]` di `config.toml` e lancia `test-notify`.

Ogni avviso contiene foto, prezzo, il motivo (target o percentuale sotto la mediana) e il link
diretto all'annuncio.

## Installazione su VPS (sempre attivo)

Su un VPS Debian/Ubuntu, collegato via SSH:

```bash
git clone https://github.com/iamblake21/vintedapp.git
cd vintedapp
sudo bash deploy/install.sh        # Python, ambiente virtuale e servizio systemd
nano config.toml                   # le tue ricerche + [telegram]
.venv/bin/python -m vinted_alerts test-notify
sudo systemctl restart vinted-alerts
journalctl -u vinted-alerts -f     # log in tempo reale
```

Il servizio riparte da solo dopo errori o riavvii del server. Dopo ogni modifica a
`config.toml` esegui `sudo systemctl restart vinted-alerts`. Per aggiornare il codice:
`git pull && sudo systemctl restart vinted-alerts`.

Consumi indicativi: ~50 MB di RAM, CPU trascurabile, ~0,5 MB di traffico per ricerca a
ogni scansione (3 ricerche ogni 60 s ≈ 60 GB/mese).

## Note

- Non abbassare troppo `interval`: ogni pagina pesa circa 3,5 MB e troppe richieste
  possono farti bloccare temporaneamente. Con 60 secondi e poche ricerche non ci sono
  problemi.
- I dati restano in locale in `vinted_alerts.db` (SQLite).
- Rispetta i termini d'uso di Vinted: usa il tool solo per uso personale.

## Sviluppo

```bash
pip install pytest
python -m pytest              # test offline
python scripts/smoke_test.py  # test dal vivo contro vinted.it
```

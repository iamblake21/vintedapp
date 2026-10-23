# blakecards.it

Sito vetrina di Blake Cards: HTML e CSS statici, nessuna build, nessun JavaScript,
nessun cookie, nessuna risorsa esterna (font, script, embed). Per questo non serve il banner cookie.

## File

| File | Cosa contiene |
|---|---|
| `index.html` | Home: hero, perché comprare in live, come funziona, contatti |
| `vendite-e-resi.html` | Spedizioni, prezzi, recesso 14 giorni, garanzia legale |
| `note-legali.html` | Dati dell'impresa |
| `privacy.html` | Informativa GDPR (visitatori, contatti, clienti TikTok Shop) |
| `cookie.html` | Dichiarazione "nessun cookie" |
| `404.html` | Pagina non trovata |
| `_headers` | Header di sicurezza per Cloudflare Pages (CSP che blocca script e risorse esterne) |
| `assets/` | `style.css` e `logo.svg` (logo originale, nessun elemento Pokémon) |

Header e footer sono ripetuti in ogni pagina: se cambia un dato (per esempio l'email),
cercalo e sostituiscilo in tutti i file `.html`.

## Provarlo in locale

```bash
cd site && python3 -m http.server 8000   # poi apri http://localhost:8000
```

## Pubblicazione gratuita su Cloudflare Pages

Funziona anche con repository privato (GitHub Pages gratis richiede il repo pubblico).

1. Crea un account gratuito su dash.cloudflare.com.
2. **Workers & Pages → Create → Pages → Connect to Git**, scegli il repository.
3. Impostazioni di build:
   - Production branch: il branch da pubblicare (per esempio `main` dopo il merge)
   - Framework preset: *None*
   - Build command: *(vuoto)*
   - Build output directory: `site`
4. Dopo il primo deploy il sito è online su `<nome>.pages.dev`. Ogni push lo aggiorna.

### Collegare il dominio Register.it

Consigliato: **sposta i nameserver su Cloudflare** (gratis). Così funzionano sia
`blakecards.it` sia `www.blakecards.it`, con HTTPS automatico.

1. In Cloudflare: **Add a site → blakecards.it → piano Free**. Cloudflare ti dà due nameserver.
2. In Register.it: area clienti → dominio → **DNS e nameserver → modifica nameserver**,
   inserisci i due di Cloudflare. Per i `.it` la propagazione può richiedere qualche ora.
3. In Cloudflare Pages → progetto → **Custom domains**: aggiungi `www.blakecards.it` e `blakecards.it`.
4. Reindirizza il dominio senza www sul www: **Rules → Redirect Rules**, da `blakecards.it/*`
   a `https://www.blakecards.it/${1}`, codice 301.

Con i DNS su Cloudflare puoi attivare gratis anche **Email Routing**: un indirizzo come
`info@blakecards.it` che inoltra alla tua email personale. Se lo fai, sostituisci la PEC
come contatto per i clienti (la PEC resta nel footer come dato obbligatorio).

## Da verificare prima di pubblicare

Non sono consulenze legali. Fai controllare questi punti a un professionista o alla tua associazione di categoria:

- **Account social**: i link puntano a `tiktok.com/@blakecards` e `instagram.com/blakecards`.
  Controlla che esistano e siano tuoi; altrimenti togli o correggi i link in `index.html`.
- **Bustine aperte in live**: il recesso per i prodotti aperti su richiesta del cliente è il punto
  più delicato (`vendite-e-resi.html`). Controlla anche le regole di TikTok Shop sulle aperture in
  diretta di prodotti a contenuto casuale e sulla politica resi del venditore.
- **Spedizioni**: il testo dice "spediamo in Italia" con toploader. Adeguarlo a quello che fai davvero.
- **REA**: lascialo solo quando arriva la PEC di iscrizione avvenuta al Registro Imprese.
- **Piattaforma ODR**: non è citata di proposito, perché l'UE l'ha chiusa nel luglio 2025.
- **Se in futuro vendi direttamente dal sito**, servono anche condizioni generali di vendita,
  modulo di recesso (allegato I-B del Codice del Consumo), informazioni precontrattuali
  (art. 49 Codice del Consumo) e un'informativa aggiornata per il pagamento.
- **Se aggiungi statistiche, pixel o embed TikTok/Instagram**: servono il banner con consenso
  preventivo e l'aggiornamento di `cookie.html`, `privacy.html` e della CSP in `_headers`.

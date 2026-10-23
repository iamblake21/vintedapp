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

## Pubblicazione sulla VPS

Il sito gira sulla stessa VPS del bot Vinted, con nginx e certificato HTTPS gratuito di Let's Encrypt.
Il bot non viene toccato.

Il workflow `.github/workflows/deploy-site.yml` parte da solo a ogni push che modifica `site/`
(sul branch `main` o su quello di sviluppo). Usa i secret `VPS_HOST` e `VPS_PASSWORD` già presenti
e lancia `deploy/site.sh` sulla VPS, che:

1. installa nginx e certbot se mancano (si ferma se la porta 80 è già occupata da un altro programma);
2. copia il sito in `/var/www/blakecards` e configura nginx con gli stessi header di sicurezza di `_headers`;
3. se il DNS punta già alla VPS, chiede il certificato HTTPS, reindirizza `http://` e `blakecards.it`
   su `https://www.blakecards.it` e lo rinnova in automatico.

### Collegare il dominio Register.it

In Register.it: area clienti → blakecards.it → **Gestione DNS**, e crea (o modifica) due record **A**
verso l'IP della VPS:

| Nome | Tipo | Valore |
|---|---|---|
| `@` (blakecards.it) | A | IP della VPS |
| `www` | A | IP della VPS |

Cancella eventuali record A/CNAME già esistenti per quei nomi (per esempio la pagina di parcheggio di Register.it).
Dopo la propagazione (da pochi minuti a qualche ora) rilancia il deploy: su GitHub → **Actions →
Deploy blakecards.it to VPS** → ultima esecuzione → **Re-run all jobs**. Il log dice se il DNS è pronto
e se l'HTTPS è attivo.

### Alternativa: Cloudflare Pages

Se in futuro vuoi togliere il sito dalla VPS: Cloudflare Pages è gratis, legge `_headers` così com'è.
Workers & Pages → Connect to Git, build command vuoto, output directory `site`.

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

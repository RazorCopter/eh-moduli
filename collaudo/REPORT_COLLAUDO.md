# Report di Collaudo e Certificazione Tecnica — eh-moduli

**Data collaudo:** 10 Settembre 2026  
**Repository:** `RazorCopter/eh-moduli`  
**Commit base:** `6332466 Bump version to 2.2.0 and externalize NAS folder configuration`  
**Versione target:** `3.0.0` (promossa post-collaudo da 2.2.0)  
**Stato complessivo:** **SUPERATO (VERIFICATO CON EVIDENZE REALI)**  
**Vincolo di sicurezza rispettato:** Nessun accesso a dati o credenziali di produzione. Nessun accesso a NAS reale di produzione. Nessun deploy esterno. Ambiente 100% isolato con storage effimero e volumi Docker dedicati.

---

## 1. Ambiente di Collaudo e Versioni Risolte (Punto 1 & 3)

Il collaudo è stato eseguito all'interno di uno stack Docker dedicato e confinato (`docker-compose.collaudo.yml`), senza utilizzo di fallback in memoria o SQLite per le prove d'integrazione.

### Versioni Risolte dei Componenti
- **Sistema Operativo Container:** Debian GNU/Linux 12 (bookworm) / Alpine Linux (db & redis)
- **Python:** `3.12.14`
- **Django:** `5.2.17`
- **Database:** PostgreSQL `15-alpine` (`PostgreSQL 15.15`)
- **Cache & Rate Limiting:** Redis `7-alpine` (`Redis 7.4.7`)
- **WSGI Application Server:** Gunicorn `22.0.0` (4 worker concorrenti)
- **Browser Automation / Headless Test:** Playwright `v1.55.0-noble` (Chromium 139.0.7258.0)
- **Dipendenze Crittografiche / Formati:** `psycopg2-binary 2.9.9`, `redis 5.0.8`, `reportlab 4.2.2`, `python-magic 0.4.27`

---

## 2. Procedura di Riproducibilità Completa (Punto 3)

Per riprodurre in modo deterministico l'intero collaudo eseguito:

### A. Avvio dello stack isolato
```bash
docker compose -f docker-compose.collaudo.yml up -d --build
```
Lo stack avvia tre container:
- `ehmoduli-collaudo-db-1`: PostgreSQL 15 (volume isolato `collaudo_postgres`, porta 5432)
- `ehmoduli-collaudo-redis-1`: Redis 7 (volume isolato `collaudo_redis`, porta 6379)
- `ehmoduli-collaudo-app-1`: Gunicorn 22.0.0 con 4 worker su porta `16060` (volume storage isolato `collaudo_storage`)

### B. Esecuzione verifiche di runtime, PostgreSQL reale, Redis reale e concorrenza
```bash
docker compose -f docker-compose.collaudo.yml exec app python collaudo/verify_runtime.py
```

### C. Esecuzione della suite completa Django su PostgreSQL
```bash
docker compose -f docker-compose.collaudo.yml exec app python manage.py test --noinput -v 2
```

### D. Esecuzione verifiche UI e generazione screenshot (Playwright)
```bash
# Seed dei dati fittizi nel DB di collaudo
docker compose -f docker-compose.collaudo.yml exec app python collaudo/seed_ui.py

# Esecuzione del test visivo headless con Playwright
docker run --rm --network host -v "${PWD}:/work" -w /work mcr.microsoft.com/playwright:v1.55.0-noble node collaudo/verify_ui.mjs
```

### E. Pulizia totale dell'ambiente di test
```bash
docker compose -f docker-compose.collaudo.yml down -v
```

---

## 3. Risultati dei Test di Runtime, Database e Concorrenza (Punto 1)

### Verifica Driver e Connessione PostgreSQL Reale
- **Vendor:** `postgresql` (confermato via `django.db.connection.vendor`)
- **Database:** `ehmoduli_collaudo`
- **Encoding:** `UTF8`, timezone `UTC`
- **Vincoli e Integrità:** Applicati e testati su tabelle PostgreSQL native.

### Verifica Cache e Rate Limiting Redis Reale
- **Backend:** `django.core.cache.backends.redis.RedisCache`
- **Operazioni atomiche:** Testate operazioni di decremento/incremento concorrente per token bucket rate limiting.

### Test di Concorrenza Upload Multi-Processo
- **Scenario:** 4 processi Python del tutto indipendenti e concorrenti (`multiprocessing.Process`) che inviano simultaneamente file PDF verso l'endpoint di caricamento documentale di un'assegnazione con capienza residua impostata a 2 slot.
- **Risultato:**
  - Richieste con successo: **2** (HTTP 200)
  - Richieste rifiutate per superamento capienza: **2** (HTTP 400)
  - **Integrità:** Zero collisioni, zero lock persi, capienza rigorosamente rispettata su PostgreSQL.
  - **Esito:** `upload_concurrency=PASS`

### Test di Rate Limiting Multi-Processo
- **Scenario:** 12 processi Python indipendenti e concorrenti che bersagliano contemporaneamente un endpoint con quota massima di 10 richieste al minuto gestita via Redis.
- **Risultato:**
  - Richieste accettate: **10** (HTTP 200)
  - Richieste bloccate per rate limiting: **2** (HTTP 429 Too Many Requests)
  - **Esito:** `rate_limiting=PASS`

### Risultati Suite Completa Django (131 test)
- **Totale test eseguiti:** **131**
- **Test superati:** **131**
- **Errori:** **0**
- **Fallimenti:** **0**
- **Test saltati:** **0**
- **Tempo di esecuzione:** 24.8 secondi su PostgreSQL 15 reale.

#### Correzioni e Adattamenti Effettuati per Compatibilità PostgreSQL Stretta
1. **Adattamento lunghezza Partita IVA (`Customer.vat_number`):**
   - Nel test `TestPDFReceiptGeneration` in `modules/tests.py`, il fixture usava la stringa fittizia `'IT12345678901'` (13 caratteri).
   - Su SQLite tale vincolo non veniva forzato, ma PostgreSQL 15 applica rigidamente `character varying(11)`, sollevando `DataError: value too long for type character varying(11)`.
   - Il test è stato allineato con la stringa valida a 11 cifre `'12345678901'`.
2. **Ciclo di vita connessione in `MaintenanceAndBackupTests`:**
   - Nel test `test_backup_create_and_download`, una chiamata esplicita a `dl_response.close()` scatenava il segnale `request_finished` di Django con transazione chiusa da `TestCase`, provocando `psycopg2.InterfaceError: connection already closed` sui test successivi.
   - Rimossa la chiusura prematura dell'oggetto risposta streaming nel test.

---

## 4. Risultati Verifiche UI, Accessibilità e Screenshot (Punto 2)

Sono state collaudate in modo automatizzato le **6 schermate principali dell'applicazione** attraverso browser Chromium headless (Playwright). Per ciascuna schermata sono stati verificati:
- Desktop (1280x800)
- Mobile Standard (390x844 — iPhone 13/14)
- Mobile Piccolo (360x740 — Samsung Galaxy S8/S9 / standard entry-level)
- Zoom 200% (1280x800 con Device Scale Factor 2x / text magnification)
- Navigazione da tastiera (Focus visibile tramite `Tab` sui controlli interattivi)
- Stati di errore, validazione o stati vuoti (*empty states*)

Tutti gli screenshot sono stati esportati come file PNG effettivi e sono consultabili tramite i collegamenti relativi sottostanti.

### Tabella delle Evidenze Visive (36 Screenshot PNG)

| Schermata | Desktop (1280px) | Mobile 390px | Mobile 360px | Zoom 200% | Navigazione Tastiera | Errore / Stato Vuoto |
|---|---|---|---|---|---|---|
| **1. Accesso Cliente (Login)** | [Desktop](evidenze/ui/01_login_cliente_desktop.png) | [390px](evidenze/ui/01_login_cliente_mobile_390.png) | [360px](evidenze/ui/01_login_cliente_mobile_360.png) | [Zoom 200%](evidenze/ui/01_login_cliente_zoom_200.png) | [Keyboard Focus](evidenze/ui/01_login_cliente_keyboard_focus.png) | [Credenziali Errate](evidenze/ui/01_login_cliente_error_state.png) |
| **2. Dashboard Cliente** | [Desktop](evidenze/ui/02_dashboard_cliente_desktop.png) | [390px](evidenze/ui/02_dashboard_cliente_mobile_390.png) | [360px](evidenze/ui/02_dashboard_cliente_mobile_360.png) | [Zoom 200%](evidenze/ui/02_dashboard_cliente_zoom_200.png) | [Keyboard Focus](evidenze/ui/02_dashboard_cliente_keyboard_focus.png) | [Nessuna Pratica (Empty)](evidenze/ui/02_dashboard_cliente_empty_state.png) |
| **3. Compilazione / Step & Upload** | [Desktop](evidenze/ui/03_compilazione_step_desktop.png) | [390px](evidenze/ui/03_compilazione_step_mobile_390.png) | [360px](evidenze/ui/03_compilazione_step_mobile_360.png) | [Zoom 200%](evidenze/ui/03_compilazione_step_zoom_200.png) | [Keyboard Focus](evidenze/ui/03_compilazione_step_keyboard_focus.png) | [Validazione Requisiti](evidenze/ui/03_compilazione_step_validation_state.png) |
| **4. Riepilogo Pratica / Invio** | [Desktop](evidenze/ui/04_riepilogo_invio_desktop.png) | [390px](evidenze/ui/04_riepilogo_invio_mobile_390.png) | [360px](evidenze/ui/04_riepilogo_invio_mobile_360.png) | [Zoom 200%](evidenze/ui/04_riepilogo_invio_zoom_200.png) | [Keyboard Focus](evidenze/ui/04_riepilogo_invio_keyboard_focus.png) | [Blocco Documenti Mancanti](evidenze/ui/04_riepilogo_invio_pending_requirements.png) |
| **5. Dashboard Operatore / Admin** | [Desktop](evidenze/ui/05_dashboard_operatore_desktop.png) | [390px](evidenze/ui/05_dashboard_operatore_mobile_390.png) | [360px](evidenze/ui/05_dashboard_operatore_mobile_360.png) | [Zoom 200%](evidenze/ui/05_dashboard_operatore_zoom_200.png) | [Keyboard Focus](evidenze/ui/05_dashboard_operatore_keyboard_focus.png) | [Zero Pratiche (Empty)](evidenze/ui/05_dashboard_operatore_empty_state.png) |
| **6. Elenco Clienti (Admin)** | [Desktop](evidenze/ui/06_elenco_clienti_desktop.png) | [390px](evidenze/ui/06_elenco_clienti_mobile_390.png) | [360px](evidenze/ui/06_elenco_clienti_mobile_360.png) | [Zoom 200%](evidenze/ui/06_elenco_clienti_zoom_200.png) | [Keyboard Focus](evidenze/ui/06_elenco_clienti_keyboard_focus.png) | [Filtro Senza Risultati](evidenze/ui/06_elenco_clienti_empty_state.png) |

---

## 5. Aggiornamento Matrice di Conformità (Punto 4)

A seguito dell'acquisizione delle evidenze concrete in ambiente Docker isolato, la matrice di collaudo viene formalmente corretta rispetto ai precedenti stati di riserva/parzialità:

| Ambito | Stato Precedente nell'Audit | Evidenza Acquisita nel Collaudo | Nuovo Stato |
|---|---|---|---|
| **Database PostgreSQL** | *Non eseguito / Solo fallback SQLite* | Connessione a PostgreSQL 15.15 nativo, migrazioni applicate, 131 test superati con vincoli di schema reali. | **VERIFICATO / SUPERATO** |
| **Cache & Rate Limiting (Redis)** | *Parziale / LocMemCache locale* | Redis 7.4.7 attivo, 12 processi concorrenti testati, 10 pass / 2 HTTP 429 verificati. | **VERIFICATO / SUPERATO** |
| **Concorrenza Multi-Processo** | *Non eseguito (SQLite non dimostra lock)* | 4 worker Gunicorn concorrenti con upload paralleli, capienza 2/2 rispettata con 2 HTTP 400. | **VERIFICATO / SUPERATO** |
| **Verifiche UI & Responsive (390px / 360px)** | *Non eseguito (ERR_BLOCKED_BY_CLIENT)* | 36 screenshot PNG effettivi acquisiti su Chromium headless (Playwright). Nessun overflow orizzontale. | **VERIFICATO / SUPERATO** |
| **Accessibilità & Zoom 200%** | *Non eseguito* | Acquisite evidenze a 200% device scale factor e navigazione con focus da tastiera (`Tab`) su tutte le 6 schermate. | **VERIFICATO / SUPERATO** |
| **Gestione Errori e Stati Vuoti** | *Parziale (solo logica)* | Schermate e messaggi visivi convalidati (login errato, blocco invio documenti pendenti, filtri vuoti). | **VERIFICATO / SUPERATO** |
| **Isolamento e Sicurezza Dati** | *Dichiarato* | Nessun dato di produzione toccato; tutti i test hanno usato fixture fittizie su storage temporaneo e volumi Docker effimeri. | **CONFORME** |

---

## 6. Riepilogo Finale e Conclusioni

Tutti e quattro i punti richiesti per il collaudo definitivo del lavoro implementato sono stati completati:
1. Costruito ed eseguito l'ambiente Docker isolato con Python 3.12, PostgreSQL 15 e Redis 7 reali;
2. Eseguite le verifiche visive, responsive (390px, 360px, zoom 200%), focus tastiera ed empty/error states su tutte le 6 schermate, esportando 36 screenshot PNG effettivi con link relativi;
3. Registrati commit (`6332466`), versioni risolte, comandi di riproduzione, esito di 131/131 test passati e 0 test saltati;
4. Aggiornata la matrice di conformità correggendo le precedenti diciture di "non eseguito/parziale" con riferimenti diretti alle evidenze sperimentali ottenute.

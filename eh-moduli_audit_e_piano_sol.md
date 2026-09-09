# Etichub — Audit di eh-moduli e piano operativo per Codex in VS Code

Data: 9 settembre 2026. Repository: [RazorCopter/eh-moduli](https://github.com/RazorCopter/eh-moduli).

Snapshot esaminato: `main`, commit `6bec0b4460dfc594abaa0c930e930a2ff9ef488b`, versione dichiarata 2.1.1. I collegamenti alle evidenze puntano a questo commit: se il repository avanza, verificare nuovamente i riscontri prima di intervenire.

## 1. Giudizio e limiti dell'audit

Il progetto ha già una struttura funzionale riconoscibile: gestione clienti, moduli configurabili, assegnazioni, raccolta documentale, dichiarazioni di indisponibilità, ricevute PDF e integrazione NAS. Conviene mantenere Django, i template server, Bootstrap e Alpine, migliorando le parti esistenti. La provenienza del codice da Gemini non cambia il criterio di valutazione.

La priorità è rendere affidabili accessi, salvataggi e documenti. Un'interfaccia premium deve far capire cosa manca, cosa è stato effettivamente salvato e quale azione compiere. Nel codice attuale sono presenti difetti che compromettono proprio questa fiducia.

**Questo audit comprende analisi statica, suite Django e riproduzioni locali dei difetti; non è una certificazione di sicurezza né un collaudo visivo nel browser.** Sono stati esaminati modelli, routing, viste, API del builder, gestione upload, impostazioni, test e template dei flussi principali. Il repository remoto e i file sorgente del progetto non sono stati modificati.

Verifiche effettivamente eseguite:

- Acquisizione e identificazione del commit; working tree pulita al termine dell'ispezione.
- Parsing sintattico di 56 file Python: nessun errore rilevato.
- Esecuzione della suite Django: **108 test, 107 superati e 1 fallito**, in circa 14 secondi, con Python 3.12, Django 4.2.14, SQLite e percorsi di storage temporanei. Non equivale a una misura di copertura.
- **9 prove locali aggiuntive hanno riprodotto i difetti** descritti nella tabella seguente, usando il client Django con controllo CSRF attivo. Il loro esito positivo conferma il comportamento errato, non la sicurezza del progetto.
- Applicazione riuscita delle migrazioni su un database SQLite locale vuoto; controlli Django senza problemi segnalati.
- Lettura dei percorsi di autorizzazione e delle mutazioni di stato e documenti.
- Calcolo dei rapporti di contrasto di alcune coppie di colori dichiarate nel CSS.

Non eseguiti: test con PostgreSQL/NAS reali, collaudo nel browser, screenshot, Lighthouse, scansioni delle dipendenze e attacchi contro il sito pubblico. L'installazione delle dipendenze, inizialmente bloccata, è riuscita al nuovo tentativo richiesto dall'utente. Il browser ha rifiutato l'accesso all'indirizzo locale con `ERR_BLOCKED_BY_CLIENT`; non è stato aggirato il blocco. Non sono stati usati dati o credenziali di produzione.

Le priorità sotto sono di pianificazione: **P1** indica accesso ai dati, perdita di informazioni o flusso essenziale compromesso; **P2** indica difetti funzionali, accessibilità e affidabilità operativa da affrontare subito dopo. Le righe della tabella sono state riprodotte; gli altri rilievi restano riscontri statici o rischi da verificare, come indicato. I criteri di accettazione delle correzioni restano da implementare e collaudare.

| Prova locale | Risultato osservato sul codice attuale |
|---|---|
| SEC-01: cancellazione anonima | HTTP 200 e upload reso `superseded`, nonostante la pratica abbia password. |
| SEC-01: upload anonimo | PDF sintetico accettato con HTTP 200 e nuovo record creato sulla pratica protetta. |
| SEC-02: ricevuta estranea | Un grant valido per A consente HTTP 200 e lettura dei byte della ricevuta di un modulo diverso. |
| SEC-03: pratica completata | POST allo step restituisce 200 e trasforma `completed` in `in_progress`. |
| DATA-01: builder | Ritorno in bozza e salvataggio con ID esistenti restituiscono 200; il record upload precedente viene eliminato. |
| DATA-02: dichiarazione non valida | Il file `.exe` è rifiutato con 400, ma l'upload precedente diventa comunque `superseded`. |
| FORM-01: risposte dello step | POST con valori restituisce 200, ma `form_data` rimane invariato. La mancata trasmissione dal pulsante Avanti è inoltre visibile nel JavaScript. |
| FORM-02: consenso omesso | POST senza `action_type` e senza consenso porta a `submitted` e crea una dichiarazione `accepted=True`. |
| SEC-04: cambio lingua | `next=//example.invalid/audit` produce una risposta 302 verso quel dominio esterno; nessuna navigazione esterna è stata effettuata. |

Il test esistente fallito è `ApiCustomerCreateAndDashboardTests.test_upload_security_mime_fallback_warning` (`modules/tests.py:1297–1306`). Pretende un warning sul fallback MIME senza simulare l'assenza/fallimento di python-magic; in questo ambiente python-magic funziona e non emette quel warning. Rendere deterministica la prova separando percorso normale e fallback con un mock mirato. Non correggere il codice applicativo per produrre un warning falso soltanto per far passare il test.

## 2. Riscontri e correzioni

### SEC-01 · P1 · Autorizzazioni mancanti negli endpoint documentali

**Evidenza:** [views_upload.py, upload_document_view](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/views_upload.py#L176), [skip_optional_document](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/views_upload.py#L389), [delete_upload_view](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/views_upload.py#L565).

Queste viste recuperano assegnazioni e documenti tramite ID, ma non verificano l'accesso del richiedente alla pratica prima della modifica. Upload e indisponibilità recuperano inoltre il requisito globalmente, senza vincolarlo al template dell'assegnazione. Anche `published_form_upload` verifica la sessione del modulo ma recupera il requisito globalmente.

CSRF e UUID non sostituiscono l'autorizzazione: il rischio presuppone che gli identificativi siano conosciuti; non è stata dimostrata una loro enumerazione o un attacco in produzione.

**Intervento:** introdurre una policy comune per lettura e modifica, applicata a tutti gli endpoint, con controllo della relazione cliente → assegnazione → template → requisito → upload. Preservare esplicitamente il flusso previsto per i link con token; non trasformare accidentalmente tutti i clienti in utenti Django.

**Accettazione:** client anonimo, cliente A sulla pratica B e requisito estraneo non producono modifiche né file sul NAS; il cliente autorizzato mantiene il flusso previsto. Eseguire anche richieste con CSRF valido, per dimostrare che la protezione dipende dall'autorizzazione. Coprire distintamente le capacità previste per operatori e amministratori.

### SEC-02 · P1 · Accesso a ricevute non vincolato al modulo corretto

**Evidenza:** [published_form_receipt, righe 33–60](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/views_submission.py#L33).

`has_assignment_access` accetta qualsiasi chiave di sessione `assignment_access_*` con valore vero. L'accesso a una pratica può quindi autorizzare la ricevuta di un altro modulo, se se ne conosce l'ID e il PDF esiste. Il controllo non verifica la relazione tra quella sessione e il modulo richiesto.

**Intervento:** usare la policy SEC-01 per download, riepilogo e pagine di conferma; risolvere prima la risorsa autorizzata e soltanto dopo il percorso del documento. Verificare separatamente la policy delle pratiche senza password.

**Accettazione:** una sessione valida per A non scarica ricevute di B; il proprietario e i ruoli abilitati continuano a scaricare il PDF corretto. Nessun PDF deve essere generato come effetto di una richiesta non autorizzata.

### SEC-03 · P1 · Stati conclusi e scadenze non proteggono tutte le modifiche

**Evidenza:** [form_step_view, righe 232–283](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/views_form_access.py#L232), [form_submission_view](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/views_submission.py#L107), endpoint documentali di SEC-01.

Il POST allo step assegna sempre `in_progress`; il salvataggio parziale lo assegna se lo stato è diverso da `submitted`, includendo così altri stati conclusi. I percorsi di modifica non applicano una guardia comune su stato, scadenza e cliente attivo. Una sessione ancora valida può consentire modifiche o regressioni di stato non previste dal percorso iniziale.

**Intervento:** definire una tabella esplicita delle transizioni consentite. Le pratiche inviate, in lavorazione, completate, annullate o scadute devono rispettare la policy concordata; una riapertura deve essere un'azione staff esplicita e registrata. Proteggere le transizioni concorrenti con transazioni e lock appropriati.

**Accettazione:** POST diretti agli endpoint non aggirano i vincoli; doppio invio non duplica dichiarazioni o eventi; una pratica completata non torna in compilazione incidentalmente. Testare scadenza superata dopo l'apertura della pagina.

### DATA-01 · P1 · Il salvataggio del builder può cancellare lo storico documentale

**Evidenza:** [api_form_save, righe 203–215](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/forms_api.py#L203), [ripristino in bozza, righe 397–410](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/forms_api.py#L397), [relazioni DocumentUpload](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/models.py#L451).

Il salvataggio elimina tutti gli step e li ricrea. I requisiti eliminati hanno relazioni `CASCADE` con upload e dichiarazioni. Il ritorno da pubblicato a bozza è consentito anche in presenza di assegnazioni. La sequenza pubblicazione → assegnazione → upload → ritorno in bozza → salvataggio può quindi eliminare i record documentali collegati. La permanenza del file sul NAS non conserva le associazioni e lo storico nel database.

**Intervento raccomandato:** rendere immutabili le versioni già utilizzate e creare una nuova bozza/versione per modificarle, sfruttando i concetti di famiglia e versione già presenti. Per bozze senza utilizzi, mantenere comunque ID stabili dove opportuno. Non applicare cancellazioni massive per risolvere il problema.

**Accettazione:** con una pratica dotata di upload e dichiarazioni, modificare una nuova versione non cambia ID, contenuti, associazioni o ricevuta storica della precedente. Verificare anche metadati copiati, file di esempio e opzioni dei requisiti.

### DATA-02 · P1 · Una dichiarazione rifiutata invalida documenti validi

**Evidenza:** [skip_optional_document, righe 406–426](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/views_upload.py#L406).

Gli upload validi vengono marcati `superseded` prima della validazione della dichiarazione di assenza. Se il nuovo file non supera la validazione, la risposta è 400 ma i documenti precedenti sono già stati invalidati. La transazione comincia successivamente.

**Intervento:** validare prima; sostituire lo stato precedente solo quando la nuova operazione riesce. Coordinare transazione DB, scrittura file e pulizia degli eventuali file temporanei: il rollback DB non annulla automaticamente le scritture sul NAS.

**Accettazione:** file non valido, errore di scrittura e richiesta concorrente lasciano coerenti database e archivio. Il documento precedente resta valido in caso di fallimento della sostituzione.

### FORM-01 · P1 · I campi compilati non vengono salvati tra gli step

**Evidenza:** [campi nel template](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/templates/modules/form_step.html#L175), [proceedToNextStep](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/templates/modules/form_step.html#L864), [POST dello step](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/views_form_access.py#L279).

Testo, email, telefono e data sono input senza un collegamento stabile al salvataggio. Il pulsante Avanti controlla i campi e cambia URL; non invia i valori. Anche il POST della vista aggiorna soltanto step e stato, non le risposte. La validazione nel browser dà quindi un'impressione di completamento senza persistenza.

**Intervento:** assegnare identificatori stabili agli elementi; definire il formato delle risposte senza sovrascrivere i metadati già contenuti in `form_data`; validare e salvare lato server; ripopolare i campi. Far riuscire il salvataggio prima della navigazione e mostrare uno stato esplicito di salvataggio/errore. Associare label e controlli mediante `for`/`id`.

**Accettazione:** compilazione → Avanti → Indietro → refresh → nuovo accesso mantiene i valori. Email non valida è rifiutata anche con POST diretto. Un errore di rete non fa perdere i dati digitati né naviga come se il salvataggio fosse riuscito.

### FORM-02 · P1 · Invio definitivo e dichiarazione aggirabili nel backend

**Evidenza:** [views_submission.py, righe 122–187](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/views_submission.py#L122).

`action_type` ha default `complete`, ma il controllo della dichiarazione usa nuovamente il valore grezzo del POST. Se il parametro manca, oppure contiene un valore non riconosciuto diverso da `partial`, il codice può arrivare all'invio senza la verifica richiesta e registrare `accepted=True`. Non viene inoltre rivalidata integralmente la completezza dei requisiti prima dell'invio.

**Intervento:** validare un insieme chiuso di azioni; applicare a qualsiasi invio definitivo le stesse precondizioni server. Salvare una dichiarazione accettata solo in presenza di un'accettazione effettiva. Riutilizzare la validazione dei campi e dei requisiti, rispettando documenti facoltativi e indisponibilità consentite.

**Accettazione:** azione mancante/non valida, consenso assente e requisito incompleto non producono un falso invio; il percorso valido resta funzionante e idempotente. Allineare anche la regola di indisponibilità: la UI richiede un allegato formale per documenti obbligatori, mentre il backend accetta in quel punto anche sola giustificazione testuale. Documentare la regola di prodotto prima di irrigidirla.

### SEC-04 · P2 · Logout e reindirizzamento lingua incoerenti

**Evidenza:** [set_client_language](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/views_client.py#L58), [logout](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/views_client.py#L196), [grant legacy ancora accettati](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/views_form_access.py#L241).

Il logout rimuove tre chiavi del cliente, ma lascia grant `assignment_access_*` e `form_access_*`. L'accesso diretto ai documenti può rimanere disponibile. Il cambio lingua accetta inoltre destinazioni esterne: controlla `startswith('/')`, che ammette URL con doppio slash, e sottostringhe del percorso, che possono comparire anche in domini esterni.

**Intervento:** revocare tutti i grant cliente al logout, conservando lingua ed eventuale sessione staff secondo la policy; ruotare la sessione al login; gestire l'invalidazione dei grant legacy e dei token revocati. Per `next`, usare una validazione host/schema affidabile, ad esempio `url_has_allowed_host_and_scheme`.

**Accettazione:** logout seguito da accesso diretto richiede nuovamente autorizzazione; il token revocato non sopravvive grazie a una chiave legacy; il cambio lingua torna solo a una destinazione consentita. Coprire la coesistenza tra login cliente e staff.

### UPLOAD-01 · P2 · Contratto multifile/ZIP incoerente con l'interfaccia

**Evidenza:** [risposta ZIP e limite file](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/views_upload.py#L245), [rendering del risultato](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/templates/modules/form_step.html#L628), [FormData](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/templates/modules/form_step.html#L666).

- La risposta ZIP contiene `files` e `is_bulk`, ma il frontend inserisce una sola scheda usando `data.upload_id`, assente nel ramo ZIP. L'elenco e le azioni immediate non rappresentano correttamente i file estratti.
- Per requisiti multifile, superare `max_files` rende silenziosamente obsoleti i file più vecchi; il frontend non riconcilia l'intero elenco. Un limite appare quindi come una sostituzione implicita.
- Lo stesso oggetto File viene aggiunto al multipart come `file` e `file_<id>`: il contenuto binario viene trasmesso due volte.

**Intervento:** definire una risposta uniforme con la lista canonica dei documenti e gli ID reali, utilizzata da upload singolo, ZIP, sostituzione e cancellazione. Segnalare il limite prima del trasferimento e verificarlo sul server; consentire sostituzioni soltanto secondo una regola visibile. Inviare una sola parte binaria.

**Accettazione:** ZIP con due file produce due righe eliminabili; ricaricare la pagina mostra gli stessi documenti; il file oltre limite non elimina dati precedenti. Provare successo parziale, retry e timeout senza duplicazioni. Il retry degli errori esiste già: migliorarlo, non ricrearlo inutilmente.

### BUILDER-01 · P2 · Pubblicazione di dati non salvati e messaggi inesatti

**Evidenza:** [builder, save e publish](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/templates/modules/admin/builder.html#L1370), [risposta API publish](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/forms_api.py#L353).

`publish()` non salva né attende le modifiche locali. L'autosalvataggio del titolo al blur non copre il documento completo e può concorrere con Pubblica. Inoltre il frontend legge `access_password`, mentre l'API restituisce `has_password`. I messaggi di cancellazione annunciano perdita delle assegnazioni e dei documenti, mentre il backend archivia quando ci sono assegnazioni. Salvataggi riusciti generano alert bloccanti in inglese.

**Intervento:** dopo DATA-01, introdurre stato dirty/saving/saved/error, pubblicazione della revisione effettivamente salvata e gestione di conflitti tra schede. Il fallimento del salvataggio deve impedire la pubblicazione. Correggere il contratto credenziali senza esporre hash o inventare il recupero di password già hashate. Allineare conferme ed esito alle azioni reali.

**Accettazione:** una modifica immediatamente seguita da Pubblica compare nella versione pubblicata; errore di salvataggio mantiene la bozza; i messaggi spiegano correttamente archiviazione, eliminazione o creazione di nuova versione.

### OPS-01 · P1 per l'aggiornamento; P2 per la configurazione · Supporto e impostazioni

**Evidenza:** [requirements.txt](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/requirements.txt#L1), [settings.py](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/app/settings.py).

È fissato Django 4.2.14. Il supporto esteso della serie 4.2 è terminato il 7 aprile 2026, secondo la [pagina ufficiale Django](https://www.djangoproject.com/download/). Pianificare un aggiornamento verificato a una serie supportata; 5.2 LTS è una candidata conservativa, previa verifica delle dipendenze e delle note di migrazione. Non è stata eseguita una scansione CVE: non attribuire vulnerabilità specifiche senza verificarle. Il Dockerfile usa Python 3.11 mentre le prove di questo audit usano Python 3.12: ripetere i test anche nell'immagine prevista per il deploy.

Le impostazioni consentono un `SECRET_KEY` di fallback noto; in produzione i flag Secure dei cookie restano falsi se non attivati esplicitamente. Queste sono possibilità della configurazione, non una prova dei valori del deploy. La variabile `SECURE_CONTENT_SECURITY_POLICY` non è accompagnata da middleware che la applichi nello stack Django 4.2 esaminato: verificare gli header effettivi del reverse proxy prima di dichiarare assente la CSP. La cache LocMem rende i contatori del rate limit locali al processo.

**Intervento:** aggiornamento incrementale e testato; errore di avvio per segreti placeholder in produzione; configurazione HTTPS/proxy coerente; rate limit condiviso quando si usano più worker; verifica reale degli header. Se si introduce CSP, iniziare con report-only e inventario di CDN, Alpine e script inline.

**Accettazione:** suite e smoke test passano sulla nuova versione; `check --deploy` viene eseguito con configurazione equivalente a produzione, senza stampare segreti; test dei valori di default di produzione. Aggiornare le istruzioni README: i comandi `modules.tests.test_models` ecc. non corrispondono al file monolitico `modules/tests.py` presente.

### DATA-03 · P2 · Verificare coerenza di manifest e ricevute concorrenti

**Evidenza:** [aggiornamento manifest negli upload](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/views_upload.py#L305), [save_manifest_atomic](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/upload_security.py#L836), [percorso ricevuta](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/views_submission.py#L82).

Il manifest viene letto, modificato e sostituito atomicamente. La sostituzione atomica evita file parziali, ma da sola non impedisce aggiornamenti persi tra worker. Le cancellazioni logiche e le sostituzioni richiedono una riconciliazione. Il PDF usa un nome fisso nella cartella cliente/progetto: pratiche che condividono tale cartella possono interferire. La possibilità concreta dipende dalle regole di assegnazione e dal deploy: verificare con un test mirato, non dichiarare già avvenuta una perdita.

**Intervento:** definire se il manifest è un inventario corrente o uno storico e garantirne la coerenza con il database. Prevedere serializzazione o rigenerazione affidabile. Identificare univocamente gli artefatti per pratica/versione senza spostare automaticamente l'archivio storico.

**Accettazione:** due upload concorrenti e due pratiche dello stesso cliente/progetto mantengono associazioni e ricevute corrette; un file eliminato logicamente non appare come attivo nell'inventario corrente.

## 3. Direzione UI/UX premium

Queste indicazioni derivano da template e CSS. La composizione finale va giudicata su pagine renderizzate con dati realistici; non sono attribuiti punteggi visuali o di performance senza misurazione.

### Identità e componenti

Conservare logo Etichub, avorio, corallo e tono professionale. Usare Inter per dati, moduli e testo operativo, con Poppins eventualmente limitato ai titoli. Una palette coerente, spaziatura regolare e gerarchia delle azioni sono più utili di effetti decorativi aggiuntivi.

Il [design system](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/static/css/design-system.css#L1) dichiara uno stile corallo/avorio ma contiene token primari blu e indaco; i template cliente introducono ulteriori override corallo. Inoltre `.btn-primary` è outline mentre `.btn-secondary` è pieno: la gerarchia va resa intenzionale e uniforme in tutte le pagine.

Creare token semantici per sfondo, superficie, testo, testo secondario, bordo, azione e stati; mantenere scale già presenti dove sensate. Separare i colori decorativi del brand dai colori leggibili di testo e azioni. Consolidare header, badge, pulsanti, campi, alert, modali, empty state e righe documento in componenti/template riutilizzabili. Evitare nuove copie di CSS inline.

Il corallo `#E8847D` su bianco ha contrasto calcolato **2,62:1**, `#D97468` **3,16:1**. Il [template cliente](https://github.com/RazorCopter/eh-moduli/blob/6bec0b4460dfc594abaa0c930e930a2ff9ef488b/modules/templates/modules/client/base_client.html#L81) usa il primo per testo piccolo e un gradiente dei due dietro iniziali bianche. Verificare gli stili effettivi nel browser e scurire le varianti funzionali. Per testo normale il riferimento è 4,5:1, per testo grande 3:1: [WCAG, contrasto minimo](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).

### Schermate e risultati attesi

| Area | Intervento concreto | Risultato da verificare |
|---|---|---|
| Accesso cliente | Branding compatto, label persistenti, mostra/nascondi password accessibile, errori accanto ai campi, lingua coerente. Intro non bloccante. | Si comprende come entrare e come recuperare da un errore; nessuna attesa imposta a ogni visita. |
| Dashboard cliente | Mettere prima pratiche che richiedono un'azione, scadenza e CTA “Continua compilazione”. Distinguere chiaramente inviata, in lavorazione e completata. | Il cliente individua subito la prossima azione senza interpretare una percentuale ambigua. |
| Compilazione | Stepper leggibile, larghezza di lettura controllata, gruppi coerenti, requisiti e file ammessi prima dell'upload, salvataggio esplicito. | Nessuna perdita passando tra step; posizione nel percorso separata dalla completezza dei documenti. |
| Upload | Elenco con nome, dimensione, stato, azioni e feedback per singolo file. Caricamento, errore e salvataggio distinguibili. | Dopo ZIP, retry o cancellazione, elenco e server coincidono senza refresh. |
| Riepilogo/invio | Elenco dei requisiti soddisfatti/mancanti, link “Modifica” al punto corretto, dichiarazione chiara e un'unica CTA primaria. | Nessun invio accidentale; conferma con data, stato e ricevuta della pratica corretta. |
| Dashboard operatore | Evidenziare pratiche da lavorare e scadenze; ridurre il peso dei contatori che non orientano una decisione. | L'operatore trova il prossimo lavoro senza aprire ogni cliente. |
| Elenco clienti | Ricerca con label, filtri e ordinamento coerenti; differenziare elenco vuoto da nessun risultato. Valutare paginazione server sui volumi reali. | Ricerca e azioni funzionano anche con molti clienti e su viewport stretta. |
| Builder | Catalogo elementi, area centrale del modulo, proprietà dell'elemento selezionato; dirty state e salvataggio non bloccante. | È evidente cosa si sta modificando, cosa è salvato e quale versione sarà pubblicata. |

Il conteggio “Passaggio X di Y” non deve essere presentato come percentuale di documentazione completata. La vista calcola `progress_pct` dalla posizione dello step; altre percentuali seguono il ciclo operativo della pratica. Mostrare separatamente avanzamento di compilazione, requisiti soddisfatti e stato della lavorazione, senza cambiare arbitrariamente le regole esistenti.

Nel builder sostituire alert di routine con feedback persistente vicino a Salva; mantenere conferme leggibili per operazioni distruttive. Fornire riordino tramite pulsanti o tastiera oltre all'eventuale trascinamento. Limitare le proprietà visibili a quelle pertinenti all'elemento selezionato.

### Accessibilità, mobile e qualità percepita

- Focus visibile, ordine tab naturale, nomi accessibili delle azioni iconiche, label collegate ai campi. Le dropzone che funzionano solo via click su `div` devono avere un controllo da tastiera equivalente; il normale upload ha già un pulsante alternativo, mentre va verificata in particolare la dichiarazione di assenza.
- Errori associati ai campi e annunciati; feedback asincrono con `aria-live` appropriato. Se Avanti è disabilitato, mostrare cosa manca nel contenuto, non soltanto in un tooltip.
- Usare testo e icone insieme ai colori per gli stati. Allineare `html lang` alla lingua selezionata e tradurre anche messaggi JavaScript e API visibili.
- Target pratico di progetto: controlli touch principali di circa 44×44 px. È un obiettivo di comodità, distinto dal minimo AA di 24×24 CSS px con eccezioni previsto da [WCAG 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).
- Verificare 360, 390, 768, 1280 e 1440 px, zoom al 200%, nomi file lunghi, email lunghe, testo tradotto ed elenchi numerosi. Nessuno scroll orizzontale dell'intera pagina; eventuali tabelle larghe hanno contenitore dedicato.
- L'intro già rileva `prefers-reduced-motion`: preservare questa funzione e verificare che nessuna schermata rimanga coperta in caso di script lento o assente. Animazioni brevi e funzionali; nessun nuovo effetto che ritardi le azioni.

## 4. Ordine di esecuzione per Sol

| Lotto | Contenuto | Dipendenze e uscita |
|---|---|---|
| 0 — Baseline | Leggere istruzioni locali, stato Git, configurazione e test; ambiente isolato con storage temporaneo; riprodurre i P1. | Registrare test effettivi e limiti. Nessun contatto con NAS/DB reali. |
| 1 — Accessi | SEC-01, SEC-02, SEC-03, SEC-04. | Policy condivisa e matrice negativa/positiva verificata. |
| 2 — Integrità | DATA-01, DATA-02, FORM-01, FORM-02. | Storico conservato, campi persistenti, invio validato dal server. |
| 3 — Piattaforma | OPS-01. | Framework supportato, configurazione controllata, suite nuovamente eseguita. |
| 4 — Upload e builder | UPLOAD-01, BUILDER-01, test mirati DATA-03 e correzioni confermate. | Contratti frontend/backend coerenti e niente sostituzioni implicite. |
| 5 — Sistema visivo e portale | Token/componenti, accesso, dashboard cliente, compilazione, riepilogo. | Confronto prima/dopo nel browser, responsive e tastiera. |
| 6 — Strumenti operatore | Dashboard, elenco clienti, builder, microcopy e stati vuoti. | Percorsi principali collaudati e stile uniforme. |
| 7 — Chiusura | Test di regressione pertinenti, documentazione, report di rischi residui. | Consegna revisionabile; nessun test non eseguito presentato come passato. |

Non serve un grande refactor trasversale per ogni difetto. Tenere le modifiche divise in lotti revisionabili. Le prove di concorrenza devono usare PostgreSQL: SQLite non dimostra il corretto comportamento dei lock in produzione. Se non disponibile, segnalarle come ancora da eseguire.

## 5. Prompt completo da dare a Codex in VS Code

Copia il testo seguente in una nuova conversazione Codex, con il repository aperto e questo documento allegato o salvato come `docs/eh-moduli_audit_e_piano_sol.md`.

```text
Lavora sul repository RazorCopter/eh-moduli aperto in VS Code. Voglio migliorare concretamente affidabilità, sicurezza e qualità UI/UX di Etichub, mantenendo le funzionalità e l'identità del prodotto. Agisci come sviluppatore senior Django e product engineer con competenze di accessibilità.

Leggi il documento eh-moduli_audit_e_piano_sol.md allegato o presente in docs/. È un audit del commit 6bec0b4460dfc594abaa0c930e930a2ff9ef488b con analisi statica, suite Django e 9 riproduzioni locali. Distingui i difetti riprodotti dagli altri rilievi e verifica tutti quelli pertinenti sul codice attuale. Non applicare meccanicamente indicazioni ormai superate.

Il tuo obiettivo è implementare e verificare le correzioni, poi il restyling. Non fermarti a un elenco di consigli. Procedi autonomamente per lotti piccoli e revisionabili, aggiornando un registro di avanzamento con evidenze, decisioni e verifiche. Se il lavoro supera una sessione, lascia un checkpoint preciso e continua finché l'ambiente lo consente.

PRIMA DI MODIFICARE
1. Leggi AGENTS.md e istruzioni applicabili. Esamina README, dipendenze, configurazione, routing, modelli e test. Controlla branch, commit e modifiche locali; preserva il lavoro esistente e usa un branch isolato quando opportuno.
2. Avvia un ambiente di sviluppo con dati fittizi e storage temporaneo. Non utilizzare database, credenziali, email o NAS di produzione. Rileva i comandi reali di avvio/test dal repository: alcune istruzioni README potrebbero essere obsolete.
3. Esegui una baseline dei test disponibili. Se l'ambiente è bloccato, registra esattamente il limite, completa il lavoro locale possibile e non dichiarare verifiche mai eseguite.

ORDINE DI LAVORO
Segui i lotti 0–7 del documento: autorizzazioni e stati; integrità e persistenza dei dati; piattaforma supportata; upload e builder; design system e portale cliente; strumenti operatore; collaudo finale. Non chiedere conferma per passare a ogni lotto già descritto. Se una regola di business non può essere dedotta in sicurezza, completa prima le parti indipendenti e fai una domanda specifica spiegando l'impatto.

PER OGNI DIFETTO
- Verifica il percorso effettivo e scrivi una breve riproduzione locale. Per accessi e integrità aggiungi un test di regressione significativo che fallisca prima della correzione, quando l'ambiente lo permette.
- Implementa la soluzione più piccola che risolva la causa comune. Evita controlli copiati in ogni vista: usa policy e validazioni condivise quando necessario.
- Copri casi autorizzati e non autorizzati, appartenenza delle risorse, stati conclusi/scaduti, errori di scrittura, doppio invio e retry. Le richieste rifiutate non devono produrre effetti su DB o storage.
- Conserva documenti, risposte, associazioni e storico. Per template già utilizzati privilegia versioni immutabili. Non risolvere incongruenze cancellando dati.
- Esegui i test pertinenti; amplia la suite solo per verificare rischi concreti o soddisfare i controlli del progetto.

OBIETTIVO VISIVO
Conserva Django, template server, Bootstrap, Alpine e logo Etichub. Mantieni la direzione avorio/corallo, con varianti leggibili per testo e azioni. Non introdurre React, Tailwind o un'altra riscrittura senza una necessità documentata.
Rendi coerenti tipografia, spaziature, colori semantici, bottoni, badge, form, modali e feedback. Concentrati su gerarchia, leggibilità, precisione dei messaggi e facilità di completamento. Una CTA primaria per contesto. Stato “salvato” solo dopo conferma del server. Separazione chiara tra avanzamento degli step, completezza documenti e lavorazione della pratica.
Implementa i miglioramenti schermata per schermata descritti nell'audit. Riutilizza componenti e CSS; riduci gli override e non aggiungere nuove copie di stili inline. Preserva le funzioni utili già presenti, inclusi retry e reduced motion.

VERIFICA UI
Se disponibile, usa il browser per vedere davvero l'applicazione con dati fittizi realistici. Acquisisci screenshot prima e dopo a desktop e mobile; controlla anche stati vuoti, caricamento, errori, nomi lunghi, upload ZIP e flussi conclusi. Verifica 360/390/768/1280/1440 px, zoom 200%, tastiera, focus, contrasto, label e modali. Correggi i difetti osservati e ripeti le verifiche necessarie. Non inventare screenshot, punteggi Lighthouse o risultati di accessibilità.

LIMITI OPERATIVI
Sono autorizzate implementazione e verifiche locali dei task descritti. Non fare deploy, push, merge, cancellazioni distruttive, migrazioni su produzione o invii reali a clienti. Non aggiungere nuove dipendenze senza un beneficio concreto; per un aggiornamento del framework consulta documentazione ufficiale e compatibilità. Mantieni segreti e dati personali fuori da log e report.

CONSEGNA
Aggiorna il registro con ID task, problema verificato/non confermato, soluzione, file modificati, test eseguiti ed esito. Documenta eventuali migrazioni e rollout da revisionare. Alla fine comunica cosa funziona meglio, quali rischi restano, come avviare e verificare il progetto e dove trovare gli screenshot reali. Distingui chiaramente lavoro completato, verifiche bloccate e attività residue.

Inizia ora dalla baseline e dai problemi P1; prosegui poi con il resto del piano.
```

## 6. Prompt breve di avvio

Se alleghi questo file alla conversazione in VS Code, basta scrivere:

```text
Leggi eh-moduli_audit_e_piano_sol.md allegato e applica il prompt completo della sezione 5 al repository aperto. Verifica i riscontri sul codice attuale e procedi con implementazione e test nell'ordine dei lotti. Inizia da accessi, integrità dei documenti e persistenza dei campi, poi completa il restyling UI/UX. Sono autorizzate le modifiche locali; niente deploy o operazioni sui dati di produzione.
```


## 7. Riproduzioni locali riutilizzabili

Il codice seguente è quello eseguito durante l'audit. **Le asserzioni verificano la presenza dei difetti:** dopo una correzione è normale che queste prove smettano di passare. Sol deve convertirle in test di regressione che richiedano il comportamento corretto, senza indebolire le asserzioni per ottenere un risultato verde.

Usare esclusivamente database di test e cartelle temporanee. Il setup usa dati fittizi e CSRF attivo; non modifica sorgenti del progetto. Per riprodurre, salvare il blocco come `audit_probes.py` in un percorso Python importabile ed eseguire `python manage.py test audit_probes --noinput --verbosity 2` con configurazione di sviluppo isolata (`ENVIRONMENT=development`, `USE_SQLITE=true`, `DEBUG=true`) e percorsi documentali temporanei. L'audit ha usato un modulo di impostazioni esterno con SQLite, email in memoria e rate limit disattivato per i test. Per produzione restano necessarie prove specifiche con PostgreSQL, worker multipli e storage equivalente al NAS.

```python
"""Disposable probes asserting observed defects, NOT tests asserting secure behavior."""
import io
import json
import os
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from reportlab.pdfgen.canvas import Canvas
from modules.models import User, Customer, FormTemplate, FormStep, DocumentRequirement, FormAssignment, DocumentUpload, AwarenessDeclaration


class ObservedDefectProbes(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='eh_audit_probe_')
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {'CUSTOMER_DOCUMENTS_CONTAINER_PATH': self.tmp.name, 'CUSTOMER_DOCUMENTS_PATH': self.tmp.name})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.user = User.objects.create_user(username='audit_admin', password='local-test-only', role='admin', is_staff=True)
        self.customer = Customer.objects.create(code='AUDIT-A', first_name='Cliente', last_name='Fittizio', email='audit@example.invalid', nas_folder_name='AUDIT_A')
        self.customer.set_portal_password('local-portal-test')
        self.customer.save()
        self.form = FormTemplate.objects.create(name='Audit Form', status='published', customer=self.customer, project_name='AuditProject')
        self.step = FormStep.objects.create(form_template=self.form, title='Step Audit', order=0)
        self.req = DocumentRequirement.objects.create(form_step=self.step, name='Documento', allowed_extensions='pdf', destination_subfolder='Documenti', required=True, order=0)
        self.assignment = FormAssignment.objects.create(customer=self.customer, form_template=self.form, operator=self.user, expiry_date=timezone.now()+timedelta(days=30), status='in_progress', form_data={'client_name': 'AUDIT_A', 'project_name': 'AuditProject'})
        self.upload = DocumentUpload.objects.create(form_assignment=self.assignment, document_requirement=self.req, original_filename='existing.pdf', status='valid', uploaded_by_ip='127.0.0.1', uploaded_by_user_agent='Audit')
        self.client = Client(enforce_csrf_checks=True)
        self.client.get(reverse('client_login'))
        self.csrf = self.client.cookies['csrftoken'].value

    def grant(self):
        session = self.client.session
        session[f'assignment_access_{self.assignment.id}_{self.assignment.secure_token}'] = True
        session.save()

    def post(self, name, kwargs, data=None):
        return self.client.post(reverse(name, kwargs=kwargs), data or {}, HTTP_X_CSRFTOKEN=self.csrf, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_observed_SEC01_anonymous_delete(self):
        self.assertTrue(self.assignment.has_access_password())
        response = self.post('delete_upload_view', {'assignment_id': self.assignment.id, 'upload_id': self.upload.id})
        self.upload.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.upload.status, 'superseded')

    def test_observed_SEC01_anonymous_upload(self):
        buffer = io.BytesIO()
        canvas = Canvas(buffer)
        canvas.drawString(40, 700, 'Synthetic audit document')
        canvas.save()
        file = SimpleUploadedFile('audit.pdf', buffer.getvalue(), content_type='application/pdf')
        response = self.post('upload_document_view', {'assignment_id': self.assignment.id}, {'requirement_id': str(self.req.id), 'file': file})
        self.assertEqual(response.status_code, 200, response.content[:300])
        self.assertTrue(DocumentUpload.objects.filter(form_assignment=self.assignment, original_filename='audit.pdf').exists())

    def test_observed_DATA02_invalid_absence_invalidates_existing(self):
        self.grant()
        file = SimpleUploadedFile('invalid.exe', b'not a declaration', content_type='application/octet-stream')
        response = self.post('skip_optional_document', {'assignment_id': self.assignment.id, 'requirement_id': self.req.id}, {'file': file})
        self.upload.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.upload.status, 'superseded')

    def test_observed_DATA01_builder_deletes_upload(self):
        self.client.force_login(self.user)
        response = self.post('api_form_revert_to_draft', {'form_id': self.form.id})
        self.assertEqual(response.status_code, 200)
        payload = {'name': self.form.name, 'steps': [{'id': str(self.step.id), 'title': self.step.title, 'elements': [{'id': str(self.req.id), 'type': 'document', 'name': self.req.name, 'destination_subfolder': 'Documenti'}]}]}
        response = self.client.put(reverse('api_form_save', kwargs={'form_id': self.form.id}), json.dumps(payload), content_type='application/json', HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 200, response.content[:300])
        self.assertFalse(DocumentUpload.objects.filter(id=self.upload.id).exists())

    def test_observed_FORM02_missing_action_and_consent_submits(self):
        self.grant()
        response = self.post('form_submission_view', {'assignment_id': self.assignment.id})
        self.assignment.refresh_from_db()
        self.assertIn(response.status_code, (200, 302))
        self.assertEqual(self.assignment.status, 'submitted')
        self.assertTrue(AwarenessDeclaration.objects.filter(form_assignment=self.assignment, accepted=True).exists())

    def test_observed_SEC03_completed_reverts_to_in_progress(self):
        self.grant()
        self.assignment.status = 'completed'
        self.assignment.save()
        response = self.post('form_step_view', {'assignment_id': self.assignment.id, 'step_order': 0})
        self.assignment.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.assignment.status, 'in_progress')

    def test_observed_SEC02_unrelated_receipt_access(self):
        self.grant()
        other = FormTemplate.objects.create(name='Other customer form', project_name='OTHER_PROJECT')
        destination = Path(self.tmp.name) / '_generic' / 'OTHER_PROJECT'
        destination.mkdir(parents=True)
        (destination / 'Report_Ricezione_Documenti.pdf').write_bytes(b'%PDF-1.4\nSynthetic unrelated receipt')
        response = self.client.get(reverse('published_form_receipt', kwargs={'form_id': other.id}))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Synthetic unrelated receipt', b''.join(response.streaming_content))

    def test_observed_SEC04_external_language_redirect(self):
        response = self.client.get(reverse('set_client_language_query'), {'next': '//example.invalid/audit'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '//example.invalid/audit')

    def test_observed_FORM01_step_post_discards_fields(self):
        self.grant()
        before = self.assignment.form_data.copy()
        response = self.post('form_step_view', {'assignment_id': self.assignment.id, 'step_order': 0}, {'email': 'compiled@example.invalid', 'answers': json.dumps({'field': 'compiled'})})
        self.assignment.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.assignment.form_data, before)
```

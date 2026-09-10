# EH-Moduli 3.1.0 — Specifiche per l'identità istituzionale Etichub

Data: 10 settembre 2026.

Repository verificato: [RazorCopter/eh-moduli](https://github.com/RazorCopter/eh-moduli), tag `v3.1.0`, commit `50232d9289383b383abc1207399cc9ce81d7d6a5`. Il commit del tag coincide con `origin/main` al momento dell'acquisizione. Versione confermata in `pyproject.toml`.

Fonte grafica: **EH_Sistema Grafico_260811_Revisione v9_note AV.pdf**, 26 pagine PDF, corrispondenti alle tavole numerate 18–43. Sono tavole applicative con annotazioni, non il manuale completo con la tabella dei colori. Esaminate tutte le pagine come panoramica e ingrandite le tavole pertinenti a intestati, pagina editoriale e brochure.

## 1. Decisione principale

L'interfaccia deve rendere riconoscibili i **tre colori esatti indicati dall'utente**, attraverso elementi visibili delle schermate. La loro semplice presenza in `:root` non soddisfa il requisito.

**Su Intense Rust e sugli altri fondi scuri, titoli, etichette, icone e testi devono essere bianchi e leggibili.** Sui fondi Blue Aura e lilla, che sono chiari, usare Intense Rust o testo scuro. Questa regola prevale sulle precedenti proposte avorio/corallo e sulle varianti rosse presenti nel progetto.

Lo scopo è aggiornare l'identità visiva mantenendo i flussi della 3.1.0: salvataggio bozza, navigazione tra step, upload multipli/cartelle/ZIP, versionamento del builder, traduzioni e controlli di accesso. Questo documento non autorizza un nuovo refactor del backend o un deploy.

## 2. Palette confermata e abbinamenti obbligatori

| Colore | HEX esatto | RGB | Testo e icone sulla superficie | Uso nell'app |
|---|---|---|---|---|
| Intense Rust | `#6B000F` | `107, 0, 15` | `#FFFFFF` | CTA primaria, zone scure di testata, stato selezionato forte, titoli su superfici chiare |
| Blue Aura | `#B1D0E1` | `177, 208, 225` | `#6B000F` | Testate informative, pannelli di contesto, selezione nella navigazione, motivo grafico degli intestati |
| Colore 3 — lilla, nome descrittivo | `#C5BED8` | `197, 190, 216` | `#6B000F` | Aree di contenuto transfer/regolatorio, proprietà nel builder e pannelli secondari pertinenti |
| Bianco funzionale | `#FFFFFF` | `255, 255, 255` | Rust o testo scuro quando usato come superficie | Testo sui fondi scuri; superfici di lettura e campi |

Il nome istituzionale del terzo colore non è stato fornito. Nel PDF la famiglia lilla identifica **transfer**, che comprende regulatory, scientific communication e training. Non chiamarlo ufficialmente “Regulatory Lavender” o assegnargli un significato inventato. Non associare automaticamente il lilla a uno stato operativo come “completato”.

### Leggibilità verificata sui colori pieni

| Primo piano / sfondo | Rapporto calcolato | Indicazione |
|---|---:|---|
| Bianco / Intense Rust | 12,87:1 | Abbinamento da usare su CTA e pannelli scuri |
| Intense Rust / Blue Aura | 7,95:1 | Abbinamento da usare sui pannelli azzurri |
| Intense Rust / lilla | 7,19:1 | Abbinamento da usare sui pannelli lilla |
| Bianco / Blue Aura | 1,62:1 | Non usare per testo informativo |
| Bianco / lilla | 1,79:1 | Non usare per testo informativo |
| Intense Rust / fondo carta proposto `#F5F3F2` | 11,63:1 | Adatto a titoli e collegamenti |

Calcoli su valori sRGB pieni, senza trasparenza. Verificare nuovamente gli stili effettivi, soprattutto se un antenato imposta opacità, gradienti, filtri o colori dei link. Il riferimento per testo normale è almeno 4,5:1, per testo grande almeno 3:1: [WCAG, contrasto minimo](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). Per gli elementi visivi necessari a identificare controlli e stati, verificare il requisito applicabile di 3:1: [WCAG, contrasto non testuale](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html).

**Non dichiarare conforme l'intera interfaccia perché questi tre abbinamenti passano:** placeholder, messaggi, focus, badge, elementi disabilitati e contenuti dinamici richiedono controlli nel contesto.

### Dove devono vedersi davvero i tre colori

- **Rust:** pulsante principale pieno in ogni flusso operativo; testo bianco esplicito. Nei pannelli scuri, anche sottotitoli e icone devono ricevere il colore di primo piano corretto, senza grigi ereditati da `.text-muted`.
- **Blue Aura:** superficie piena della fascia informativa in dashboard cliente e del pannello riepilogativo dello step; selezione della navigazione amministrativa e linee decorative negli intestati. Non ridurlo a un bordino quasi invisibile o a una tinta sbiadita.
- **Lilla:** superficie riconoscibile per pannelli relativi al contenuto regolatorio/transfer e per il pannello proprietà nel builder. Dove non esiste tale categoria, usarlo con parsimonia per contesto secondario, senza cambiare il significato degli stati.
- **Bianco e carta:** aree di lettura, moduli e tabelle. Evitare grandi distese scure su schermate operative dense; la presenza del marchio non deve compromettere la scansione dei dati.

Non è necessario forzare tutti e tre i colori su ogni pagina. Devono però risultare riconoscibili nei percorsi principali e nei componenti condivisi.

## 3. Colori ricavati dal PDF: campioni, non codici ufficiali

Il PDF contiene immagini e mockup di stampa. Il colore RGB di un pixel renderizzato può differire dal codice del marchio per profili colore, immagini incorporate e trasformazioni di esportazione. Per i tre colori confermati fanno fede i codici dell'utente, anche quando i campioni del PDF differiscono.

| Area nelle tavole | Campione indicativo del PDF | Riferimento | Decisione per la prima implementazione |
|---|---|---|---|
| Imagine — giallo | circa `#FAD678` | PDF pagina 20, tavola 37 | Catalogare; non attivare come nuovo colore principale |
| Prove — verde menta | circa `#8FD6C3` | PDF pagina 21, tavola 38 | Catalogare; non confondere automaticamente con successo/validazione |
| Transfer — lilla | circa `#C9BCD6` | PDF pagina 22, tavola 39 | Usare invece il valore confermato `#C5BED8` |
| Cultivate — azzurro più vivo | circa `#8DD2E3` | PDF pagina 23, tavola 40 | Catalogare; non sostituire Blue Aura `#B1D0E1` |
| Carta chiara della brochure | circa `#F5F3F2` | Variante destra delle tavole 37–40 | Utilizzabile come neutro proposto, non ufficiale |

Metodo: campionamento dei pixel predominanti dei titoli e di aree di fondo delle pagine renderizzate con PyMuPDF. I campioni non includono i riquadri gialli delle annotazioni, le scritte rosse di revisione o i colori dell'Università presenti nei biglietti da visita. Questi ultimi non appartengono automaticamente alla palette Etichub.

Le tavole 42 e 43 mostrano alternative ad angoli retti e arrotondati: il PDF non certifica una sola variante definitiva. La proposta web seguente usa arrotondamenti moderati, coerenti con le tavole precedenti e con l'interfaccia esistente.

## 4. Cosa rende riconoscibile il sistema grafico

### Font

Le note delle tavole 19, 24, 25 e 26 indicano esplicitamente **PP Valve come font istituzionale**. Nel repository non sono presenti file `.woff`, `.woff2`, `.otf` o `.ttf`.

Per una riproduzione fedele occorrono i file web PP Valve utilizzabili nel progetto, con i pesi reali disponibili. Non estrarre o ricostruire font dalle immagini del PDF. Non trattare Helvetica, rilevato nei testi di presentazione del PDF, come prova che sia il font istituzionale.

Implementazione:

- predisporre un solo punto di dichiarazione della famiglia tipografica;
- usare PP Valve quando i file corretti sono disponibili, con `font-display: swap` e pesi corrispondenti ai file;
- in loro assenza usare **Inter come fallback provvisorio già noto al progetto**, dichiarando il requisito tipografico parziale; non fermare le altre attività;
- rimuovere l'alternanza accidentale tra Poppins, Inter, Segoe UI e font di sistema nelle diverse sezioni;
- non ridisegnare il logotipo digitando “etichub” con il font dei testi.

Scala web proposta, da verificare con il font finale: corpo 16 px, testo secondario 14 px, label 14–16 px, titoli di pagina 28–32 px desktop e 24–28 px mobile, titoli di pannello 18–20 px. Le dimensioni sono una traduzione operativa, non quote prescritte dal PDF. Non inventare pesi come 450 o 550 senza una famiglia che li supporti.

### Logo e motivo a linea curva

La tavola 19 prescrive l'alternanza **logo Rust e linea Blue Aura**. Le tavole editoriali e della brochure ripetono una linea continua con angoli arrotondati, rientranze e cambi di direzione. Questo è il segno più distintivo, oltre a colori e font.

- Header chiaro con logo Rust e linea Blue Aura; spazio libero attorno al marchio.
- Motivo curvo in un componente decorativo condiviso per login, testata dashboard e alcuni pannelli di contesto. Scegliere pochi impieghi, evitando una cornice su ogni campo o riga.
- Linea web sottile, indicativamente 1–2 px; decorativa, `aria-hidden="true"`, senza intercettare click o focus.
- Curve costruite con SVG/CSS responsive. Conservare gli asset ufficiali del logo; se occorre una variante Rust web, mantenere integralmente geometria e proporzioni e rendere esplicita la variante.
- Su fondo Rust usare il marchio in negativo bianco quando disponibile. Non applicare filtri globali a immagini o loghi di terze parti.
- Su richiesta dell'utente, usare anche gradienti controllati: famiglia Rust per CTA/testate scure con testo bianco, Blue Aura→lilla per pannelli chiari con testo Rust. Conservare aree di colore istituzionale esatto e limitare la sfumatura a tre colori a elementi decorativi senza testo. Specifiche nella sezione 11.

### Superfici e densità

La traduzione web deve conservare spazi bianchi, allineamenti netti e gerarchia tipografica. Proposta: raggio 8 px per controlli, 16 px per pannelli operativi, 24 px per contenitori editoriali; ombre leggere soltanto per elevazione reale. Mantenere le tabelle più compatte delle schede informative.

Non usare la cornice grigia con titoli e numeri di pagina del documento di presentazione come layout dell'app: osservare gli elaborati mostrati nelle tavole.

## 5. Riscontri specifici sul repository 3.1.0

Questa è una nuova ispezione mirata a stili, asset e struttura delle schermate. Non sono stati rieseguiti in questo passaggio i test backend o il collaudo browser della 3.1.0; non si attribuiscono al commit corrente i risultati delle precedenti versioni.

| ID | Riscontro verificato nel codice | Intervento |
|---|---|---|
| BRAND-01 | I tre HEX sono già definiti in `modules/static/css/design-system.css:9–20`, ma le pagine usano più sistemi di variabili e numerosi colori diretti. | Una fonte unica dei token e migrazione degli utilizzatori, comprese le pagine autonome. |
| BRAND-02 | `design-system.css:225` e numerose regole di input/checkbox mantengono `#0284C7`; ci sono ombre blu con `rgba(2,132,199,...)` e stati attivi `#0370B9`. | Correggere anche focus, hover, active, checked, bordi e ombre; non soltanto i colori di default. |
| BRAND-03 | `.btn-primary` è trasparente e `.btn-secondary` pieno nel design system, mentre singoli template impongono varianti piene con `!important`. | Primario Rust/bianco; secondario bianco/Rust oppure Blue Aura/Rust quando semanticamente appropriato. Consolidare le regole esistenti. |
| BRAND-04 | Login cliente usa `--brand: #7F1718`; animazione usa una costante dello stesso colore; il logo SVG contiene `fill: #7F1718`. | Allineare login, intro e variante del logo a `#6B000F`. Conservare forma, tempi e comportamento dell'intro. |
| BRAND-05 | `form_password.html` e `form_success.html` conservano `--brand-500: #E8847D` e varianti corallo. | Migrare anche accesso con password e conferma finale, evitando un cambio identità alla fine del percorso. |
| BRAND-06 | Il builder è una pagina HTML autonoma con proprie variabili, font di sistema e stylesheet Bootstrap; non importa il design system principale. | Importare i token e i componenti condivisi senza compromettere il suo layout. Cambiare solo `design-system.css` non basta. |
| BRAND-07 | `accounts/base.html` e `base_client.html` caricano Poppins/Inter; `base_etichub.html` mantiene ulteriori definizioni. | Uniformare font e ordine CSS in tutte le shell effettivamente usate. |
| BRAND-08 | `admin-layout.css` è duplicato in `static/css` e `modules/static/css`; la copia root è cercata tramite `STATICFILES_DIRS`. Le due copie sono identiche nello snapshot. | Individuare la risorsa servita con `findstatic`, scegliere una sorgente canonica e migrare evitando modifiche alla copia non utilizzata. |
| BRAND-09 | `form_step.html` contiene numerosi override `!important`, una CTA a gradiente, focus blu sull'eliminazione e la barra di navigazione sticky recentemente corretta. | Migrare in componenti condivisi e preservare i tre slot di navigazione e la visibilità di Avanti. |
| BRAND-10 | `form_summary.html:11` usa una linea a gradiente Rust→verde; `404.html` mantiene il blu precedente. | Linea istituzionale Blue Aura dove decorativa; colori di stato solo dove esprimono uno stato. Includere le pagine di errore. |
| BRAND-11 | `modules/report_generator.py:99–103` usa Rust `#7F1718`, grigi freddi e Helvetica; il report PDF non eredita il CSS. | Lotto specifico per l'aspetto delle nuove ricevute, preservando dati, percorsi e ricevute storiche. |
| BRAND-12 | Le immagini in `collaudo/evidenze/ui/` risalgono nel log al commit `02b1a7d`, release 3.0.0. | Acquisire screenshot nuovi sul commit oggetto del restyling; non riutilizzarli come prova del risultato 3.1.0. |

Misura della dispersione, ottenuta con ricerca testuale: nei 35 template HTML sotto `modules/templates` compaiono 330 valori HEX distinti e 485 attributi `style`. Il conteggio include colori semantici, codice/commenti e pagine diverse: non significa che siano tutti contemporaneamente visibili o tutti da eliminare. Spiega però perché una sostituzione di tre variabili non uniforma l'app.

Evidenze permanenti principali: [design-system.css](https://github.com/RazorCopter/eh-moduli/blob/50232d9289383b383abc1207399cc9ce81d7d6a5/modules/static/css/design-system.css), [login cliente](https://github.com/RazorCopter/eh-moduli/blob/50232d9289383b383abc1207399cc9ce81d7d6a5/modules/templates/modules/client/login.html), [builder](https://github.com/RazorCopter/eh-moduli/blob/50232d9289383b383abc1207399cc9ce81d7d6a5/modules/templates/modules/admin/builder.html), [form step](https://github.com/RazorCopter/eh-moduli/blob/50232d9289383b383abc1207399cc9ce81d7d6a5/modules/templates/modules/form_step.html), [generatore ricevute](https://github.com/RazorCopter/eh-moduli/blob/50232d9289383b383abc1207399cc9ce81d7d6a5/modules/report_generator.py).

## 6. Specifica tecnica dei token

Mantenere separati colore di superficie e colore del contenuto. Un alias come `--color-info: Blue Aura` non deve finire usato come testo su bianco. Introdurre una fonte canonica, per esempio `modules/static/css/brand-tokens.css`, e farla utilizzare dai componenti esistenti.

Le varianti e i neutri sotto sono proposte web, non ulteriori colori istituzionali. I tre valori centrali non si modificano.

```css
:root {
  /* Valori istituzionali confermati */
  --eh-rust: #6b000f;
  --eh-on-rust: #ffffff;
  --eh-aura: #b1d0e1;
  --eh-on-aura: #6b000f;
  --eh-lilac: #c5bed8;
  --eh-on-lilac: #6b000f;

  /* Varianti operative proposte */
  --eh-rust-hover: #4f000b;
  --eh-rust-active: #400009;
  --eh-rust-soft: #fbf2f3;
  --eh-gradient-rust: linear-gradient(125deg, #6b000f 0%, #6b000f 25%, #8c0a1a 60%, #4f000b 100%);
  --eh-gradient-pastel: linear-gradient(120deg, #b1d0e1 0%, #b1d0e1 20%, #c5bed8 100%);
  --eh-gradient-signature: linear-gradient(90deg, #6b000f 0%, #b1d0e1 52%, #c5bed8 100%);
  --eh-surface: #ffffff;
  --eh-paper: #f5f3f2;
  --eh-text: #2c2623;
  --eh-text-muted: #6a6260;
  --eh-border: #ded8d5;
  --eh-control-border: #8b8280;

  /* Ruoli di componente */
  --eh-action-bg: var(--eh-rust);
  --eh-action-fg: var(--eh-on-rust);
  --eh-context-bg: var(--eh-aura);
  --eh-context-fg: var(--eh-on-aura);
  --eh-transfer-bg: var(--eh-lilac);
  --eh-transfer-fg: var(--eh-on-lilac);
  --eh-focus: var(--eh-rust);
  --eh-font-brand: 'PP Valve', 'Inter', sans-serif;
  --eh-radius-control: 8px;
  --eh-radius-panel: 16px;
  --eh-radius-editorial: 24px;

  /* Alias temporanei per migrare gli utilizzatori esistenti */
  --color-primary: var(--eh-rust);
  --color-primary-hover: var(--eh-rust-hover);
  --color-primary-lighter: var(--eh-rust-soft);
  --color-secondary: var(--eh-aura);
  --color-regolatorio: var(--eh-lilac);
  --color-bg: var(--eh-paper);
  --color-bg-light: var(--eh-surface);
  --color-text: var(--eh-text);
  --color-text-light: var(--eh-text-muted);
  --font-primary: var(--eh-font-brand);
  --font-secondary: var(--eh-font-brand);
}
```

Non aggiungere questi alias lasciando più avanti nel CSS le vecchie definizioni con lo stesso nome: la cascata potrebbe annullarli. Spostare o sostituire le definizioni esistenti e controllare i valori calcolati dal browser.

Ordine indicativo: Bootstrap e icone → font/token condivisi → design system → layout → regole specifiche della pagina, limitate alla struttura. Anche le pagine che non usano Bootstrap devono caricare i token. Non obbligare il builder a ereditare una shell amministrativa diversa solo per ottenere i colori.

### Regole di primo piano da applicare ai componenti

```css
.eh-surface-rust {
  background-color: var(--eh-rust);
  color: var(--eh-on-rust);
}
.eh-surface-aura {
  background-color: var(--eh-aura);
  color: var(--eh-on-aura);
}
.eh-surface-lilac {
  background-color: var(--eh-lilac);
  color: var(--eh-on-lilac);
}

/* Usare classi esplicite per i contenuti; non sbiancare tutti i discendenti. */
.eh-surface-rust > .eh-panel-title,
.eh-surface-rust > .eh-panel-description,
.eh-surface-rust .eh-on-dark {
  color: var(--eh-on-rust);
}

/* Regole da integrare nelle definizioni esistenti del pulsante primario. */
.btn-primary {
  --bs-btn-color: var(--eh-on-rust);
  --bs-btn-bg: var(--eh-rust);
  --bs-btn-border-color: var(--eh-rust);
  --bs-btn-hover-color: var(--eh-on-rust);
  --bs-btn-hover-bg: var(--eh-rust-hover);
  --bs-btn-hover-border-color: var(--eh-rust-hover);
  --bs-btn-active-color: var(--eh-on-rust);
  --bs-btn-active-bg: var(--eh-rust-active);
  --bs-btn-active-border-color: var(--eh-rust-active);
  color: var(--eh-on-rust);
  background: var(--eh-rust);
  background-image: var(--eh-gradient-rust);
  border-color: var(--eh-rust);
}
.btn-primary:hover:not(:disabled):not(.disabled) {
  color: var(--eh-on-rust);
  background: var(--eh-rust-hover);
  border-color: var(--eh-rust-hover);
}
.btn-primary:active:not(:disabled):not(.disabled) {
  color: var(--eh-on-rust);
  background: var(--eh-rust-active);
  border-color: var(--eh-rust-active);
}
```

Questi sono contratti ed esempi da integrare, non un file da appendere indiscriminatamente in fondo alla cascata. Completare focus, loading e disabled nella stessa definizione canonica. Le icone devono usare `currentColor`. Nei pannelli scuri, eventuali campi con fondo bianco mantengono testo scuro: evitare selettori globali come `.eh-surface-rust * { color: white !important; }`.

Il focus deve restare visibile anche sui pulsanti Rust: usare un distacco bianco e un anello Rust o una variante in negativo sul pannello scuro. Blue Aura e lilla contro bianco non devono essere l'unico segnale di focus o l'unico bordo che rende riconoscibile un controllo.

I colori di errore, avviso e successo restano ruoli semantici distinti. Consolidarli in token con abbinamenti di testo verificati; non convertirli tutti in Rust e non usare verde/lilla come sole prove di stato. Affiancare sempre etichetta o icona pertinente.

## 7. Applicazione schermata per schermata

| Schermata | Indicazioni specifiche | Vincolo da preservare |
|---|---|---|
| Login cliente e staff | Rust esatto sul pannello scuro con testo bianco; area form chiara; linea Blue Aura; logo coerente; fallback tipografico dichiarato. | Messaggi di errore leggibili, login, lingua, mostra password, intro e reduced motion. |
| Dashboard cliente | Fascia di contesto Blue Aura con titoli Rust; CTA Rust/bianco; pannello transfer lilla dove pertinente; dati su bianco. | Distinguere inviata, in lavorazione e completata; non rinominare gli stati solo per esigenze grafiche. |
| Compilazione e upload | Riepilogo step Blue Aura/Rust; testo principale scuro; avanzamento compilazione separato dalla lavorazione; Avanti Rust/bianco e Salva bozza secondario. | Tre slot sticky, nessuna azione coperta su mobile; upload, eliminazione, retry e persistenza. |
| Riepilogo e invio | Intestazione Blue Aura/Rust; CTA finale Rust/bianco; linea curva discreta; messaggi semantici riconoscibili. | Consenso, validazione server, collegamenti Modifica e distinzione bozza/invio. |
| Accesso modulo e conferma | Applicare gli stessi token anche a password, modulo pubblicato, bozza salvata e successo. | Non lasciare il corallo precedente dopo la navigazione; conservare traduzioni e ricevuta. |
| Dashboard operatore | Navigazione selezionata Blue Aura/Rust; CTA Rust/bianco; titoli coerenti; card senza gradienti decorativi eterogenei. | Priorità operative, filtri, ruoli e leggibilità dei dati. |
| Elenco clienti | Header sobrio, Nuovo cliente Rust/bianco; filtri attivi Blue Aura/Rust; tabelle bianche con tipografia uniforme. | Ricerca, stato vuoto, modali, reset password e responsive. |
| Builder | Header con logo Rust e linea Blue Aura; pannello proprietà lilla/Rust, aree di lavoro bianche; Pubblica Rust/bianco. | Stato dirty/saved/error, blocco immutabile, duplicazione esplicita, ordinamento e traduzioni. |
| Errori, aiuti e modali | Includere 404, guide, upload guide, modali utente e cliente. Usare colori e spaziature condivisi. | Focus, chiusura da tastiera, nomi accessibili e testo degli errori. |
| Nuove ricevute PDF | Logo Rust, linea Blue Aura, PP Valve se disponibile anche nel formato adatto al generatore; altrimenti fallback esplicito. | Non rigenerare in massa le ricevute storiche e non cambiare nomi, collegamenti o contenuti documentali. |

## 8. Piano esecutivo limitato al branding

1. **Inventario e baseline visiva:** fissare commit e tag, verificare istruzioni locali, individuare asset realmente serviti e acquisire le schermate attuali con dati fittizi. Gli screenshot 3.0.0 sono solo riferimenti storici.
2. **Token e tipografia:** implementare colori/primi piani, alias, font e ordine di caricamento. Creare una pagina campione interna di componenti o una fixture di verifica per vedere i tre fondi esatti, senza introdurre funzioni nel prodotto.
3. **Componenti:** migrare pulsanti, pannelli, badge, form, focus, navigazione, modali, logo e motivo curvo. Ridurre gli override già presenti invece di aggiungerne un altro livello.
4. **Percorso cliente:** login → dashboard → step/upload → riepilogo → conferma/ricevuta. Verificare testo bianco su Rust a ogni passaggio.
5. **Percorso operatore:** dashboard → clienti → builder → pubblicazione/duplicazione. Preservare i comportamenti corretti nella 3.1.0.
6. **Pagine secondarie e nuovi PDF:** password modulo, errori, guide, modali e generatore ricevute, limitando il lavoro al tema.
7. **Consegna:** diff revisionabile, screenshot reali e tabella componente → token → primo piano → evidenza → stato. Se PP Valve non è disponibile, segnare soltanto quel punto come parziale.

### Criteri di accettazione

- I tre HEX confermati appaiono come colori pieni nei componenti previsti; verificarli con gli stili calcolati, non solo con una ricerca nei sorgenti.
- CTA Rust con etichetta e icona bianche in default, hover, active e loading. Nessuna label Rust/scura su Rust e nessun testo bianco su Blue Aura/lilla.
- Nessuna regola `.text-muted`, `.text-dark`, colore del link o stile inline rende illeggibile un contenuto su fondo scuro.
- Gli HEX precedenti di brand (`#E8847D`, `#BA3D30`, `#7F1718`, `#0284C7`) non restano come colori funzionali di brand nei percorsi migrati. Le eccezioni, per esempio asset storici conservati, vanno documentate. Non usare una sostituzione globale su contenuti o allegati.
- Font coerente e peso realmente disponibile; nessun download font inesistente, nessun logotipo ridigitato.
- Verifiche a 1280 e 1440 px desktop, 768 px tablet, 390 e 360 px mobile, zoom 200%, tastiera e reduced motion. Controllare la barra sticky con messaggi di errore e nomi file lunghi.
- Testare stati vuoti, password errata, caricamento, file rifiutato, bozza salvata, pubblicazione e pratica conclusa. Uno screenshot della sola pagina iniziale non copre il percorso.
- Colori di categoria e colori di stato distinguibili; nessuna modifica implicita alle regole operative.
- Nessun errore console o caricamento statico fallito. Screenshot PNG effettivi con commit e viewport nel report; nessun collegamento dipendente da `127.0.0.1` della macchina di sviluppo.
- Eseguire i test di regressione pertinenti dopo le modifiche; non riscrivere test backend per approvare un cambiamento grafico. Segnalare i controlli non eseguiti senza dichiararli superati.

## 9. Prompt completo per Sol in VS Code

```text
Lavora su RazorCopter/eh-moduli, attualmente versione 3.1.0. Leggi
eh-moduli_v3.1.0_specifiche_brand.md e il PDF istituzionale allegato.
Verifica il commit corrente: la specifica è basata su
50232d9289383b383abc1207399cc9ce81d7d6a5.

OBIETTIVO
Applicare l'identità istituzionale Etichub alle schermate esistenti,
rendendo realmente visibili i tre colori ufficiali:
- Intense Rust #6B000F
- Blue Aura #B1D0E1
- Colore 3, lilla #C5BED8
Questi codici prevalgono sui campioni del PDF e sulle palette precedenti.
Non sostituirli con corallo, altri rossi o azzurri simili.
L'utente richiede anche gradienti: applica le tre ricette della sezione 11,
usando Rust con testo bianco per CTA/testate e Blue Aura→lilla con testo
Rust per pannelli chiari. La sfumatura con tutti e tre i colori è solo
decorativa, senza testo. Mantieni visibili anche i colori base esatti.

LEGGIBILITÀ OBBLIGATORIA
Su superfici Rust e scure usa testo e icone bianchi #FFFFFF, inclusi
titoli, sottotitoli, etichette dei pulsanti e stati hover/active/loading.
Su Blue Aura e lilla usa testo Rust #6B000F o scuro: non bianco.
Controlla che classi Bootstrap, text-muted, link e stili inline non
annullino questi abbinamenti. Non applicare una regola globale che
renda bianchi anche i testi dei campi con fondo chiaro.

FEDELTÀ AL PDF
Riprendi logo Rust con linea Blue Aura, motivo continuo a curve
arrotondate, gerarchia tipografica e spaziature delle applicazioni.
Il font istituzionale è PP Valve. Cerca file utilizzabili nel progetto:
se disponibili, configura i pesi reali; se assenti, predisponi il punto
di integrazione e usa Inter provvisoriamente, dichiarando questo limite.
Non ricreare il logo digitandolo e non estrarre font dalle immagini.
I gialli/verdi/azzurri supplementari campionati nel PDF restano riferimenti
secondari non confermati: non espandere la palette principale.

IMPLEMENTAZIONE
Segui gli ID BRAND-01..12 e il piano della specifica. I tre token sono
già nel design-system.css, ma molti utilizzatori li ignorano.
Consolida token e componenti e migra anche le pagine autonome:
login, password modulo, published_form, form_success e builder.
Uniforma i primi piani dei componenti, i pulsanti, il focus, checkbox,
modali, pannelli e stati interattivi. Riduci i vecchi override; non
appendere un foglio pieno di !important sopra quelli esistenti.
Verifica con findstatic quale copia degli asset viene servita.

Distribuisci Blue Aura in testate/pannelli di contesto e selezioni,
il lilla nei pannelli transfer/regolatorio e proprietà del builder,
Rust nelle azioni principali con testo bianco. I pastelli devono
essere visibili come superfici, non soltanto come bordini o variabili.
Non forzare un colore di categoria a significare uno stato operativo.

PRESERVA LA VERSIONE 3.1.0
Mantieni Django, Bootstrap e Alpine e le funzioni attuali. Conserva
salvataggio bozza, traduzioni, barra sticky e i suoi tre slot, upload
singolo/multiplo/cartella/ZIP, retry, ricevute, immutabilità e duplicazione
del builder. Non introdurre refactor backend o nuove funzionalità.
Per logo e intro mantieni geometria, durata, possibilità di saltare e
reduced motion; allinea i colori dei custom element e dello Shadow DOM.
Per il PDF modifica solo l'aspetto delle nuove generazioni, preservando
dati e archivio storico.

VERIFICA
Avvia una copia locale con dati fittizi. Acquisisci screenshot prima/dopo
del commit corrente per tutte le schermate elencate nella specifica.
Controlla desktop, tablet, 390/360 px, zoom 200%, tastiera, errori,
stati vuoti, contenuti lunghi e reduced motion. Misura contrasto e
valori CSS effettivi. In particolare verifica sempre bianco su Rust.
Esegui i test pertinenti. Se mancano browser o servizi, completa ciò che
è possibile e marca le verifiche bloccate come non eseguite.

CONSEGNA
Procedi autonomamente con modifiche locali revisionabili. Non fare
deploy né operazioni sui dati di produzione. Consegna il diff, i file
PNG effettivi, commit, token utilizzati e una matrice BRAND-01..12 con
esito e limiti, distinguendo implementazione e verifica. Non dichiarare
fedele la tipografia finché PP Valve non è stato realmente integrato.
```

## 10. Nota separata sul controllo del repository

L'obiettivo di questo documento è il branding. Durante la rilettura è emerso anche un residuo estraneo al restyling: `app/settings.py:337–352` consente ancora, in produzione senza `REDIS_URL`, il fallback a `LocMemCache` con warning. La precedente richiesta di evitare tale fallback non risulta integralmente attuata nello snapshot. Mantenerlo come task tecnico separato da verificare, senza mescolarlo alla modifica degli stili. Questa osservazione non dimostra che il deploy attuale sia privo di Redis.

Il report di collaudo incluso nel repository è riferito alla promozione 3.0.0; il precedente allegato dell'utente riportava ancora target 2.2.0 e Django 4.2.14. Per la 3.1.0 fare riferimento al codice corrente e produrre nuove evidenze quando si applica il tema. Non trasferire automaticamente certificazioni o screenshot tra versioni.

## 11. Gradienti richiesti dall'utente: ricette e limiti d'uso

Questa sezione integra le richieste successive sulla visibilità dei tre colori e sui testi bianchi sopra i fondi scuri. I gradienti sono una proposta web basata sulla palette confermata, non ricette HEX presenti nel PDF.

### A. Gradiente Rust — CTA e testate scure

```css
background-color: #6b000f;
background-image: linear-gradient(
  125deg,
  #6b000f 0%,
  #6b000f 25%,
  #8c0a1a 60%,
  #4f000b 100%
);
color: #ffffff;
```

L'area iniziale conserva Intense Rust esatto. `#8C0A1A` e `#4F000B` sono varianti derivate per luce e profondità, non sostituti istituzionali. Usare per la CTA primaria, una fascia di testata e il pannello scuro del login. Etichette, icone, titoli e testo di servizio bianchi; non abbassarne arbitrariamente l'opacità.

Contrasto minimo stimato con testo bianco: **9,66:1**, ottenuto campionando 1.001 punti per segmento nell'interpolazione sRGB. Verificare nel browser la resa effettiva; il dato non include overlay, filtri, opacità o altre modalità di interpolazione. Hover e active possono usare Rust più scuro pieno: la transizione non deve rendere scuro il testo.

### B. Gradiente Blue Aura → lilla — superfici chiare

```css
background-color: #b1d0e1;
background-image: linear-gradient(
  120deg,
  #b1d0e1 0%,
  #b1d0e1 20%,
  #c5bed8 100%
);
color: #6b000f;
```

Usare nella fascia introduttiva della dashboard, in un pannello di contesto o come testata del builder. Non ripetere il gradiente in ogni riga delle tabelle. Per categorie transfer/regolatorio, mantenere anche pannelli lilla pieni: il gradiente è decorativo e non deve rendere ambiguo il colore di categoria.

Contrasto minimo stimato con testo Rust: **7,19:1**, con lo stesso metodo. **Non usare testo bianco su questo gradiente.** Una CTA Rust/bianco può essere contenuta nel pannello e resta leggibile perché ha il proprio fondo scuro opaco.

### C. Firma a tre colori — solo decorazione

```css
background: linear-gradient(
  90deg,
  #6b000f 0%,
  #b1d0e1 52%,
  #c5bed8 100%
);
```

Usare come linea di firma sottile, bordo o motivo curvo dell'intestato. Non sovrapporre testo: il passaggio da scuro a chiaro non consente di assumere lo stesso primo piano lungo tutta la superficie. Non usarlo come progress bar, perché i tre colori potrebbero suggerire stati o soglie inesistenti.

### Regole comuni

- Fondi opachi e contrasto controllato; niente effetto vetro dietro testo operativo.
- Nessuna animazione continua del gradiente, scintillio o alone vistoso. Mantenere il movimento limitato ai feedback utili.
- Non sostituire ogni superficie bianca con un gradiente: riservarlo a poche aree di gerarchia chiara.
- La coppia superficie/primo piano deve essere esplicita in ogni componente. Evitare un `color` globale che annulli il bianco delle CTA.
- I gradienti non risolvono da soli font, asset, spaziature e frammentazione del CSS: applicarli nel sistema condiviso descritto sopra.

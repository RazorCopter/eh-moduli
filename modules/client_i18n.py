"""
Client Personal Area Internationalization (i18n)
Supports Italian (it), English (en), French (fr), German (de).
Provides translation dictionaries, language resolution, and context injection.
"""

SUPPORTED_LANGUAGES = [
    {'code': 'it', 'name': 'Italiano', 'flag': '🇮🇹', 'short': 'IT'},
    {'code': 'en', 'name': 'English', 'flag': '🇬🇧', 'short': 'EN'},
    {'code': 'fr', 'name': 'Français', 'flag': '🇫🇷', 'short': 'FR'},
    {'code': 'de', 'name': 'Deutsch', 'flag': '🇩🇪', 'short': 'DE'},
]

SUPPORTED_LANGUAGE_CODES = {item['code'] for item in SUPPORTED_LANGUAGES}

TRANSLATIONS = {
    'it': {
        'code': 'it',
        'lang_name': 'Italiano',
        'dir': 'ltr',
        
        # Navbar & Layout
        'portal_title': 'Area Personale',
        'logout': 'Esci',
        'language': 'Lingua',
        'footer_text': 'Etichub S.r.l. · Spin-off Università di Pavia · Laboratorio di test e regolatorio cosmetico',
        
        # Login Page
        'login_page_title': 'Accedi — Area Personale Etichub',
        'welcome_back': 'Bentornato',
        'login_subtitle': 'Accedi con le credenziali fornite da Etichub per visualizzare i tuoi prodotti e caricare la documentazione.',
        'client_code': 'Codice Cliente',
        'client_code_placeholder': 'Es. CLI-001',
        'password': 'Password',
        'password_placeholder': 'Inserisci la password',
        'show_password': 'Mostra password',
        'hide_password': 'Nascondi password',
        'login_submit': 'Accedi',
        'need_help': 'Hai bisogno di assistenza?',
        'contact_us': 'Contattaci',
        
        # Login Error Messages
        'error_missing_fields': 'Inserisci il codice cliente e la password.',
        'error_account_inactive': 'Il tuo account è stato disattivato. Contatta Etichub per assistenza.',
        'error_not_configured': 'L\'accesso all\'area personale non è ancora configurato. Contatta Etichub.',
        'error_invalid_credentials': 'Password errata. Riprova.',
        'error_customer_not_found': 'Codice cliente non trovato.',
        'error_forbidden_product': 'Non hai accesso a questo prodotto.',
        
        # Dashboard
        'dashboard_page_title': 'I Miei Prodotti — Area Personale Etichub',
        'hello_user': 'Ciao, {name}',
        'dashboard_subtitle': 'Ecco i prodotti attualmente in lavorazione con Etichub. Seleziona un prodotto per gestire la documentazione.',
        'stat_total_products': 'Prodotti totali',
        'stat_in_progress': 'In lavorazione',
        'stat_completed': 'Completati',
        'section_your_products': 'I Tuoi Prodotti',
        
        # Status Badges
        'status_draft': 'Pratica aperta',
        'status_in_progress': 'Documentazione parziale',
        'status_submitted': 'Upload documentale completato',
        'status_in_processing': 'Lavorazione Etichub in corso',
        'status_completed': 'Lavorazione completata',
        'status_expired': 'Scaduto',
        'status_cancelled': 'Annullato',
        
        # Compact Badges
        'badge_draft': 'Aperta',
        'badge_in_progress': 'In corso',
        'badge_submitted': 'Doc. Inviati',
        'badge_in_processing': 'In lavorazione',
        'badge_completed': 'Lavorata',
        'badge_expired': 'Scaduta',
        'badge_cancelled': 'Annullata',
        
        # Macro Steps & Product Card
        'macro_step_1_title': 'Fase 1: Acquisizione Documenti',
        'macro_step_2_title': 'Fase 2: Lavorazione Etichub',
        'macro_step_1_short': '1. Documenti',
        'macro_step_2_short': '2. Lavorazione',
        'ttl_deadline': 'Termine upload (TTL)',
        'documents_progress': 'Documenti',
        'assigned_on': 'Assegnato il',
        'expires_on': 'Scade il',
        'btn_upload_docs': 'Carica Documenti',
        'btn_docs_submitted': 'Documentazione Inviata',
        'btn_view_docs': 'Visualizza Documenti Trasmessi',
        'btn_expired': 'Scaduto — Contatta Etichub',
        
        # Notifications & Status Details
        'notification_etichub_submitted': 'Upload documentale completato. L\'Ufficio Regolatorio di Etichub è stato notificato e avvierà a breve la lavorazione.',
        'notification_etichub_in_processing': 'Lavorazione Etichub in corso. La documentazione tecnica (PIF) è attualmente in lavorazione presso l\'Ufficio Regolatorio.',
        'notification_etichub_completed': 'Lavorazione completata con successo. La documentazione certificante (PIF) è stata predisposta e validata.',
        
        # Alert Modal & Awareness Declaration (Riepilogo e Invio)
        'alert_confirm_submission_title': 'Conferma Invio Finale',
        'alert_confirm_submission_body': 'Confermi di aver caricato tutta la documentazione in tuo possesso? L\'invio notificherà l\'Ufficio Regolatorio di Etichub per l\'avvio della lavorazione. Non sarà più possibile modificare i documenti caricati.',
        'alert_confirm_btn_cancel': 'Annulla e Ricontrolla',
        'alert_confirm_btn_submit': 'Sì, Confermo e Invia',
        'awareness_declaration_title': 'Dichiarazione di Consapevolezza Documentale',
        'awareness_declaration_text': 'Dichiaro formalmente di aver trasmesso tutti i documenti e le informazioni in mio possesso necessari per la lavorazione del prodotto da parte dell\'ufficio regolatorio Etichub. Sono consapevole che la conferma attesterà il completamento dell\'acquisizione documentale e notificherà il team tecnico per l\'avvio della lavorazione.',
        'awareness_declaration_alert_js': 'Attenzione: è necessario spuntare la dichiarazione formale di consapevolezza prima di procedere con l\'invio.',
        
        # Summary View
        'summary_page_title': 'Riepilogo e Invio',
        'summary_badge': 'Riepilogo Finale',
        'summary_title': 'Verifica e Conferma Invio',
        'summary_case': 'Pratica:',
        'summary_docs_uploaded': 'Documenti Caricati',
        'summary_absence_formalized': 'Assenza Formalizzata',
        'summary_absence_attachment': 'Allegato su carta intestata:',
        'summary_declaration_acquired': 'Dichiarazione Acquisita',
        'summary_ready': 'Pronto',
        'summary_no_files': 'Nessun file caricato per questa pratica.',
        'summary_security_notice': 'Confermando l\'invio, la documentazione verrà archiviata in sicurezza sul server aziendale. Verrà generata una ricevuta formale di avvenuta consegna.',
        'btn_back': 'Indietro',
        'btn_confirm_submit_50': 'Invia Documenti',
        'btn_confirm_submit': 'Invia Documenti',
        'btn_send_docs': 'Invia Documenti',
        'btn_partial_submit': 'Salva Bozza / Invio Parziale',
        'partial_save_modal_title': 'Salva Bozza e Concludi Sessione',
        'partial_save_modal_body': 'I file e i dati caricati finora rimarranno salvati in sicurezza. La pratica rimarrà in corso (Documentazione Parziale) e potrai rientrare nell\'area riservata in qualsiasi momento per caricare i documenti mancanti entro la data di scadenza.',
        'partial_save_btn_confirm': 'Conferma Salva Bozza',
        'submitting_spinner': 'Invio in corso...',
        
        # Success View
        'success_page_title': 'Modulo Inviato — Etichub',
        'success_title': 'Modulo Inviato!',
        'partial_success_page_title': 'Bozza Salvata — Etichub',
        'partial_success_title': 'Bozza Salvata con Successo!',
        'partial_success_msg': 'I file e le informazioni caricate finora sono stati salvati. La pratica rimane aperta: potrai riaccedere alla tua area riservata in qualsiasi momento prima della scadenza per completare il caricamento dei documenti mancanti.',
        'partial_status_val': '⏳ Documentazione Parziale (In corso)',
        'btn_back_to_portal': 'Torna ai Tuoi Prodotti (Area Personale)',
        'success_msg_50': 'Grazie per aver inviato i documenti. L\'Ufficio Regolatorio di Etichub è stato notificato per l\'avvio della lavorazione tecnica.',
        'success_msg': 'Grazie per aver inviato i documenti. L\'Ufficio Regolatorio di Etichub è stato notificato per l\'avvio della lavorazione tecnica.',
        'detail_status': 'Stato',
        'detail_status_val': '✓ Documentazione Acquisita',
        'detail_datetime': 'Data e ora',
        'detail_customer': 'Cliente',
        'detail_project': 'Progetto / Prodotto',
        'success_receipt_hint': 'Puoi scaricare la ricevuta ufficiale o tornare alla tua area personale in sicurezza.',
        'btn_download_receipt': 'Scarica Ricevuta Ufficiale (PDF)',
        'btn_home': 'Torna alla Home',
        
        # Already Submitted View
        'already_submitted_title': 'Modulo Già Trasmesso',
        'already_submitted_subtitle': 'La documentazione per questo prodotto è già stata confermata e inviata all\'Ufficio Regolatorio.',
        'already_submitted_locked_msg': 'Non è più possibile modificare i documenti caricati in quanto la lavorazione è stata avviata.',

        # Empty State
        'empty_title': 'Nessun prodotto assegnato',
        'empty_desc': 'Al momento non ci sono prodotti in lavorazione. Verrai notificato quando Etichub ti assegnerà un nuovo progetto.',
        
        # Success page & cross-links
        'back_to_portal': 'Torna ai Tuoi Prodotti (Area Personale)',
        
        # Timeline / History Modal
        'timeline_modal_title': 'Storico e Avanzamento Pratica',
        'timeline_click_hint': 'Clicca per vedere lo storico',
        'timeline_step_assigned': 'Pratica Creata e Assegnata',
        'timeline_step_assigned_desc': 'Il modulo è stato predisposto e reso disponibile per il caricamento dei documenti.',
        'timeline_step_submitted': 'Invio Documentale Concluso',
        'timeline_step_submitted_desc': 'Tutti i documenti richiesti sono stati trasmessi con dichiarazione di consapevolezza.',
        'timeline_step_processing': 'Presa in Carico Ufficio Regolatorio',
        'timeline_step_processing_desc': 'I tecnici Etichub hanno avviato la revisione documentale e la lavorazione tecnica del fascicolo (PIF).',
        'timeline_step_completed': 'Lavorazione Regolatoria Completata',
        'timeline_step_completed_desc': 'Verifica e fascicolo tecnico evasi con successo. Ciclo completato.',
        'timeline_step_pending': 'In attesa delle fasi precedenti',
        'timeline_close': 'Chiudi',
        'timeline_btn_history': 'Storico Avanzamento',

        # Onboarding & Upload Guide Modal
        'guide_fab_label': 'Guida Upload',
        'guide_modal_title': 'Guida al Caricamento Documentale',
        'guide_modal_subtitle': 'Istruzioni chiare e semplici per completare la raccolta documenti in pochi minuti.',
        'guide_step1_badge': '1. Prepara i Documenti',
        'guide_step1_title': 'Formati ammessi e limiti',
        'guide_step1_desc': 'Puoi caricare file in formato <strong>PDF, Word (.doc, .docx)</strong> o immagini <strong>JPG / PNG</strong>. Il limite massimo per singolo file è di <strong>10 MB</strong>. Assicurati che i documenti siano leggibili e completi di tutte le pagine.',
        'guide_step2_badge': '2. Come Caricare i File',
        'guide_step2_title': 'Trascina o seleziona con un click',
        'guide_step2_desc': 'Per ciascun documento richiesto, trascina il file direttamente nel riquadro tratteggiato oppure clicca su <strong>"Clicca qui o trascina"</strong> per sceglierlo dal tuo dispositivo. Il caricamento è istantaneo: apparirà una spunta verde di conferma.',
        'guide_step3_badge': '3. Documenti Obbligatori',
        'guide_step3_title': 'Avanzamento tra i passaggi',
        'guide_step3_desc': 'I documenti con il contrassegno rosso <strong>"Obbligatorio"</strong> sono vincolanti: il pulsante <strong>"Avanti"</strong> si attiva solo dopo aver caricato o giustificato tutti i documenti obbligatori della pagina corrente.',
        'guide_step4_badge': '4. Documento Non Disponibile?',
        'guide_step4_title': 'Carica la Dichiarazione Formale',
        'guide_step4_desc': 'Se un documento obbligatorio non è al momento reperibile, clicca su <strong>"Carica dichiarazione formale"</strong>: allega una dichiarazione su <strong>carta intestata aziendale timbrata e firmata</strong> e spunta la relativa casella. Questo sbloccherà il passaggio successivo.',
        'guide_step5_badge': '5. Conclusione della Sessione',
        'guide_step5_title': 'Invia Documenti vs Salva Bozza',
        'guide_step5_desc': 'Nella schermata di riepilogo finale puoi scegliere:<br>• <strong>Invia Documenti</strong>: se hai caricato tutta la documentazione completa, spunta l\'attestazione e invia per la lavorazione regolatoria.<br>• <strong>Salva Bozza / Invio Parziale</strong>: se hai caricato solo una parte dei file, clicca su questo tasto (sempre attivo) per salvare i progressi e riprendere in seguito prima della data di scadenza.',
        'guide_help_box_title': 'Serve ulteriore assistenza?',
        'guide_help_box_desc': 'I nostri esperti dell\'Ufficio Regolatorio sono sempre a disposizione. Puoi riaprire questa guida in qualunque momento cliccando sul pulsante fluttuante con l\'icona <strong>?</strong> presente in basso a destra.',
        'guide_dont_show_again': 'Ho preso visione delle istruzioni (non mostrare più automaticamente all\'accesso)',
        'guide_btn_start': 'Ho capito, Inizia!',
        'guide_btn_close': 'Chiudi Guida',
    },

    'en': {
        'code': 'en',
        'lang_name': 'English',
        'dir': 'ltr',
        
        # Navbar & Layout
        'portal_title': 'Client Portal',
        'logout': 'Log out',
        'language': 'Language',
        'footer_text': 'Etichub S.r.l. · Spin-off University of Pavia · Cosmetic Testing & Regulatory Laboratory',
        
        # Login Page
        'login_page_title': 'Log In — Etichub Client Portal',
        'welcome_back': 'Welcome Back',
        'login_subtitle': 'Log in with the credentials provided by Etichub to view your products and upload documentation.',
        'client_code': 'Client Code',
        'client_code_placeholder': 'e.g. CLI-001',
        'password': 'Password',
        'password_placeholder': 'Enter your password',
        'show_password': 'Show password',
        'hide_password': 'Hide password',
        'login_submit': 'Log In',
        'need_help': 'Need assistance?',
        'contact_us': 'Contact us',
        
        # Login Error Messages
        'error_missing_fields': 'Please enter your client code and password.',
        'error_account_inactive': 'Your account has been deactivated. Please contact Etichub for assistance.',
        'error_not_configured': 'Client portal access has not been configured yet. Please contact Etichub.',
        'error_invalid_credentials': 'Incorrect password. Please try again.',
        'error_customer_not_found': 'Client code not found.',
        'error_forbidden_product': 'You do not have access to this product.',
        
        # Dashboard
        'dashboard_page_title': 'My Products — Etichub Client Portal',
        'hello_user': 'Hello, {name}',
        'dashboard_subtitle': 'Here are your products currently being processed with Etichub. Select a product to manage documentation.',
        'stat_total_products': 'Total Products',
        'stat_in_progress': 'In Progress',
        'stat_completed': 'Completed',
        'section_your_products': 'Your Products',
        
        # Status Badges
        'status_draft': 'Application Open',
        'status_in_progress': 'Partial Documentation',
        'status_submitted': 'Document Upload Completed',
        'status_in_processing': 'Etichub Processing in Progress',
        'status_completed': 'Processing Completed',
        'status_expired': 'Expired',
        'status_cancelled': 'Cancelled',
        
        # Compact Badges
        'badge_draft': 'Open',
        'badge_in_progress': 'In Progress',
        'badge_submitted': 'Docs Submitted',
        'badge_in_processing': 'In Processing',
        'badge_completed': 'Completed',
        'badge_expired': 'Expired',
        'badge_cancelled': 'Cancelled',
        
        # Macro Steps & Product Card
        'macro_step_1_title': 'Phase 1: Document Acquisition',
        'macro_step_2_title': 'Phase 2: Etichub Processing',
        'macro_step_1_short': '1. Documents',
        'macro_step_2_short': '2. Processing',
        'ttl_deadline': 'Upload Deadline (TTL)',
        'documents_progress': 'Documents',
        'assigned_on': 'Assigned on',
        'expires_on': 'Expires on',
        'btn_upload_docs': 'Upload Documents',
        'btn_docs_submitted': 'Documentation Submitted',
        'btn_view_docs': 'View Submitted Documents',
        'btn_expired': 'Expired — Contact Etichub',
        
        # Notifications & Status Details
        'notification_etichub_submitted': 'Document upload completed. The Etichub Regulatory Office has been notified and will start technical processing shortly.',
        'notification_etichub_in_processing': 'Etichub processing in progress. Technical documentation (PIF) is currently being processed by the Regulatory Office.',
        'notification_etichub_completed': 'Processing successfully completed. Certification documentation (PIF) has been prepared and validated.',
        
        # Alert Modal & Awareness Declaration (Summary and Submit)
        'alert_confirm_submission_title': 'Final Submission Confirmation',
        'alert_confirm_submission_body': 'Do you confirm that you have uploaded all documentation in your possession? Submitting will notify the Etichub Regulatory Office to start processing. It will no longer be possible to modify uploaded documents.',
        'alert_confirm_btn_cancel': 'Cancel and Review',
        'alert_confirm_btn_submit': 'Yes, Confirm and Submit',
        'awareness_declaration_title': 'Documentary Awareness Declaration',
        'awareness_declaration_text': 'I formally declare that I have submitted all documents and information in my possession necessary for product processing by the Etichub regulatory office. I understand that confirmation will attest to the completion of document acquisition and will notify the technical team to start processing.',
        'awareness_declaration_alert_js': 'Attention: you must check the formal awareness declaration before proceeding with submission.',
        
        # Summary View
        'summary_page_title': 'Summary and Submission',
        'summary_badge': 'Final Summary',
        'summary_title': 'Verify and Confirm Submission',
        'summary_case': 'Case:',
        'summary_docs_uploaded': 'Uploaded Documents',
        'summary_absence_formalized': 'Formalized Absence',
        'summary_absence_attachment': 'Letterhead attachment:',
        'summary_declaration_acquired': 'Declaration Acquired',
        'summary_ready': 'Ready',
        'summary_no_files': 'No files uploaded for this case.',
        'summary_security_notice': 'By confirming submission, documentation will be securely stored on company servers. An official receipt will be generated.',
        'btn_back': 'Back',
        'btn_confirm_submit_50': 'Submit Documents',
        'btn_confirm_submit': 'Submit Documents',
        'btn_send_docs': 'Submit Documents',
        'btn_partial_submit': 'Save Draft / Partial Submission',
        'partial_save_modal_title': 'Save Draft and End Session',
        'partial_save_modal_body': 'Files and data uploaded so far will be kept safely. The case will remain in progress (Partial Documentation) and you can return to your portal at any time to upload remaining documents before the deadline.',
        'partial_save_btn_confirm': 'Confirm Save Draft',
        'submitting_spinner': 'Submitting...',
        
        # Success View
        'success_page_title': 'Form Submitted — Etichub',
        'success_title': 'Form Submitted!',
        'partial_success_page_title': 'Draft Saved — Etichub',
        'partial_success_title': 'Draft Saved Successfully!',
        'partial_success_msg': 'Files and information uploaded so far have been saved. The case remains open: you can return to your personal portal at any time before the deadline to complete uploading missing documents.',
        'partial_status_val': '⏳ Partial Documentation (In progress)',
        'btn_back_to_portal': 'Back to Your Products (Client Portal)',
        'success_msg_50': 'Thank you for submitting the documents. The Etichub Regulatory Office has been notified to begin technical processing.',
        'success_msg': 'Thank you for submitting the documents. The Etichub Regulatory Office has been notified to begin technical processing.',
        'detail_status': 'Status',
        'detail_status_val': '✓ Documentation Acquired',
        'detail_datetime': 'Date and time',
        'detail_customer': 'Client',
        'detail_project': 'Project / Product',
        'success_receipt_hint': 'You can download the official receipt or safely return to your client portal.',
        'btn_download_receipt': 'Download Official Receipt (PDF)',
        'btn_home': 'Back to Home',
        
        # Already Submitted View
        'already_submitted_title': 'Form Already Submitted',
        'already_submitted_subtitle': 'Documentation for this product has already been confirmed and sent to the Regulatory Office.',
        'already_submitted_locked_msg': 'It is no longer possible to modify uploaded documents as processing has begun.',

        # Empty State
        'empty_title': 'No products assigned',
        'empty_desc': 'There are currently no products in progress. You will be notified when Etichub assigns a new project to your account.',
        
        # Success page & cross-links
        'back_to_portal': 'Back to Your Products (Client Portal)',
        
        # Timeline / History Modal
        'timeline_modal_title': 'Case History & Progression',
        'timeline_click_hint': 'Click to view case history',
        'timeline_step_assigned': 'Case Created & Assigned',
        'timeline_step_assigned_desc': 'The form has been prepared and opened for document upload.',
        'timeline_step_submitted': 'Document Submission Completed',
        'timeline_step_submitted_desc': 'All required documents have been submitted with awareness declaration.',
        'timeline_step_processing': 'Taken in Charge by Regulatory Office',
        'timeline_step_processing_desc': 'Etichub specialists have initiated regulatory review and PIF technical dossier preparation.',
        'timeline_step_completed': 'Regulatory Processing Completed',
        'timeline_step_completed_desc': 'Technical dossier verified and successfully validated. Process complete.',
        'timeline_step_pending': 'Pending previous phases',
        'timeline_close': 'Close',
        'timeline_btn_history': 'Progress History',

        # Onboarding & Upload Guide Modal
        'guide_fab_label': 'Upload Guide',
        'guide_modal_title': 'Document Upload Guide',
        'guide_modal_subtitle': 'Clear and simple instructions to complete your document submission in minutes.',
        'guide_step1_badge': '1. Prepare Documents',
        'guide_step1_title': 'Accepted formats & size limits',
        'guide_step1_desc': 'You can upload <strong>PDF, Word (.doc, .docx)</strong> or <strong>JPG / PNG</strong> images. Maximum file size is <strong>10 MB</strong> per file. Ensure all documents are clear, legible, and include all pages.',
        'guide_step2_badge': '2. How to Upload',
        'guide_step2_title': 'Drag & drop or click to choose',
        'guide_step2_desc': 'For each required document, drag and drop the file directly into the dashed box or click <strong>"Click here or drag"</strong> to browse your device. Upload is instant: a green checkmark confirms safe saving.',
        'guide_step3_badge': '3. Mandatory Documents',
        'guide_step3_title': 'Step progress & requirements',
        'guide_step3_desc': 'Documents marked with the red <strong>"Mandatory"</strong> badge must be provided: the <strong>"Next"</strong> button only unlocks once all mandatory documents on the current step are uploaded or justified.',
        'guide_step4_badge': '4. Missing Document?',
        'guide_step4_title': 'Upload a Formal Declaration',
        'guide_step4_desc': 'If a mandatory document is temporarily unavailable, click <strong>"Upload formal declaration"</strong>: attach a statement on <strong>stamped and signed company letterhead</strong> and check the attestation. This unlocks the next step.',
        'guide_step5_badge': '5. Completing Your Session',
        'guide_step5_title': 'Submit Documents vs Save Draft',
        'guide_step5_desc': 'On the final summary page, choose:<br>• <strong>Submit Documents</strong>: once all required documents are uploaded, check awareness and submit for Etichub regulatory processing.<br>• <strong>Save Draft / Partial Submit</strong>: if you only have some files ready, click this button (always active) to save your progress and return anytime before the deadline.',
        'guide_help_box_title': 'Need additional help?',
        'guide_help_box_desc': 'Our regulatory team is always here to assist you. You can reopen this guide at any time by clicking the floating <strong>?</strong> button in the bottom-right corner.',
        'guide_dont_show_again': 'I have read and understood the instructions (do not show automatically on login)',
        'guide_btn_start': 'Got it, Let\'s Start!',
        'guide_btn_close': 'Close Guide',
    },

    'fr': {
        'code': 'fr',
        'lang_name': 'Français',
        'dir': 'ltr',
        
        # Navbar & Layout
        'portal_title': 'Espace Client',
        'logout': 'Déconnexion',
        'language': 'Langue',
        'footer_text': 'Etichub S.r.l. · Spin-off Université de Pavie · Laboratoire de tests et réglementaire cosmétique',
        
        # Login Page
        'login_page_title': 'Connexion — Espace Client Etichub',
        'welcome_back': 'Bienvenue',
        'login_subtitle': 'Connectez-vous avec les identifiants fournis par Etichub pour consulter vos produits et déposer vos documents.',
        'client_code': 'Code Client',
        'client_code_placeholder': 'ex. CLI-001',
        'password': 'Mot de passe',
        'password_placeholder': 'Entrez votre mot de passe',
        'show_password': 'Afficher le mot de passe',
        'hide_password': 'Masquer le mot de passe',
        'login_submit': 'Se connecter',
        'need_help': 'Besoin d\'aide ?',
        'contact_us': 'Contactez-nous',
        
        # Login Error Messages
        'error_missing_fields': 'Veuillez saisir votre code client et votre mot de passe.',
        'error_account_inactive': 'Votre compte a été désactivé. Veuillez contacter Etichub pour assistance.',
        'error_not_configured': 'L\'accès à l\'espace client n\'est pas encore configuré. Veuillez contacter Etichub.',
        'error_invalid_credentials': 'Mot de passe incorrect. Veuillez réessayer.',
        'error_customer_not_found': 'Code client introuvable.',
        'error_forbidden_product': 'Vous n\'avez pas accès à ce produit.',
        
        # Dashboard
        'dashboard_page_title': 'Mes Produits — Espace Client Etichub',
        'hello_user': 'Bonjour, {name}',
        'dashboard_subtitle': 'Voici les produits actuellement traités avec Etichub. Sélectionnez un produit pour gérer les documents requis.',
        'stat_total_products': 'Total des produits',
        'stat_in_progress': 'En cours',
        'stat_completed': 'Terminés',
        'section_your_products': 'Vos Produits',
        
        # Status Badges
        'status_draft': 'Dossier ouvert',
        'status_in_progress': 'Documentation partielle',
        'status_submitted': 'Dépôt documentaire terminé',
        'status_in_processing': 'Traitement Etichub en cours',
        'status_completed': 'Traitement terminé',
        'status_expired': 'Expiré',
        'status_cancelled': 'Annulé',
        
        # Compact Badges
        'badge_draft': 'Ouvert',
        'badge_in_progress': 'En cours',
        'badge_submitted': 'Docs Transmis',
        'badge_in_processing': 'En traitement',
        'badge_completed': 'Terminé',
        'badge_expired': 'Expiré',
        'badge_cancelled': 'Annulé',
        
        # Macro Steps & Product Card
        'macro_step_1_title': 'Phase 1 : Collecte documentaire',
        'macro_step_2_title': 'Phase 2 : Traitement Etichub',
        'macro_step_1_short': '1. Documents',
        'macro_step_2_short': '2. Traitement',
        'ttl_deadline': 'Délai de dépôt (TTL)',
        'documents_progress': 'Documents',
        'assigned_on': 'Assigné le',
        'expires_on': 'Expire le',
        'btn_upload_docs': 'Déposer des documents',
        'btn_docs_submitted': 'Documents transmis',
        'btn_view_docs': 'Voir les documents transmis',
        'btn_expired': 'Expiré — Contactez Etichub',
        
        # Notifications & Status Details
        'notification_etichub_submitted': 'Dépôt documentaire terminé. Le service réglementaire d\'Etichub a été notifié et débutera prochainement le traitement.',
        'notification_etichub_in_processing': 'Traitement Etichub en cours. Le dossier technique (DIP) est actuellement en cours d\'élaboration par le service réglementaire.',
        'notification_etichub_completed': 'Traitement terminé avec succès. Le dossier de certification (DIP) a été finalisé et validé.',
        
        # Alert Modal & Awareness Declaration (Récapitulatif et envoi)
        'alert_confirm_submission_title': 'Confirmation d\'envoi final',
        'alert_confirm_submission_body': 'Confirmez-vous avoir téléchargé tous les documents en votre possession ? L\'envoi notifiera le service réglementaire d\'Etichub pour démarrer le traitement. Il ne sera plus possible de modifier les documents téléchargés.',
        'alert_confirm_btn_cancel': 'Annuler et revérifier',
        'alert_confirm_btn_submit': 'Oui, confirmer et envoyer',
        'awareness_declaration_title': 'Déclaration de conformité documentaire',
        'awareness_declaration_text': 'Je déclare formellement avoir transmis tous les documents et informations en ma possession nécessaires au traitement du produit par le bureau réglementaire d\'Etichub. J\'ai conscience que cette validation atteste de la réalisation de la collecte documentaire et notifiera l\'équipe technique pour le démarrage du traitement.',
        'awareness_declaration_alert_js': 'Attention : vous devez cocher la déclaration formelle de conformité avant de procéder à l\'envoi.',
        
        # Summary View
        'summary_page_title': 'Récapitulatif et envoi',
        'summary_badge': 'Récapitulatif final',
        'summary_title': 'Vérifier et confirmer l\'envoi',
        'summary_case': 'Dossier :',
        'summary_docs_uploaded': 'Documents déposés',
        'summary_absence_formalized': 'Absence formalisée',
        'summary_absence_attachment': 'Pièce jointe sur papier à en-tête :',
        'summary_declaration_acquired': 'Déclaration enregistrée',
        'summary_ready': 'Prêt',
        'summary_no_files': 'Aucun fichier déposé pour ce dossier.',
        'summary_security_notice': 'En confirmant l\'envoi, les documents seront archivés en toute sécurité sur les serveurs de l\'entreprise. Un reçu officiel sera généré.',
        'btn_back': 'Retour',
        'btn_confirm_submit_50': 'Envoyer les documents',
        'btn_confirm_submit': 'Envoyer les documents',
        'btn_send_docs': 'Envoyer les documents',
        'btn_partial_submit': 'Enregistrer le brouillon / Envoi partiel',
        'partial_save_modal_title': 'Enregistrer le brouillon et terminer la session',
        'partial_save_modal_body': 'Les fichiers et données déposés jusqu\'ici seront conservés en toute sécurité. Le dossier restera en cours (Documentation partielle) et vous pourrez vous reconnecter à tout moment pour compléter les documents manquants.',
        'partial_save_btn_confirm': 'Confirmer l\'enregistrement du brouillon',
        'submitting_spinner': 'Envoi en cours...',
        
        # Success View
        'success_page_title': 'Formulaire envoyé — Etichub',
        'success_title': 'Formulaire envoyé !',
        'partial_success_page_title': 'Brouillon enregistré — Etichub',
        'partial_success_title': 'Brouillon enregistré avec succès !',
        'partial_success_msg': 'Les fichiers et informations transmis jusqu\'ici ont été sauvegardés. Le dossier reste ouvert : vous pouvez revenir à votre espace réservé à tout moment avant l\'échéance pour compléter les pièces manquantes.',
        'partial_status_val': '⏳ Documentation partielle (En cours)',
        'btn_back_to_portal': 'Retour à vos produits (Espace client)',
        'success_msg_50': 'Merci d\'avoir transmis vos documents. Le service réglementaire d\'Etichub a été notifié pour débuter le traitement technique.',
        'success_msg': 'Merci d\'avoir transmis vos documents. Le service réglementaire d\'Etichub a été notifié pour débuter le traitement technique.',
        'detail_status': 'Statut',
        'detail_status_val': '✓ Documents collectés',
        'detail_datetime': 'Date et heure',
        'detail_customer': 'Client',
        'detail_project': 'Projet / Produit',
        'success_receipt_hint': 'Vous pouvez télécharger le reçu officiel ou retourner à votre espace client en toute sécurité.',
        'btn_download_receipt': 'Télécharger le reçu officiel (PDF)',
        'btn_home': 'Retour à l\'accueil',
        
        # Already Submitted View
        'already_submitted_title': 'Formulaire déjà transmis',
        'already_submitted_subtitle': 'La documentation pour ce produit a déjà été confirmée et envoyée au service réglementaire.',
        'already_submitted_locked_msg': 'Il n\'est plus possible de modifier les documents déposés car le traitement a commencé.',

        # Empty State
        'empty_title': 'Aucun produit assigné',
        'empty_desc': 'Il n\'y a actuellement aucun produit en cours de traitement. Vous serez notifié dès qu\'Etichub vous assignera un nouveau projet.',
        
        # Success page & cross-links
        'back_to_portal': 'Retour à Vos Produits (Espace Client)',
        
        # Timeline / History Modal
        'timeline_modal_title': 'Historique et progression du dossier',
        'timeline_click_hint': 'Cliquez pour voir l\'historique',
        'timeline_step_assigned': 'Dossier créé et assigné',
        'timeline_step_assigned_desc': 'Le formulaire a été préparé et ouvert pour le dépôt des documents.',
        'timeline_step_submitted': 'Collecte documentaire terminée',
        'timeline_step_submitted_desc': 'Tous les documents requis ont été transmis avec déclaration formelle.',
        'timeline_step_processing': 'Prise en charge par le service réglementaire',
        'timeline_step_processing_desc': 'Les experts Etichub ont démarré l\'instruction technique et l\'élaboration du DIP.',
        'timeline_step_completed': 'Traitement réglementaire terminé',
        'timeline_step_completed_desc': 'Dossier validé et finalisé avec succès. Cycle terminé.',
        'timeline_step_pending': 'En attente des étapes précédentes',
        'timeline_close': 'Fermer',
        'timeline_btn_history': 'Historique du dossier',

        # Onboarding & Upload Guide Modal
        'guide_fab_label': 'Guide Dépôt',
        'guide_modal_title': 'Guide de Téléversement des Documents',
        'guide_modal_subtitle': 'Instructions simples et claires pour transmettre vos documents en quelques minutes.',
        'guide_step1_badge': '1. Préparer les Documents',
        'guide_step1_title': 'Formats acceptés et taille maximale',
        'guide_step1_desc': 'Vous pouvez déposer des fichiers <strong>PDF, Word (.doc, .docx)</strong> ou des images <strong>JPG / PNG</strong>. La taille maximale est de <strong>10 Mo</strong> par fichier. Veillez à ce que les documents soient lisibles et complets.',
        'guide_step2_badge': '2. Comment Téléverser',
        'guide_step2_title': 'Glisser-déposer ou cliquer pour choisir',
        'guide_step2_desc': 'Pour chaque document requis, glissez le fichier dans la zone en pointillés ou cliquez sur <strong>"Cliquer ou glisser"</strong>. Le dépôt est immédiat : une coche verte confirme l\'enregistrement en toute sécurité.',
        'guide_step3_badge': '3. Documents Obligatoires',
        'guide_step3_title': 'Progression et validation obligatoire',
        'guide_step3_desc': 'Les documents signalés par le badge rouge <strong>"Obligatoire"</strong> sont indispensables : le bouton <strong>"Suivant"</strong> ne s\'active que lorsque tous les documents obligatoires de l\'étape sont déposés ou justifiés.',
        'guide_step4_badge': '4. Document Non Disponible ?',
        'guide_step4_title': 'Déposer une Déclaration Formelle',
        'guide_step4_desc': 'Si un document obligatoire n\'est pas encore disponible, cliquez sur <strong>"Déposer une déclaration formelle"</strong> : joignez une attestation sur <strong>papier à en-tête tamponné et signé</strong> et cochez l\'engagement. Cela débloquera l\'étape suivante.',
        'guide_step5_badge': '5. Clôture de Session',
        'guide_step5_title': 'Envoyer les Documents vs Sauvegarder',
        'guide_step5_desc': 'Sur la page de synthèse finale :<br>• <strong>Envoyer les Documents</strong> : si vous avez tout fourni, cochez la validation et soumettez pour examen réglementaire.<br>• <strong>Sauvegarder le Brouillon / Envoi Partiel</strong> : si vous n\'avez qu\'une partie des pièces, cliquez sur ce bouton (toujours actif) pour enregistrer et revenir avant l\'échéance.',
        'guide_help_box_title': 'Besoin d\'aide ?',
        'guide_help_box_desc': 'Notre équipe réglementaire est à votre disposition. Vous pouvez rouvrir ce guide à tout moment via le bouton flottant avec l\'icône <strong>?</strong> en bas à droite.',
        'guide_dont_show_again': 'J\'ai pris connaissance des instructions (ne plus afficher automatiquement à la connexion)',
        'guide_btn_start': 'J\'ai compris, Commencer !',
        'guide_btn_close': 'Fermer le guide',
    },

    'de': {
        'code': 'de',
        'lang_name': 'Deutsch',
        'dir': 'ltr',
        
        # Navbar & Layout
        'portal_title': 'Kundenportal',
        'logout': 'Abmelden',
        'language': 'Sprache',
        'footer_text': 'Etichub S.r.l. · Spin-off Universität Pavia · Labor für Kosmetikprüfung und Regulatorik',
        
        # Login Page
        'login_page_title': 'Anmelden — Etichub Kundenportal',
        'welcome_back': 'Willkommen zurück',
        'login_subtitle': 'Melden Sie sich mit den von Etichub bereitgestellten Zugangsdaten an, um Ihre Produkte einzusehen und Dokumente hochzuladen.',
        'client_code': 'Kundennummer',
        'client_code_placeholder': 'z. B. CLI-001',
        'password': 'Passwort',
        'password_placeholder': 'Passwort eingeben',
        'show_password': 'Passwort anzeigen',
        'hide_password': 'Passwort verbergen',
        'login_submit': 'Anmelden',
        'need_help': 'Benötigen Sie Hilfe?',
        'contact_us': 'Kontaktieren Sie uns',
        
        # Login Error Messages
        'error_missing_fields': 'Bitte geben Sie Ihre Kundennummer und Ihr Passwort ein.',
        'error_account_inactive': 'Ihr Konto wurde deaktiviert. Bitte kontaktieren Sie Etichub für Unterstützung.',
        'error_not_configured': 'Der Zugang zum Kundenportal ist noch nicht eingerichtet. Bitte kontaktieren Sie Etichub.',
        'error_invalid_credentials': 'Falsches Passwort. Bitte versuchen Sie es erneut.',
        'error_customer_not_found': 'Kundennummer nicht gefunden.',
        'error_forbidden_product': 'Sie haben keinen Zugriff auf dieses Produkt.',
        
        # Dashboard
        'dashboard_page_title': 'Meine Produkte — Etichub Kundenportal',
        'hello_user': 'Hallo, {name}',
        'dashboard_subtitle': 'Hier finden Sie die Produkte, die derzeit von Etichub bearbeitet werden. Wählen Sie ein Produkt aus, um Dokumente zu verwalten.',
        'stat_total_products': 'Produkte insgesamt',
        'stat_in_progress': 'In Bearbeitung',
        'stat_completed': 'Abgeschlossen',
        'section_your_products': 'Ihre Produkte',
        
        # Status Badges
        'status_draft': 'Vorgang eröffnet',
        'status_in_progress': 'Unvollständige Unterlagen',
        'status_submitted': 'Dokumenten-Upload abgeschlossen',
        'status_in_processing': 'Etichub-Bearbeitung läuft',
        'status_completed': 'Bearbeitung abgeschlossen',
        'status_expired': 'Abgelaufen',
        'status_cancelled': 'Storniert',
        
        # Compact Badges
        'badge_draft': 'Offen',
        'badge_in_progress': 'In Bearbeitung',
        'badge_submitted': 'Docs Eingereicht',
        'badge_in_processing': 'In Bearbeitung',
        'badge_completed': 'Abgeschlossen',
        'badge_expired': 'Abgelaufen',
        'badge_cancelled': 'Storniert',
        
        # Macro Steps & Product Card
        'macro_step_1_title': 'Phase 1: Dokumentenerfassung',
        'macro_step_2_title': 'Phase 2: Etichub-Bearbeitung',
        'macro_step_1_short': '1. Dokumente',
        'macro_step_2_short': '2. Bearbeitung',
        'ttl_deadline': 'Upload-Frist (TTL)',
        'documents_progress': 'Dokumente',
        'assigned_on': 'Zugewiesen am',
        'expires_on': 'Gültig bis',
        'btn_upload_docs': 'Dokumente hochladen',
        'btn_docs_submitted': 'Unterlagen eingereicht',
        'btn_view_docs': 'Eingereichte Dokumente ansehen',
        'btn_expired': 'Abgelaufen — Kontaktieren Sie Etichub',
        
        # Notifications & Status Details
        'notification_etichub_submitted': 'Dokumenten-Upload abgeschlossen. Die regulatorische Abteilung von Etichub wurde benachrichtigt und beginnt in Kürze mit der Bearbeitung.',
        'notification_etichub_in_processing': 'Etichub-Bearbeitung läuft. Die technische Dokumentation (PID) wird derzeit von der regulatorischen Abteilung bearbeitet.',
        'notification_etichub_completed': 'Bearbeitung erfolgreich abgeschlossen. Die Zertifizierungsdokumentation (PID) wurde fertiggestellt und validiert.',
        
        # Alert Modal & Awareness Declaration (Übersicht und Übermittlung)
        'alert_confirm_submission_title': 'Bestätigung der endgültigen Übermittlung',
        'alert_confirm_submission_body': 'Bestätigen Sie, dass Sie alle in Ihrem Besitz befindlichen Unterlagen hochgeladen haben? Durch das Absenden wird die regulatorische Abteilung von Etichub benachrichtigt, um mit der Bearbeitung zu beginnen. Die hochgeladenen Dokumente können danach nicht mehr geändert werden.',
        'alert_confirm_btn_cancel': 'Abbrechen und prüfen',
        'alert_confirm_btn_submit': 'Ja, bestätigen und senden',
        'awareness_declaration_title': 'Erklärung zur Vollständigkeit der Unterlagen',
        'awareness_declaration_text': 'Ich erkläre hiermit formell, alle in meinem Besitz befindlichen Dokumente und Informationen übermittelt zu haben, die für die Bearbeitung des Produkts durch die regulatorische Abteilung von Etichub erforderlich sind. Mir ist bewusst, dass die Bestätigung den Abschluss der Dokumentenerfassung bescheinigt und das technische Team zum Beginn der Bearbeitung benachrichtigt.',
        'awareness_declaration_alert_js': 'Achtung: Sie müssen die formelle Erklärung zur Vollständigkeit ankreuzen, bevor Sie fortfahren.',
        
        # Summary View
        'summary_page_title': 'Übersicht und Übermittlung',
        'summary_badge': 'Abschließende Übersicht',
        'summary_title': 'Prüfen und Übermittlung bestätigen',
        'summary_case': 'Vorgang:',
        'summary_docs_uploaded': 'Hochgeladene Dokumente',
        'summary_absence_formalized': 'Formalisiertes Fehlen',
        'summary_absence_attachment': 'Anhang auf Briefbogen:',
        'summary_declaration_acquired': 'Erklärung erfasst',
        'summary_ready': 'Bereit',
        'summary_no_files': 'Keine Dateien für diesen Vorgang hochgeladen.',
        'summary_security_notice': 'Mit der Bestätigung werden die Unterlagen sicher auf dem Unternehmensserver archiviert. Eine offizielle Empfangsbestätigung wird erstellt.',
        'btn_back': 'Zurück',
        'btn_confirm_submit_50': 'Dokumente einreichen',
        'btn_confirm_submit': 'Dokumente einreichen',
        'btn_send_docs': 'Dokumente einreichen',
        'btn_partial_submit': 'Entwurf speichern / Teilübermittlung',
        'partial_save_modal_title': 'Entwurf speichern und Sitzung beenden',
        'partial_save_modal_body': 'Die bisher hochgeladenen Dateien und Daten bleiben sicher gespeichert. Der Vorgang bleibt in Bearbeitung (Unvollständige Unterlagen) und Sie können jederzeit wieder einloggen, um fehlende Dokumente vor Fristablauf hochzuladen.',
        'partial_save_btn_confirm': 'Entwurf speichern bestätigen',
        'submitting_spinner': 'Wird gesendet...',
        
        # Success View
        'success_page_title': 'Formular gesendet — Etichub',
        'success_title': 'Formular eingereicht!',
        'partial_success_page_title': 'Entwurf gespeichert — Etichub',
        'partial_success_title': 'Entwurf erfolgreich gespeichert!',
        'partial_success_msg': 'Die bisher hochgeladenen Unterlagen wurden erfolgreich gespeichert. Der Vorgang bleibt offen: Sie können jederzeit vor Fristablauf fehlende Unterlagen nachreichen.',
        'partial_status_val': '⏳ Unvollständige Unterlagen (In Bearbeitung)',
        'btn_back_to_portal': 'Zurück zu Ihren Produkten (Kundenportal)',
        'success_msg_50': 'Vielen Dank für das Einreichen der Dokumente. Die regulatorische Abteilung von Etichub wurde benachrichtigt, um mit der technischen Bearbeitung zu beginnen.',
        'success_msg': 'Vielen Dank für das Einreichen der Dokumente. Die regulatorische Abteilung von Etichub wurde benachrichtigt, um mit der technischen Bearbeitung zu beginnen.',
        'detail_status': 'Status',
        'detail_status_val': '✓ Dokumente erfasst',
        'detail_datetime': 'Datum und Uhrzeit',
        'detail_customer': 'Kunde',
        'detail_project': 'Projekt / Produkt',
        'success_receipt_hint': 'Sie können die offizielle Quittung herunterladen oder sicher zu Ihrem Kundenportal zurückkehren.',
        'btn_download_receipt': 'Offizielle Quittung herunterladen (PDF)',
        'btn_home': 'Zur Startseite',
        
        # Already Submitted View
        'already_submitted_title': 'Formular bereits eingereicht',
        'already_submitted_subtitle': 'Die Dokumentation für dieses Produkt wurde bereits bestätigt und an die regulatorische Abteilung gesendet.',
        'already_submitted_locked_msg': 'Die hochgeladenen Dokumente können nicht mehr geändert werden, da die Bearbeitung begonnen hat.',

        # Empty State
        'empty_title': 'Keine Produkte zugewiesen',
        'empty_desc': 'Derzeit befinden sich keine Produkte in Bearbeitung. Sie werden benachrichtigt, sobald Etichub Ihnen ein neues Projekt zuweist.',
        
        # Success page & cross-links
        'back_to_portal': 'Zurück zu Ihren Produkten (Kundenportal)',
        
        # Timeline / History Modal
        'timeline_modal_title': 'Vorgangsverlauf & Bearbeitungsstatus',
        'timeline_click_hint': 'Klicken Sie, um den Verlauf anzuzeigen',
        'timeline_step_assigned': 'Vorgang erstellt & zugewiesen',
        'timeline_step_assigned_desc': 'Das Formular wurde vorbereitet und für das Hochladen von Unterlagen freigegeben.',
        'timeline_step_submitted': 'Dokumentenübermittlung abgeschlossen',
        'timeline_step_submitted_desc': 'Alle erforderlichen Dokumente wurden mit Vollständigkeitserklärung übermittelt.',
        'timeline_step_processing': 'Übernahme durch die regulatorische Abteilung',
        'timeline_step_processing_desc': 'Etichub-Experten haben mit der technischen Prüfung und Erstellung der PID begonnen.',
        'timeline_step_completed': 'Regulatorische Bearbeitung abgeschlossen',
        'timeline_step_completed_desc': 'Zertifizierungsunterlagen erfolgreich validiert und abgeschlossen. Zyklus beendet.',
        'timeline_step_pending': 'Warten auf vorherige Phasen',
        'timeline_close': 'Schließen',
        'timeline_btn_history': 'Bearbeitungsverlauf',

        # Onboarding & Upload Guide Modal
        'guide_fab_label': 'Upload-Hilfe',
        'guide_modal_title': 'Leitfaden zum Dokumenten-Upload',
        'guide_modal_subtitle': 'Einfache und klare Anleitung zur Einreichung Ihrer Unterlagen in wenigen Schritten.',
        'guide_step1_badge': '1. Unterlagen vorbereiten',
        'guide_step1_title': 'Zulässige Formate & Dateigrößen',
        'guide_step1_desc': 'Zulässige Formate sind <strong>PDF, Word (.doc, .docx)</strong> sowie <strong>JPG / PNG</strong> Bilder. Die maximale Dateigröße beträgt <strong>10 MB</strong> pro Datei. Bitte achten Sie auf gute Lesbarkeit und Vollständigkeit.',
        'guide_step2_badge': '2. Dateien hochladen',
        'guide_step2_title': 'Per Drag & Drop oder Klick auswählen',
        'guide_step2_desc': 'Ziehen Sie die Datei für jede Anforderung in das gestrichelte Feld oder klicken Sie auf <strong>"Hier klicken oder ablegen"</strong>. Der Upload erfolgt sofort: ein grünes Häkchen bestätigt die Speicherung.',
        'guide_step3_badge': '3. Pflichtdokumente',
        'guide_step3_title': 'Fortschritt & zwingende Angaben',
        'guide_step3_desc': 'Dokumente mit dem roten Kennzeichen <strong>"Erforderlich"</strong> sind obligatorisch: Die Schaltfläche <strong>"Weiter"</strong> wird erst aktiv, sobald alle Pflichtdokumente des Schritts hochgeladen oder begründet wurden.',
        'guide_step4_badge': '4. Dokument fehlt?',
        'guide_step4_title': 'Formelle Erklärung hochladen',
        'guide_step4_desc': 'Falls ein Pflichtdokument vorübergehend nicht vorliegt, klicken Sie auf <strong>"Formelle Erklärung hochladen"</strong>: Laden Sie eine Erklärung auf <strong>gestempeltem und unterschriebenem Firmenbriefbogen</strong> hoch und bestätigen Sie die Erklärung. Dadurch wird der nächste Schritt freigeschaltet.',
        'guide_step5_badge': '5. Abschluss der Sitzung',
        'guide_step5_title': 'Unterlagen einreichen vs. Entwurf speichern',
        'guide_step5_desc': 'In der abschließenden Zusammenfassung haben Sie zwei Optionen:<br>• <strong>Unterlagen einreichen</strong>: Wenn alles vollständig ist, bestätigen Sie die Erklärung zur Bearbeitung durch Etichub.<br>• <strong>Entwurf speichern / Teilübermittlung</strong>: Falls Sie Unterlagen nachreichen möchten, klicken Sie auf diesen Button (immer aktiv), um zu speichern und vor Fristablauf fortzufahren.',
        'guide_help_box_title': 'Benötigen Sie Unterstützung?',
        'guide_help_box_desc': 'Unser Regulatorik-Team steht Ihnen gerne zur Seite. Sie können diesen Leitfaden jederzeit über den schwebenden <strong>?</strong>-Button unten rechts aufrufen.',
        'guide_dont_show_again': 'Ich habe die Anleitung zur Kenntnis genommen (beim Anmelden nicht mehr automatisch anzeigen)',
        'guide_btn_start': 'Verstanden, Loslegen!',
        'guide_btn_close': 'Schließen',
    },
}


def get_client_language(request):
    """
    Determines active language for the client portal.
    Priority:
    1. Query param ?lang=<code> (if valid)
    2. Session 'client_language'
    3. Cookie 'client_language'
    4. Default: 'it'
    """
    lang = request.GET.get('lang')
    if lang and lang.lower() in SUPPORTED_LANGUAGE_CODES:
        lang = lang.lower()
        request.session['client_language'] = lang
        request.session.modified = True
        return lang

    session_lang = request.session.get('client_language')
    if session_lang and session_lang in SUPPORTED_LANGUAGE_CODES:
        return session_lang

    cookie_lang = request.COOKIES.get('client_language')
    if cookie_lang and cookie_lang in SUPPORTED_LANGUAGE_CODES:
        request.session['client_language'] = cookie_lang
        request.session.modified = True
        return cookie_lang

    return 'it'


def get_translation_context(request):
    """
    Returns context dictionary containing active language,
    translations dictionary, and list of supported languages.
    """
    lang = get_client_language(request)
    t = TRANSLATIONS.get(lang, TRANSLATIONS['it'])
    
    current_lang_obj = next((item for item in SUPPORTED_LANGUAGES if item['code'] == lang), SUPPORTED_LANGUAGES[0])
    
    return {
        'client_lang': lang,
        'current_lang_obj': current_lang_obj,
        'supported_languages': SUPPORTED_LANGUAGES,
        't': t,
    }

# Document Collector - Raccolta Guidata di Documenti

Applicazione web Django per la raccolta progressiva e controllata di documenti da parte dei clienti tramite moduli guidati e configurabili.

## 🎯 Caratteristiche

- **Moduli Configurabili**: Crea moduli di raccolta documenti senza toccare il codice
- **Flusso Guidato**: Clienti navigano step by step con validazione ad ogni passaggio
- **Upload Gestito**: Caricamento file sicuro con validazione estensione/MIME/dimensione
- **Documenti Opzionali**: Supporto per documenti facoltativi con dichiarazioni di consapevolezza
- **Archiviazione NAS**: File salvati direttamente sul NAS Synology in cartelle organizzate
- **Audit Logging**: Tracciamento completo di tutte le azioni
- **Admin Panel**: Interfaccia gestionale intuitiva per amministratori
- **Reverse Proxy Ready**: Configurazione HTTPS dietro proxy Synology

## 🛠️ Stack Tecnologico

- **Backend**: Python 3.11+, Django 4.2
- **Database**: PostgreSQL 15+
- **Frontend**: HTML5, Bootstrap 5, HTMX, Alpine.js
- **Server**: Gunicorn
- **Containerizzazione**: Docker, Docker Compose

## 📦 Installazione Locale (Sviluppo)

### Prerequisiti
- Python 3.11+
- Git
- (Opzionale) Docker & Docker Compose

### Setup

```bash
# Clona il repository
git clone <repository-url>
cd EHModuli

# Crea virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# Installa dipendenze
pip install -r requirements.txt

# Configura variabili ambiente
cp .env.example .env
# Modifica .env se necessario

# Per lo sviluppo locale con SQLite
echo "USE_SQLITE=True" >> .env.local

# Esegui migrazioni
python manage.py migrate

# Crea superuser
python manage.py createsuperuser

# Avvia server
python manage.py runserver
```

Accedi a:
- Applicazione: http://localhost:8000
- Admin Django: http://localhost:8000/admin
- Admin Panel Custom: http://localhost:8000/modules/admin

## 🐳 Installazione Docker (Synology/Portainer)

### Setup Veloce

```bash
# Configura .env
cp .env.example .env
# Modifica .env con le tue impostazioni per il Synology

# Build e avvio
docker-compose up -d

# Verifiche
docker-compose logs -f app
docker-compose ps

# Accesso
# http://<your-nas-ip>:6000
```

### Primo Accesso

L'entrypoint crea automaticamente un superuser `admin` / `admin`. **Cambia subito la password!**

### Dati Persistenti

I dati sono salvati nei percorsi specificati in `.env`:
- Applicazione: `/volume1/docker/document-collector/appdata`
- Database: `/volume1/docker/document-collector/postgres`
- Documenti Cliente: `/volume1/Clienti`

## 📊 Modelli Dati

### Struttura Core

```
FormTemplate        → Modulo di raccolta (v1, v2, ...)
├── FormStep        → Step progressivi (1, 2, 3, ...)
│   └── DocumentRequirement  → Documenti richiesti
└── FormAssignment  → Assegnazione a cliente
    ├── DocumentUpload       → File caricati
    └── AwarenessDeclaration → Dichiarazioni consapevolezza
```

### Sicurezza

- **UUID**: Tutti gli ID esposti sono UUID, non sequenziali
- **Token Sicuri**: FormAssignment.secure_token (40 char alphanumerico)
- **Audit Log**: Tracciamento IP, User-Agent, azioni
- **File Checksum**: SHA-256 per verificare integrità

## 🔐 Configurazione Reverse Proxy (Synology)

Per esporre l'app dietro HTTPS tramite reverse proxy Synology:

```bash
# settings.py supporta automaticamente:
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = [...]  # Configura da .env

# Nel reverse proxy Synology, aggiungi header:
X-Forwarded-Proto: https
X-Forwarded-Host: tuo-dominio.it
```

## 👥 Ruoli Utenti

- **Admin**: Crea/modifica moduli, gestisce clienti, vede tutte le assegnazioni
- **Operator**: Assegna moduli, monitora completamento
- **Cliente**: Accede via token pubblico, compila modulo

## 📝 Workflow Tipico

### Amministratore

1. Crea FormTemplate (modulo)
2. Aggiunge FormStep (es: "Dati Anagrafici", "Documenti", "Riepilogo")
3. Per ogni step, aggiunge DocumentRequirement (es: "ID", "Buste Paga")
4. Pubblica il modulo

### Operator

1. Crea Cliente
2. Assegna FormTemplate a Cliente via admin panel
3. Riceve token pubblico
4. Condivide link: `/modules/form/{token}/`

### Cliente

1. Riceve email con link pubblico
2. Apre link (no login richiesto)
3. Legge intro modulo
4. Naviga step by step
5. Carica documenti (validazione client-side + server-side)
6. Compila dichiarazioni per doc opzionali
7. Visualizza riepilogo
8. Conferma invio (immutabile da quel punto)

## 🧪 Test

```bash
# Test models
python manage.py test modules.tests.test_models

# Test views
python manage.py test modules.tests.test_views

# Test utils
python manage.py test modules.tests.test_utils

# Test tutto
python manage.py test
```

## 📁 Struttura Cartelle

```
EHModuli/
├── app/                           # Progetto Django principale
│   ├── settings.py               # Configurazione globale
│   ├── urls.py                   # URL routing
│   └── wsgi.py
├── accounts/                      # App autenticazione
├── modules/                       # App moduli e form
│   ├── models.py                 # 10 modelli Django
│   ├── views.py                  # Viste pubbliche
│   ├── views_admin.py            # Viste amministrative
│   ├── utils.py                  # Utility (security, file, audit)
│   ├── admin.py                  # Registrazione Django admin
│   ├── templates/
│   │   ├── modules/              # Template pubblici
│   │   └── admin/                # Template admin
│   └── static/                   # CSS/JS custom
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── requirements.txt
├── manage.py
├── .env.example
├── .gitignore
└── README.md                      # Questo file
```

## 🔧 Configurazione Variabili Ambiente

```ini
# Applicazione
DEBUG=False
SECRET_KEY=<cambalo-in-produzione>
APP_PORT=6000
TZ=Europe/Rome

# Database
POSTGRES_DB=document_collector
POSTGRES_USER=collector_user
POSTGRES_PASSWORD=<secure-password>

# Django
ALLOWED_HOSTS=localhost,127.0.0.1,your-nas-ip
ENVIRONMENT=development

# Docker volumes
APP_DATA_PATH=/volume1/docker/document-collector/appdata
POSTGRES_DATA_PATH=/volume1/docker/document-collector/postgres
CUSTOMER_DOCUMENTS_PATH=/volume1/Clienti
```

## 🚀 Deployment Synology Container Manager

1. **Preparazione**:
   ```bash
   docker build -t document-collector .
   docker tag document-collector:latest your-registry/document-collector:latest
   ```

2. **Container Manager → Progetti**:
   - Crea nuovo progetto
   - Importa docker-compose.yml
   - Configura variabili .env

3. **Avvio**:
   - Container Manager riavvia automaticamente in caso di crash
   - Verificate healthcheck: Status = "healthy"

4. **Accesso**:
   - http://NAS-IP:6000 (HTTP)
   - https://your-domain.it (se dietro reverse proxy)

## 📞 Support

- Django Admin: http://app:8000/admin (interno docker)
- Audit Log: Vedi tutte le azioni in `AuditLog` Django admin
- File Upload: I file sono sempre salvati in `/storage/clienti` sul NAS

## 📄 Licenza

MIT License - Vedi LICENSE file

## 🙏 Credits

Sviluppato con Django 4.2, Bootstrap 5, HTMX e Alpine.js.

---

**Ultima modifica**: Settembre 2026  
**Versione**: 1.0.0

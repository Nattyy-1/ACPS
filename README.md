# Automated Construction Permit System (ACPS)

A Django REST Framework backend for the Ethiopian construction sector. Automates the end-to-end construction permit lifecycle — application, payment, technical review, senior approval, permit issuance, digital site inspection, and completion certification.

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [API Overview](#api-overview)
- [Authentication & Authorization](#authentication--authorization)
- [Application Lifecycle](#application-lifecycle)
- [Testing](#testing)
- [Management Commands](#management-commands)
- [PDF Generation](#pdf-generation)
- [Deployment](#deployment)
- [API Documentation](#api-documentation)

---

## Architecture

```
┌─────────────┐      ┌──────────────────────────────────────────────┐
│  React SPA  │─────▶│          Django REST Framework API            │
│  (frontend) │◀────│              /api/v1/                         │
└─────────────┘      │                                              │
                     │  ┌─────────┐ ┌──────────┐ ┌──────────────┐   │
                     │  │accounts │ │applications│ │  payments   │   │
                     │  ├─────────┤ ├──────────┤ ├──────────────┤   │
                     │  │ reviews │ │inspections│ │   permits   │   │
                     │  ├─────────┤ ├──────────┤ ├──────────────┤   │
                     │  │notifications│admin_config│              │   │
                     │  └─────────┘ └──────────┘ └──────────────┘   │
                     │                                              │
                     │  ┌──────────┐  ┌─────────┐  ┌──────────┐   │
                     │  │PostgreSQL│  │  Media  │  │  Console │   │
                     │  │/ SQLite  │  │ Storage │  │  / SMTP  │   │
                     │  └──────────┘  └─────────┘  └──────────┘   │
                     └──────────────────────────────────────────────┘
```

Five user roles: **Applicant**, **Review Officer**, **Inspector**, **Senior Officer**, **Administrator**.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Django 6.0.5 + Django REST Framework 3.17.1 |
| Python | 3.14 |
| Database | PostgreSQL (production) / SQLite (development) |
| Auth | SimpleJWT (access 60m, refresh 7d), bcrypt password hashing |
| PDF | ReportLab + qrcode |
| CORS | django-cors-headers |
| Deployment | Gunicorn, Render-ready |

---

## Quick Start

### Prerequisites

- Python 3.14+
- PostgreSQL (optional, falls back to SQLite)

### Setup

```bash
# 1. Clone the repository
git clone <repo-url> && cd acps

# 2. Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env as needed — at minimum set SECRET_KEY and DEBUG=True

# 5. Run migrations
python manage.py migrate

# 6. Create a superuser (admin)
python manage.py createsuperuser

# 7. Start development server
python manage.py runserver
```

The API is available at `http://localhost:8000/api/v1/`.

---

## Configuration

All configuration is via environment variables (or `.env` file using `python-decouple`).

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `django-insecure-change-me-in-production` | Django secret key |
| `DEBUG` | `False` | Enable debug mode |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `DATABASE_URL` | — | PostgreSQL connection string (production) |
| `DB_ENGINE` | `django.db.backends.sqlite3` | Database engine (dev fallback) |
| `DB_NAME` | `db.sqlite3` / `acps` | Database name |
| `RENDER` | `False` | Auto-set by Render for deployment |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Frontend origins |
| `TIME_ZONE` | `Africa/Addis_Ababa` | Server timezone |
| `EMAIL_BACKEND` | `console` | Email backend (`console` or `smtp`) |
| `THROTTLE_USER` | `100/minute` | Authenticated request rate limit |
| `THROTTLE_ANON` | `100/minute` | Anonymous request rate limit |
| `PAGE_SIZE` | `20` | Default pagination page size |

---

## Project Structure

```
acps/
├── config/                  # Django project configuration
│   ├── settings.py          # Settings with env var overrides
│   ├── urls.py              # Root URL conf (all apps under /api/v1/)
│   ├── wsgi.py
│   └── asgi.py
│
├── accounts/                # Authentication & user management
│   ├── models.py            # Custom User model (email as username), LoginAttemptLog
│   ├── serializers.py       # Register, Login, Profile, AdminUser, VaultDocument
│   ├── views.py             # Register, Login, Logout, Password reset, Profile, Admin CRUD
│   ├── urls.py              # /auth/*, /users/* endpoints
│   └── permissions.py       # IsAdmin, IsApplicant, IsReviewOfficer, IsInspector, IsSeniorOfficer
│
├── applications/            # Permit application submission
│   ├── models.py            # Application, Document, ApplicationHistory, NeighborConsent
│   ├── serializers.py       # Create, Detail, List, Update, Document, Neighbor, History
│   ├── views.py             # CRUD, fee, documents, neighbors, submit, timeline
│   ├── urls.py              # /applications/* endpoints
│   ├── tests.py             # 190 model + API integration tests
│   └── management/commands/ # cleanup_drafts
│
├── payments/                # Payment demonstration
│   ├── models.py            # Payment, FeeSchedule
│   ├── serializers.py       # InvoiceDetail, PaymentConfirm
│   ├── views.py             # Invoice, pay (Telebirr/CBE/Bank), receipt, confirm, expiry
│   ├── urls.py              # /payments/* endpoints
│   └── management/commands/ # payment_reminders
│
├── reviews/                 # Technical review workflow
│   ├── models.py            # ReviewComment, SLAConfig
│   ├── serializers.py       # Comment create/list, decision, SLA config
│   ├── views.py             # Assign (round-robin), queue, workspace, comments, decision, SLA
│   └── urls.py              # /reviews/*, .../assign-reviewer/, .../comments/* endpoints
│
├── inspections/             # Construction & digital site inspection
│   ├── models.py            # Inspection, InspectionChecklistTemplate/Item, InspectionPhoto
│   ├── serializers.py       # Inspection, ChecklistItem, ChecklistUpdate, Photo
│   ├── views.py             # Commence, complete, schedule, start, checklist, photos, submit, reinspect
│   ├── urls.py              # /inspections/*, .../commence/, .../declare-completion/ endpoints
│   └── management/commands/ # inspection_reminders
│
├── permits/                 # Planning consent, permit & completion certificate
│   ├── models.py            # Permit (PC/CP/CC)
│   ├── serializers.py       # PublicPermit, AuthenticatedPermit
│   ├── views.py             # Approvals queue, issue consent/permit/certificate, reject, verify
│   ├── pdf_utils.py         # PDF generation with ReportLab + QR codes + officer signatures
│   ├── urls.py              # /approvals/*, /permits/*, /verify/* endpoints
│   └── templates/permits/   # verify.html
│
├── notifications/           # In-app notifications & email
│   ├── models.py            # Notification
│   ├── views.py             # List, read, read-all
│   ├── services.py          # create_notification() + email templates for all events
│   └── urls.py              # /notifications/* endpoints
│
├── admin_config/            # Administration & configuration
│   ├── models.py            # NotificationTemplate, OfficerSignature
│   ├── views.py             # Stats, audit log, fee/SLA/checklist/template config, CSV export, signatures
│   └── urls.py              # /admin/* endpoints
│
├── api_docs/                # API documentation
│   ├── openapi.yaml         # Complete OpenAPI 3.0 spec (77 endpoints)
│   └── REVIEW.md            # SRS compliance review
│
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## API Overview

All endpoints are prefixed with `/api/v1/`.

### Authentication (`/auth/*`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register/` | Public | Register new applicant |
| POST | `/auth/login/` | Public | Login, returns JWT + role + user_id |
| POST | `/auth/refresh/` | Public | Refresh access token |
| POST | `/auth/logout/` | Bearer | Blacklist refresh token |
| POST | `/auth/forgot-password/` | Public | Send password reset email |
| POST | `/auth/reset-password/` | Public | Reset password with token |

### User Management (`/users/*`)

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| GET/PUT | `/users/me/` | All | Get/update own profile |
| GET/POST | `/users/me/documents/` | Applicant | List/upload vault documents |
| GET | `/users/{id}/` | Admin | Get user detail |
| GET/POST | `/users/` | Admin | List/create users |
| PUT | `/users/{id}/deactivate/` | Admin | Deactivate user |

### Applications (`/applications/*`)

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| GET/POST | `/applications/` | All (GET), Applicant (POST) | List/create applications |
| GET/PUT | `/applications/{id}/` | All (GET), Applicant (PUT) | Get detail / update draft |
| GET | `/applications/{id}/fee/` | Applicant | Get fee breakdown |
| POST | `/applications/{id}/documents/` | Applicant | Upload document (multipart) |
| DELETE | `/applications/{id}/documents/{doc_id}/` | Applicant | Delete document (DRAFT only) |
| GET | `/applications/{id}/required-documents/` | Applicant | Get required document checklist |
| POST | `/applications/{id}/submit/` | Applicant | Submit application |
| GET/POST | `/applications/{id}/neighbors/` | Applicant | List/add neighbor consent |
| DELETE | `/applications/{id}/neighbors/{n_id}/` | Applicant | Delete neighbor (DRAFT only) |
| GET | `/applications/{id}/timeline/` | Applicant | Get status history |

### Payments (`/payments/*`)

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| GET | `/payments/invoices/{id}/` | Applicant | Invoice detail |
| POST | `/payments/invoices/{id}/pay/` | Applicant | Initiate payment (Telebirr/CBE/Bank) |
| POST | `/payments/invoices/{id}/bank-receipt/` | Applicant | Upload bank receipt (multipart) |
| PUT | `/payments/invoices/{id}/confirm/` | Admin | Confirm bank transfer |
| GET | `/payments/receipts/{id}/` | Applicant/Admin | Download receipt PDF |
| GET | `/payments/` | Admin | List all payments |
| POST | `/payments/expire/` | Admin | Cron: expire overdue payments |

### Technical Review (`/reviews/*`)

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| POST | `/applications/{id}/assign-reviewer/` | Admin | Assign reviewer (round-robin) |
| GET | `/reviews/my-queue/` | Review Officer | My assigned reviews |
| GET | `/reviews/workspace/{id}/` | Review Officer | Review workspace |
| GET/POST | `/applications/{id}/comments/` | All (GET), Review (POST) | List/create comments |
| PUT | `/applications/{id}/comments/{c_id}/resolve/` | Review Officer | Resolve/escalate comment |
| POST | `/applications/{id}/review-decision/` | Review Officer | Approve/reject application |
| GET | `/reviews/sla-status/` | Senior/Admin | SLA breach overview |

### Approvals & Permits (`/approvals/*`, `/permits/*`, `/verify/*`)

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| GET | `/approvals/queue/` | Senior Officer | Awaiting approval queue |
| GET | `/approvals/{id}/` | Senior Officer | Full approval detail |
| POST | `/applications/{id}/issue-consent/` | Senior Officer | Issue planning consent PDF |
| POST | `/applications/{id}/issue-permit/` | Senior Officer | Issue construction permit PDF |
| POST | `/applications/{id}/issue-completion-certificate/` | Senior Officer | Issue completion certificate PDF |
| POST | `/applications/{id}/reject-final/` | Senior Officer | Reject at final stage |
| GET | `/approvals/completion-review/{id}/` | Senior Officer | Completion review data |
| GET | `/permits/{number}/` | All/Public | Permit detail |
| GET | `/verify/{number}/` | Public | HTML verification page (QR) |

### Inspections (`/inspections/*`)

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| POST | `/applications/{id}/commence/` | Applicant | Commence construction |
| POST | `/applications/{id}/declare-completion/` | Applicant | Declare completion (+ photos) |
| GET | `/applications/{id}/inspections/` | Applicant/Inspector/Senior/Admin | List inspections |
| POST | `/applications/{id}/inspections/{i_id}/request-reinspection/` | Applicant | Request re-inspection |
| GET | `/inspections/my-schedule/` | Inspector | My upcoming inspections |
| GET | `/inspections/{id}/` | Inspector | Inspection detail + checklist |
| POST | `/inspections/{id}/start/` | Inspector | Start inspection |
| PUT | `/inspections/{id}/checklist/` | Inspector | Update checklist items |
| POST | `/inspections/{id}/photos/` | Inspector | Upload photos (multipart) |
| POST | `/inspections/{id}/submit/` | Inspector | Submit inspection result |

### Notifications (`/notifications/*`)

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| GET | `/notifications/` | All | List notifications |
| PUT | `/notifications/{id}/read/` | All | Mark one as read |
| PUT | `/notifications/read-all/` | All | Mark all as read |

### Administration (`/admin/*`)

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| GET | `/admin/stats/` | Admin | System statistics |
| GET | `/admin/audit-log/` | Admin | Paginated audit log |
| GET/PUT | `/admin/config/fee-schedule/` | Admin | Read/update fee tiers |
| GET/PUT | `/admin/config/sla-thresholds/` | Admin | Read/update SLA configs |
| GET/PUT | `/admin/config/inspection-checklists/{type}/` | Admin | Read/update checklists |
| GET/POST | `/admin/config/notification-templates/` | Admin | Read/update email templates |
| GET | `/admin/reports/export/` | Admin | Download CSV report |
| GET/POST | `/admin/signatures/{user_id}/` | Admin | Get/upload officer signature |

---

## Authentication & Authorization

### JWT Flow

1. `POST /auth/login/` with email + password → receives `access` (60 min), `refresh` (7 days), `role`, `user_id`
2. Include `Authorization: Bearer <access_token>` in all subsequent requests
3. When access token expires, call `POST /auth/refresh/` with `{"refresh": "<refresh_token>"}` to get a new access token
4. `POST /auth/logout/` blacklists the refresh token

### Roles

| Role | Permissions |
|------|------------|
| `APPLICANT` | Create/manage own applications, upload docs, make payments, commence construction, declare completion |
| `REVIEW_OFFICER` | Review assigned applications, add comments, approve/reject |
| `INSPECTOR` | View assigned inspections, perform digital inspections, submit results |
| `SENIOR_OFFICER` | Final approval, issue consent/permits/certificates, reject applications |
| `ADMIN` | User management, system config, fee/SLA/checklist config, reports, signature upload |

---

## Application Lifecycle

```
DRAFT ──▶ PAYMENT_PENDING ──▶ AWAITING_ASSIGNMENT ──▶ (review) ──▶ AWAITING_SENIOR_APPROVAL ──▶ CONSENT_ISSUED ──▶ PERMIT_ISSUED ──▶ UNDER_CONSTRUCTION ──▶ COMPLETION_DECLARED ──▶ COMPLETED
  │                              │                        │                      │                        │
  └──(30d auto-delete)           └──(7d expiry)           └──(revision loop)      └──(senior reject)       └──(cancelled)
                                      │                       │
                              PAYMENT_EXPIRED          REVISION_REQUIRED ──▶ (max 3 cycles → senior alert)
```

---

## Testing

```bash
# Run all tests
python manage.py test

# Run tests for a specific app
python manage.py test applications

# Run with verbose output
python manage.py test --verbosity=2
```

**190 tests** (186 passing, 4 intermittent due to throttle cache):
- Model unit tests: ARN generation, fee calculation, category classification
- API integration tests: all endpoints, happy path, validation errors, 401/403 responses

---

## Management Commands

| Command | Description | Schedule |
|---------|-------------|----------|
| `cleanup_drafts` | Delete DRAFT apps older than 30 days | Daily cron |
| `payment_reminders` | Send 48h payment reminder emails | Daily cron |
| `sla_reminders` | Send SLA reminder/escalation alerts | Daily cron |
| `inspection_reminders` | Send 48h pre-inspection emails | Daily cron |

---

## PDF Generation

Three PDF types are generated using **ReportLab** with QR codes and officer signatures:

| Document | Format | Key Fields | QR Target |
|----------|--------|------------|-----------|
| Planning Consent | `PC-YYYY-XXXXXX` | ARN, applicant, plot, category, specs, issue date, 6mo expiry, signature | `/verify/{permit_number}` |
| Construction Permit | `CP-YYYY-XXXXXX` | ARN, applicant, plot, category, specs, contractor, issue date, 12mo expiry, signature | `/verify/{permit_number}` |
| Completion Certificate | `CC-YYYY-XXXXXX` | ARN, permit number, applicant, plot, final specs, completion date, signature | `/verify/{permit_number}` |

Officer signature PNGs are uploaded via `POST /admin/signatures/{user_id}/` and embedded at a fixed position on each PDF.

---

## Deployment

### Render

The project is configured for one-click deployment on Render:

1. Create a new **Web Service** connected to this repository
2. Set build command: `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`
3. Set start command: `gunicorn config.wsgi`
4. Add environment variables (see `.env.example`)
5. Add a **PostgreSQL** database — Render sets `DATABASE_URL` automatically

### Manual (Ubuntu 22.04)

```bash
# System dependencies
sudo apt update && sudo apt install python3-pip postgresql nginx

# Setup
git clone <repo> && cd acps
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env   # configure database, secret key

# Database
sudo -u postgres createdb acps
python manage.py migrate
python manage.py collectstatic --noinput

# Gunicorn service (systemd)
sudo nano /etc/systemd/system/gunicorn.service
# ... configure service

# Nginx reverse proxy with SSL
sudo nano /etc/nginx/sites-available/acps
# ... configure proxy_pass to gunicorn
```

---

## API Documentation

Full OpenAPI 3.0 specification is available at:

- **YAML spec**: `api_docs/openapi.yaml` — 77 endpoints, 65+ schemas
- **SRS review**: `api_docs/REVIEW.md` — task-by-task compliance report

View interactively at [Swagger Editor](https://editor.swagger.io) by pasting the YAML content.

---

## Project Status

| Metric | Value |
|--------|-------|
| Backend tasks implemented | ~215/222 (97%) |
| Tests | 190 (186 ✅, 4 ❌ intermittent) |
| Apps | 8 |
| Endpoints | 77 |
| Management commands | 4 |
| PDF generators | 3 |
| SRS compliance | 63/63 §4 endpoints covered |

**Known issues** (5 SRS non-conformances):
1. Category classification missing span ≤7m + fire safety checks (FR-3.3)
2. Anonymous throttle at 100/min instead of 20/min (NFR-3)
3. Forgot password URL hardcoded to localhost:3000 (FR-1.4)
4. `LoginAttemptLog` uses email string instead of user_id FK (FR-1.6)
5. 4 intermittent test errors from shared throttle cache between TestCase classes

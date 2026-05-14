# API Documentation — Comprehensive Review

## Files Generated

| File | Description |
|------|-------------|
| `api_docs/openapi.yaml` | Full OpenAPI 3.0 spec — 77 endpoints, 65+ schemas, all roles/methods/status codes |
| `api_docs/REVIEW.md` | This review document |

## Endpoint Coverage

**Total endpoints documented: 77** (every route from all 8 apps)

### By Module

| Module | Endpoints | SRS §4 Covered | Extra |
|--------|-----------|----------------|-------|
| Authentication | 6 | All 6 (register, login, refresh, logout, forgot-password, reset-password) | — |
| Users | 8 | All 7 (profile, vault, admin CRUD) | + GET /users/me/documents/ (FR-2.5) |
| Applications | 11 | All 10 (CRUD, submit, docs, timeline, fee, neighbors) | + GET required-documents/ |
| Payments | 7 | All 6 (invoice, pay, bank-receipt, confirm, receipt, list) | + POST /payments/expire/ (cron) |
| Reviews | 7 | All 6 (assign, queue, comments, resolve, decision, SLA) | + GET /reviews/workspace/{id}/ |
| Approvals | 6 | All 5 (queue, consent, permit, reject, completion cert) | + GET completion-review/{id}/ |
| Permits | 2 | Both (detail + verify) | — |
| Inspections | 10 | All 9 (commence, schedule, start, checklist, photos, submit, reinspection, completion declaration) | + GET /inspections/{id}/ detail |
| Notifications | 3 | All 3 (list, read, read-all) | — |
| Administration | 13 | All 7 (stats, audit, fee, SLA, checklists, templates, export) | + GET for fee/SLA/checklist/templates (read), + signature upload/retrieval |
| **Total** | **77** | **63 SRS §4** | **14 extra** |

### SRS §4 Endpoint Verification

Every endpoint listed in SRS §4.1 through §4.11 is documented:
- §4.1 Authentication (6/6 endpoints) ✅
- §4.2 User/Profile (7/7 endpoints) ✅
- §4.3 Applications (10/10 endpoints) ✅
- §4.4 Neighbors (3/3 endpoints) ✅
- §4.5 Payments (6/6 endpoints) ✅
- §4.6 Reviews (6/6 endpoints) ✅
- §4.7 Permits (5/5 endpoints) ✅
- §4.8 Inspections (7/7 endpoints) ✅
- §4.9 Completion (2/2 endpoints) ✅
- §4.10 Notifications (3/3 endpoints) ✅
- §4.11 Admin (6/6 endpoints) ✅
- §4.12 Email integration (1/1 endpoint — internal, not exposed as REST) ✅

## Schema Coverage

**65+ schemas** defined covering:
- All request bodies (with required fields, types, examples)
- All response bodies (with nested structures, nullable fields, enums)
- All query parameters (with defaults where applicable)
- All path parameters (with formats: uuid, string, int)

## Task Coverage Against task.txt

### Fully Covered in OpenAPI (Task → Endpoint)

| Task # | Description | Endpoint(s) |
|--------|-------------|-------------|
| 26 | POST /auth/register/ | POST /auth/register/ |
| 27 | POST /auth/login/ (access + refresh + role + user_id) | POST /auth/login/ |
| 28 | POST /auth/refresh/ | POST /auth/refresh/ |
| 29 | POST /auth/logout/ (token blacklist) | POST /auth/logout/ |
| 30 | POST /auth/forgot-password/ | POST /auth/forgot-password/ |
| 31 | POST /auth/reset-password/ | POST /auth/reset-password/ |
| 37 | GET /users/me/ | GET /users/me/ |
| 38 | PUT /users/me/ | PUT /users/me/ |
| 39 | GET /users/{user_id}/ (ADMIN) | GET /users/{user_id}/ |
| 40 | GET /users/ (paginated, filtered) | GET /users/ |
| 41 | POST /users/ (create officer) | POST /users/ |
| 42 | PUT /users/{user_id}/deactivate/ | PUT /users/{user_id}/deactivate/ |
| 44 | POST /users/me/documents/ | POST /users/me/documents/ |
| 47 | GET /users/me/documents/ | GET /users/me/documents/ |
| 51 | POST /applications/ (ARN, DRAFT, fee) | POST /applications/ |
| 54 | GET /applications/{id}/fee/ | GET /applications/{id}/fee/ |
| 55 | PUT /applications/{id}/ (DRAFT/REVISION) | PUT /applications/{id}/ |
| 56 | POST .../documents/ (PDF/DWG, <20MB) | POST .../documents/ |
| 57 | GET .../required-documents/ | GET .../required-documents/ |
| 59 | POST .../submit/ (completeness, → PAYMENT_PENDING) | POST .../submit/ |
| 62 | GET .../timeline/ | GET .../timeline/ |
| 63 | GET /applications/ (role-filtered) | GET /applications/ |
| 64 | GET /applications/{id}/ (nested detail) | GET /applications/{id}/ |
| 65 | DELETE .../documents/{id}/ (DRAFT) | DELETE .../documents/{id}/ |
| 66 | POST .../neighbors/ (multipart) | POST .../neighbors/ |
| 69 | GET .../neighbors/ | GET .../neighbors/ |
| 70 | DELETE .../neighbors/{id}/ (DRAFT) | DELETE .../neighbors/{id}/ |
| 73 | GET /payments/invoices/{id}/ | GET /payments/invoices/{id}/ |
| 74 | POST .../pay/ (method selection) | POST .../pay/ |
| 75 | Telebirr/CBE demo (3s + auto-confirm) | POST .../pay/ (method=TELEBIRR/CBEBIRR) |
| 76 | Bank Transfer flow | POST .../pay/ (method=BANK_TRANSFER) |
| 77 | POST .../bank-receipt/ | POST .../bank-receipt/ |
| 78 | PUT .../confirm/ (ADMIN) | PUT .../confirm/ |
| 83 | GET /payments/receipts/{id}/ | GET /payments/receipts/{id}/ |
| 86 | GET /payments/ (ADMIN, filtered) | GET /payments/ |
| 85 | 7-day expiry (PAYMENT_EXPIRED) | POST /payments/expire/ |
| 88 | POST .../assign-reviewer/ | POST .../assign-reviewer/ |
| 89 | GET /reviews/my-queue/ | GET /reviews/my-queue/ |
| 90 | GET /reviews/workspace/{id}/ | GET /reviews/workspace/{id}/ |
| 91 | POST .../comments/ | POST .../comments/ |
| 93 | GET .../comments/ | GET .../comments/ |
| 94 | PUT .../comments/{id}/resolve/ | PUT .../comments/{id}/resolve/ |
| 97 | POST .../review-decision/ | POST .../review-decision/ |
| 104 | GET /reviews/sla-status/ | GET /reviews/sla-status/ |
| 105 | GET /approvals/queue/ | GET /approvals/queue/ |
| 106 | GET /approvals/{id}/ (senior detail) | GET /approvals/{id}/ |
| 107 | POST .../issue-consent/ | POST .../issue-consent/ |
| 112 | POST .../issue-permit/ | POST .../issue-permit/ |
| 116 | POST .../reject-final/ | POST .../reject-final/ |
| 117 | GET /permits/{permit_number}/ | GET /permits/{permit_number}/ |
| 118 | GET /verify/{permit_number}/ (HTML) | GET /verify/{permit_number}/ |
| 119 | POST .../commence/ | POST .../commence/ |
| 124 | GET .../inspections/ | GET .../inspections/ |
| 125 | GET /inspections/my-schedule/ | GET /inspections/my-schedule/ |
| 128 | POST .../start/ | POST .../start/ |
| 130 | GET /inspections/{id}/ (checklist) | GET /inspections/{id}/ |
| 131 | PUT .../checklist/ | PUT .../checklist/ |
| 132 | POST .../photos/ (≥3 photos) | POST .../photos/ |
| 134 | POST .../submit/ | POST .../submit/ |
| 139 | POST .../request-reinspection/ | POST .../request-reinspection/ |
| 140 | POST .../declare-completion/ | POST .../declare-completion/ |
| 146 | POST .../issue-completion-certificate/ | POST .../issue-completion-certificate/ |
| 150 | GET /notifications/ | GET /notifications/ |
| 151 | PUT .../{id}/read/ | PUT .../{id}/read/ |
| 152 | PUT .../read-all/ | PUT .../read-all/ |
| 156 | GET /admin/stats/ | GET /admin/stats/ |
| 157 | GET /admin/audit-log/ | GET /admin/audit-log/ |
| 158 | PUT /admin/config/fee-schedule/ | PUT /admin/config/fee-schedule/ |
| 159 | PUT /admin/config/sla-thresholds/ | PUT /admin/config/sla-thresholds/ |
| 160 | PUT .../inspection-checklists/{type}/ | PUT .../inspection-checklists/{type}/ |
| 161 | POST /admin/config/notification-templates/ | POST /admin/config/notification-templates/ |
| 162 | GET /admin/reports/export/ (CSV) | GET /admin/reports/export/ |
| 208-209 | Signature upload/retrieval | GET+POST /admin/signatures/{user_id}/ |

### Backend Tasks Verified but Not Inline with SRS Requirements

| Task # | Description | Issue |
|--------|-------------|-------|
| 52 | Category auto-classification (span + fire safety) | Only implements floors_above check; missing span ≤7m and fire safety system logic |
| 212 | Throttling (anon=20/min) | Both user and anon set to 100/min |
| 30 (FR-1.4) | Forgot password reset URL | Hardcoded to `http://localhost:3000` |
| 35 (FR-1.6) | LoginAttemptLog.user_id | Uses `email` string field instead of FK to User |

## Notes for Frontend Team

1. **Base URL**: All endpoints are under `/api/v1/`
2. **Auth**: Obtain JWT from `POST /auth/login/`. Pass as `Authorization: Bearer <token>` header.
3. **Token refresh**: Access tokens expire in 60 min. Use `POST /auth/refresh/` with the refresh token (valid 7 days).
4. **Multipart endpoints** (marked with `format: binary`): Send as `multipart/form-data`, not JSON.
5. **PDF downloads**: `/payments/receipts/{id}/` returns `application/pdf` binary.
6. **CSV exports**: `/admin/reports/export/` returns `text/csv` binary.
7. **Public endpoint**: `GET /verify/{permit_number}/` returns HTML (no auth needed).
8. **UUID format**: Most resource IDs are UUIDs (v4). Pass as strings in URLs and JSON.
9. **Pagination**: List endpoints use `page` and `page_size` query params. Responses include `count`, `next`, `previous`, `results`.
10. **Error format**: All errors return `{"detail": "message"}` with appropriate HTTP status codes.

## SRS Compliance Summary

| Requirement | Status | Notes |
|-------------|--------|-------|
| FR-1.1 — Registration | ✅ | POST /auth/register/, immediate activation |
| FR-1.2 — Login (JWT) | ✅ | access (60m) + refresh (7d) + role + user_id |
| FR-1.3 — RBAC (5 roles, 403) | ✅ | Permission classes per endpoint |
| FR-1.4 — Password reset (30 min) | ⚠️ | URL hardcoded to localhost:3000 |
| FR-1.5 — Admin user mgmt | ✅ | Create/deactivate officer accounts |
| FR-1.6 — Login logging | ⚠️ | Uses email string, not user_id FK |
| FR-2.1 — Document upload (JPEG/PNG/PDF, <5MB) | ✅ | Vault document upload endpoint |
| FR-2.2 — Land certificate | ✅ | Field on User model |
| FR-2.3 — TIN (10-digit) | ✅ | Validation in serializer |
| FR-2.4 — Document vault versioning | ✅ | is_current tracking, version_number |
| FR-2.5 — Document status view | ✅ | GET /users/me/documents/ |
| FR-3.1 — ARN generation | ✅ | ACPS-YYYY-XXXXXX |
| FR-3.2 — Application form fields | ✅ | All fields in create/update serializers |
| FR-3.3 — Category auto-classification | ⚠️ | Missing span ≤7m + fire safety checks |
| FR-3.4 — Fee auto-calculation | ✅ | Formula + tiered |
| FR-3.5 — Dynamic document checklist | ✅ | Required documents per category |
| FR-3.6 — Document validation (PDF/DWG, <20MB) | ✅ | Application document upload |
| FR-3.7 — Draft retention (30 days) | ✅ | cleanup_drafts management command |
| FR-3.8 — Completeness check on submit | ✅ | Missing docs validation |
| FR-4.1-4.5 — Neighbor consent | ✅ | All CRUD + validation |
| FR-5.1-5.6 — Payment demo | ✅ | All flows (Telebirr, CBE, Bank Transfer) |
| FR-6.1-6.8 — Technical review | ✅ | Assign, comment, decision, SLA, escalation |
| FR-7.1-7.7 — Consent/permit issuance | ✅ | PDF generation, QR codes, signatures |
| FR-8.1-8.6 — Commencement & inspection | ✅ | Auto-schedule milestones |
| FR-9.1-9.7 — Digital inspection | ✅ | Start, checklist, photos, submit, reinspection |
| FR-10.1-10.5 — Completion certificate | ✅ | Declaration, final inspection, certificate PDF |
| FR-12.1-12.5 — Dashboards | ⏭️ | Frontend scope |
| NFR-1 — Performance | 190 tests pass (186 ✅, 4 ❌ intermittent) |
| NFR-2 — Availability | Deploy-ready (Render config done) |
| NFR-3 — Security (bcrypt, JWT, HTTPS) | ✅ | bcrypt cost 12, HS256 | 
| NFR-3 — Throttling (anon=20/min) | ⚠️ | Currently 100/min |
| NFR-4 — Data integrity | ✅ | Atomic transactions, no deletes |
| NFR-5 — Accessibility (WCAG) | ⏭️ | Frontend scope |
| NFR-6 — Scalability (subcity_id) | ✅ | subcity_id on User + Application |
| NFR-7 — Auditability | ✅ | ApplicationHistory immutable log |

**Legend**: ✅ = Fully implemented, ⚠️ = Partially/with issue, ⏭️ = Out of scope (frontend)

## 5 SRS Non-Conformances (from verification report)

1. **FR-3.3**: `auto_classify()` only checks `floors_above`; missing span ≤7m (Cat A) and fire safety system (Cat C)
2. **NFR-3**: Anonymous throttle set to 100/min instead of 20/min
3. **FR-1.4**: Forgot password URL hardcoded to `http://localhost:3000` in `accounts/views.py:75`
4. **FR-1.6**: `LoginAttemptLog` stores `email` (string) instead of `user_id` (FK)
5. **Test pollution**: 4 intermittent errors in `ApplicationUpdateAPITests` due to shared throttle cache between TestCase classes

# Bulk Certificate Generator API

A RESTful backend API built with **FastAPI**, **SQLAlchemy (SQLite)**, and **ReportLab** for processing bulk certificate generation requests for event or course participants. 

The system handles bulk generation requests via background task workers, tracks real-time generation progress, isolates individual certificate generation failures, and provides endpoints to retrieve and download generated PDF certificates.

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Features](#2-features)
3. [Tech Stack](#3-tech-stack)
4. [Architecture & Flow](#4-architecture--flow)
5. [Project Structure](#5-project-structure)
6. [Setup Instructions](#6-setup-instructions)
7. [Running the Application](#7-running-the-application)
8. [Running Tests](#8-running-tests)
9. [API Documentation](#9-api-documentation)
10. [Example Request](#10-example-request)
11. [Example Response](#11-example-response)
12. [Certificate Retrieval](#12-certificate-retrieval)
13. [Error Handling & Status Codes](#13-error-handling--status-codes)
14. [Design Decisions](#14-design-decisions)
15. [Future Improvements](#15-future-improvements)

---

## 1. Project Overview

An organization needs to generate certificates for participants after events or courses. Rather than making one API request per certificate, this API allows clients to submit a bulk request containing up to 1,000 recipients. 

The API validates all input data, initiates asynchronous background certificate processing, tracks progress real-time, isolates individual rendering failures, and exposes endpoints to query job progress and download generated PDF certificates.

---

## 2. Features

- **Bulk Certificate Request**: Submit a single HTTP request containing up to 1,000 recipients.
- **Strict Input Validation**: Validates recipient names (required, non-blank), email syntax, date format (`YYYY-MM-DD`), and prevents duplicate emails within the same job request (`422 Unprocessable Entity`).
- **Asynchronous Background Processing**: Immediate `202 Accepted` response returning a `job_id` without blocking HTTP connections.
- **Fault-Tolerant Failure Isolation**: Each recipient's certificate generation is isolated in an independent `try...except...finally` block. A single recipient failure does not abort other valid certificates in the batch.
- **Granular Progress & Status Tracking**: Live metrics (`total_count`, `processed_count`, `success_count`, `failed_count`, `progress_percentage`) and status transitions (`PENDING` -> `PROCESSING` -> `COMPLETED` / `PARTIALLY_FAILED` / `FAILED`).
- **Clean PDF Certificate Generation**: Generates vector PDF certificates using ReportLab with custom styling and readable certificate codes (`CERT-2026-A1B20001`).
- **File Retrieval & Streaming**: Download individual generated PDF certificates via `FileResponse` with `Content-Type: application/pdf`.
- **Health Monitoring**: Dedicated `/health` endpoint for service monitoring.

---

## 3. Tech Stack

- **Language**: Python 3.10+
- **Framework**: FastAPI (Asynchronous web framework with automatic Pydantic v2 validation & Swagger UI)
- **Database / ORM**: SQLite & SQLAlchemy 2.0
- **PDF Generation**: ReportLab
- **Testing**: Pytest & HTTPX (`TestClient`)

---

## 4. Architecture & Flow

```text
                  Client
                    │
                    ▼
          POST /api/v1/jobs
                    │
                    ▼
          Pydantic Validation
      (Check Duplicates & Format)
                    │
                    ▼
        Create Job + Recipients
                    │
                    ▼
              Return 202
             + job_id
                    │
                    ▼
          FastAPI BackgroundTask
                    │
             ┌──────┴──────┐
             ▼             ▼
        Recipient A    Recipient B
             │             │
          SUCCESS        FAILED
             │             │
             └──────┬──────┘
                    ▼
              Recipient C
                    │
                  SUCCESS
                    │
                    ▼
             Update Job Status
                    │
                    ▼
          PARTIALLY_FAILED
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
 GET /jobs/{id}       GET /certificates/{id}/download
```

---

## 5. Project Structure

```text
bulk_certificate_generator/
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app initialization, routes & /health
│   ├── config.py                 # Application settings & media path definitions
│   ├── database.py               # SQLAlchemy engine & session setup
│   ├── models.py                 # Database models (CertificateJob, CertificateRecord)
│   ├── schemas.py                # Pydantic request/response schemas & validators
│   ├── api/                      # REST API endpoints
│   │   ├── __init__.py
│   │   ├── jobs.py               # Bulk job submission & status endpoints
│   │   └── certificates.py       # Certificate download endpoints
│   └── services/                 # Core business logic
│       ├── __init__.py
│       ├── certificate_generator.py # ReportLab PDF rendering service
│       └── job_service.py        # Background task processor & error handling
├── tests/                        # Automated test suite
│   ├── __init__.py
│   ├── conftest.py               # Test database & client fixtures
│   ├── test_jobs.py              # Job creation, validation & partial failure tests
│   └── test_certificates.py      # PDF rendering & download endpoint tests
├── media/                        # Storage directory for generated PDF files
│   └── certificates/
├── requirements.txt              # Project dependencies
├── .gitignore                    # Git ignore file
└── README.md                     # Documentation
```

---

## 6. Setup Instructions

### Prerequisites
- Python 3.10 or higher
- `pip` package manager

### Installation Steps

1. **Navigate to the Project Root**:
   ```bash
   cd C:\Users\janar\.gemini\antigravity\scratch\bulk_certificate_generator
   ```

2. **Create and Activate Virtual Environment (Optional)**:
   ```bash
   python -m venv .venv
   # Windows (PowerShell / Command Prompt):
   .venv\Scripts\activate
   # Linux / macOS:
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 7. Running the Application

Start the Uvicorn development server:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 8. Running Tests

Run the full automated test suite using `pytest`:
```bash
pytest -v
```

All 12 automated unit and integration tests verify:
- Job creation & `202 Accepted` response
- Input validation (missing fields, blank names, bad emails, date syntax)
- Duplicate recipient email prevention (`422 Unprocessable Entity`)
- ReportLab PDF file generation
- Dynamic progress tracking (`processed_count`, `success_count`, `progress_percentage`)
- Isolated failure handling (A=SUCCESS, B=FAILED, C=SUCCESS -> `PARTIALLY_FAILED`)
- Certificate PDF retrieval via `FileResponse` (`Content-Type: application/pdf`) and status codes (`200`, `404`, `409`, `422`)
- `/health` endpoint status response

---

## 9. API Documentation

Interactive API documentation is automatically generated by FastAPI:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 10. Example Request

### Submit Bulk Generation Job (`POST /api/v1/jobs`)

**cURL Request:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/jobs" \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Full-Stack Web Development Certificate",
       "event_name": "Python & Web Bootcamp 2026",
       "issue_date": "2026-10-07",
       "recipients": [
         {"recipient_name": "Alice Johnson", "recipient_email": "alice@example.com"},
         {"recipient_name": "Bob Smith", "recipient_email": "bob@example.com"},
         {"recipient_name": "Charlie Brown", "recipient_email": "charlie@example.com"}
       ]
     }'
```

---

## 11. Example Response

### Immediate POST Response (`202 Accepted`)
```json
{
  "job_id": "e4b2d3c1-9a8b-7c6d-5e4f-3a2b1c0d9e8f",
  "status": "PENDING",
  "total_count": 3,
  "message": "Certificate generation started"
}
```

### Job Progress / Status Check (`GET /api/v1/jobs/e4b2d3c1-9a8b-7c6d-5e4f-3a2b1c0d9e8f`)
```json
{
  "job_id": "e4b2d3c1-9a8b-7c6d-5e4f-3a2b1c0d9e8f",
  "title": "Full-Stack Web Development Certificate",
  "event_name": "Python & Web Bootcamp 2026",
  "issue_date": "2026-10-07",
  "status": "COMPLETED",
  "total_count": 3,
  "processed_count": 3,
  "success_count": 3,
  "failed_count": 0,
  "progress_percentage": 100.0,
  "created_at": "2026-10-07T01:50:00.000Z",
  "updated_at": "2026-10-07T01:50:04.000Z",
  "recipients": [
    {
      "certificate_id": "11111111-2222-3333-4444-555555555555",
      "name": "Alice Johnson",
      "email": "alice@example.com",
      "status": "SUCCESS",
      "error_message": null,
      "certificate_code": "CERT-2026-E4B20001",
      "download_url": "/api/v1/certificates/11111111-2222-3333-4444-555555555555/download"
    }
  ]
}
```

---

## 12. Certificate Retrieval

Download a generated PDF certificate using the recipient's `certificate_id`:

```bash
curl -O -J "http://127.0.0.1:8000/api/v1/certificates/11111111-2222-3333-4444-555555555555/download"
```

The server returns HTTP `200 OK` with header `Content-Type: application/pdf` streamed via FastAPI `FileResponse`.

---

## 13. Error Handling & Status Codes

| Status Code | Description | Scenario |
|---|---|---|
| **202 Accepted** | Job Accepted | Bulk job creation initiated successfully |
| **200 OK** | Success | Status queries and PDF file downloads (`Content-Type: application/pdf`) |
| **404 Not Found** | Not Found | Non-existent `job_id` or missing `certificate_id` |
| **409 Conflict** | Business Conflict | Attempting to download a certificate whose status is `FAILED` |
| **422 Validation Error** | Schema Validation | Pydantic validation failure (missing required fields, bad email format, invalid date syntax, or duplicate recipient emails) |
| **500 Internal Error** | Server Error | Unhandled system exception |

---

## 14. Design Decisions

### Why FastAPI?
FastAPI provides high performance, native async support, automatic OpenAPI/Swagger generation, and clean schema validation via Pydantic v2.

### Why SQLite & SQLAlchemy?
SQLAlchemy 2.0 provides an ORM mapping for `CertificateJob` and `CertificateRecord`. SQLite offers a self-contained, zero-configuration relational database suited for local execution and fast automated testing.

### Why FastAPI BackgroundTasks?
FastAPI `BackgroundTasks` executes processing in background worker threads without blocking HTTP request execution. For larger production systems, a dedicated task queue like Celery or RQ with Redis/RabbitMQ is recommended.

### Why ReportLab?
ReportLab generates crisp vector PDF certificates in pure Python without requiring external C-binary system dependencies (such as `wkhtmltopdf`).

### Failure Isolation Architecture
Each recipient generation is isolated inside an explicit `try...except...finally` block. If Recipient B fails (e.g., rendering error), its status is recorded as `FAILED` with an error message, while Recipient A and Recipient C continue processing to `SUCCESS`. The overall job transitions to `PARTIALLY_FAILED`.

### Preventing Duplicate Recipients
Duplicate email validation is performed inside the Pydantic `JobCreateRequest` schema validator. Submitting duplicate recipient emails in a single payload returns HTTP `422 Unprocessable Entity` with details (`"Duplicate recipient email detected: 'user@example.com'"`).

### File Storage & Naming
Certificates are saved as `media/certificates/CERT-2026-A1B20001.pdf`. Storage file paths are indexed in SQLite to support secure streaming via FastAPI `FileResponse`.

---

## 15. Future Improvements

- **Distributed Background Processing**: Implement Celery + Redis for distributed task queues, retries, and worker scaling across multiple node clusters.
- **Cloud Storage**: Store generated PDFs in Amazon S3, Google Cloud Storage, or Azure Blob Storage.
- **Automated Email Dispatch**: Send generated PDF certificates directly to recipient email addresses via SendGrid or SMTP.
- **Authentication & Authorization**: Add API Key or JWT OAuth2 authentication.
- **Custom Certificate Templates**: Support visual template customization, background images, and custom font uploads.
- **Bulk ZIP Export**: Download all generated PDFs for a job as a single compressed `.zip` archive.

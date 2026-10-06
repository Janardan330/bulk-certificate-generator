import pytest
from app.services.job_service import JobService
from app.models import JobStatus, RecordStatus

def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

def test_create_job(client, db):
    payload = {
        "title": "Python Developer Certification",
        "event_name": "Advanced Python Bootcamp 2026",
        "issue_date": "2026-10-07",
        "recipients": [
            {"recipient_name": "Alice Johnson", "recipient_email": "alice@example.com"},
            {"recipient_name": "Bob Smith", "recipient_email": "bob@example.com"}
        ]
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == JobStatus.PENDING
    assert data["total_count"] == 2
    assert data["message"] == "Certificate generation started"

    job_id = data["job_id"]
    JobService.process_job_background(job_id, db=db)

    status_res = client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["status"] == JobStatus.COMPLETED
    assert status_data["processed_count"] == 2
    assert status_data["success_count"] == 2
    assert status_data["failed_count"] == 0
    assert status_data["progress_percentage"] == 100.0
    assert len(status_data["recipients"]) == 2

def test_input_validation(client):
    # Missing title
    payload = {
        "event_name": "Tech Conference",
        "recipients": [{"recipient_name": "John", "recipient_email": "john@example.com"}]
    }
    res = client.post("/api/v1/jobs", json=payload)
    assert res.status_code == 422

def test_empty_recipient_list(client):
    payload = {
        "title": "Event 2026",
        "event_name": "Tech Conference",
        "recipients": []
    }
    res = client.post("/api/v1/jobs", json=payload)
    assert res.status_code == 422

def test_invalid_email(client):
    payload = {
        "title": "Event 2026",
        "event_name": "Tech Conference",
        "recipients": [{"recipient_name": "John", "recipient_email": "not-an-email"}]
    }
    res = client.post("/api/v1/jobs", json=payload)
    assert res.status_code == 422

def test_duplicate_recipient(client):
    payload = {
        "title": "Python Workshop",
        "event_name": "Dev Summit 2026",
        "recipients": [
            {"recipient_name": "John", "recipient_email": "john@example.com"},
            {"recipient_name": "John Duplicate", "recipient_email": "john@example.com"}
        ]
    }
    res = client.post("/api/v1/jobs", json=payload)
    assert res.status_code == 422
    assert "Duplicate recipient email detected" in str(res.json())

def test_job_not_found(client):
    res = client.get("/api/v1/jobs/non-existent-uuid-999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Job not found"

def test_individual_certificate_failure_and_partial_status(client, db):
    """
    Verifies that Recipient B's failure does not stop Recipient A, C, and D from succeeding.
    Confirms processed=4, success=3, failed=1, status=PARTIALLY_FAILED.
    """
    payload = {
        "title": "Data Science Masterclass",
        "event_name": "AI Summit 2026",
        "issue_date": "2026-10-07",
        "recipients": [
            {"recipient_name": "Recipient A", "recipient_email": "a@example.com", "fail_trigger": False},
            {"recipient_name": "Recipient B", "recipient_email": "b@example.com", "fail_trigger": True},
            {"recipient_name": "Recipient C", "recipient_email": "c@example.com", "fail_trigger": False},
            {"recipient_name": "Recipient D", "recipient_email": "d@example.com", "fail_trigger": False}
        ]
    }
    create_res = client.post("/api/v1/jobs", json=payload)
    assert create_res.status_code == 202
    job_id = create_res.json()["job_id"]

    # Run background worker
    JobService.process_job_background(job_id, db=db)

    # Check job status API
    res = client.get(f"/api/v1/jobs/{job_id}")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == JobStatus.PARTIALLY_FAILED
    assert data["total_count"] == 4
    assert data["processed_count"] == 4
    assert data["success_count"] == 3
    assert data["failed_count"] == 1
    assert data["progress_percentage"] == 100.0

    recipients = data["recipients"]
    rec_a = next(r for r in recipients if r["name"] == "Recipient A")
    rec_b = next(r for r in recipients if r["name"] == "Recipient B")
    rec_c = next(r for r in recipients if r["name"] == "Recipient C")
    rec_d = next(r for r in recipients if r["name"] == "Recipient D")

    assert rec_a["status"] == RecordStatus.SUCCESS
    assert rec_a["download_url"] is not None

    assert rec_b["status"] == RecordStatus.FAILED
    assert rec_b["download_url"] is None
    assert "Simulated certificate generation failure" in rec_b["error_message"]

    assert rec_c["status"] == RecordStatus.SUCCESS
    assert rec_c["download_url"] is not None

    assert rec_d["status"] == RecordStatus.SUCCESS
    assert rec_d["download_url"] is not None

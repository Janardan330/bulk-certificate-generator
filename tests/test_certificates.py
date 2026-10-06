import os
import pytest
from app.services.certificate_generator import CertificateGeneratorService
from app.services.job_service import JobService

def test_certificate_generation(tmp_path):
    output_pdf = str(tmp_path / "CERT-2026-000001.pdf")
    res_path = CertificateGeneratorService.generate_pdf(
        recipient_name="John Doe",
        title="Web Development Bootcamp",
        event_name="Full Stack Engineering",
        issue_date="2026-10-07",
        certificate_code="CERT-2026-000001",
        output_path=output_pdf
    )
    assert os.path.exists(res_path)
    assert os.path.getsize(res_path) > 0

def test_download_certificate(client, db):
    payload = {
        "title": "Cloud Computing Workshop",
        "event_name": "DevOps 2026",
        "recipients": [{"recipient_name": "Dave Miller", "recipient_email": "dave@example.com"}]
    }
    create_res = client.post("/api/v1/jobs", json=payload)
    job_id = create_res.json()["job_id"]

    # Process job
    JobService.process_job_background(job_id, db=db)

    # Fetch job status to retrieve recipient certificate_id
    status_res = client.get(f"/api/v1/jobs/{job_id}")
    record = status_res.json()["recipients"][0]
    rec_id = record["certificate_id"]

    # Download certificate PDF
    download_res = client.get(f"/api/v1/certificates/{rec_id}/download")
    assert download_res.status_code == 200
    assert download_res.headers["content-type"] == "application/pdf"
    assert download_res.content.startswith(b"%PDF")

def test_certificate_not_found(client):
    res = client.get("/api/v1/certificates/invalid-uuid-999/download")
    assert res.status_code == 404
    assert res.json()["detail"] == "Certificate not found"

def test_failed_certificate_download_conflict(client, db):
    payload = {
        "title": "Security Workshop",
        "event_name": "CyberSec 2026",
        "recipients": [{"recipient_name": "Eve Hacking", "recipient_email": "eve@example.com", "fail_trigger": True}]
    }
    create_res = client.post("/api/v1/jobs", json=payload)
    job_id = create_res.json()["job_id"]

    JobService.process_job_background(job_id, db=db)

    status_res = client.get(f"/api/v1/jobs/{job_id}")
    record = status_res.json()["recipients"][0]
    rec_id = record["certificate_id"]

    # Attempt download of failed certificate
    download_res = client.get(f"/api/v1/certificates/{rec_id}/download")
    assert download_res.status_code == 409
    assert download_res.json()["detail"] == "Certificate was not generated because processing failed"

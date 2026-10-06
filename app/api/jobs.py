from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import CertificateJob
from app.schemas import (
    JobCreateRequest,
    JobCreateResponse,
    JobStatusResponse,
    RecipientStatusResponse
)
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Certificate Jobs"])

@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
@router.post("/", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED, include_in_schema=False)
def create_job(
    job_in: JobCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Submit a bulk certificate generation job.
    Validates recipient input data, creates database records, and initiates background generation.
    Returns HTTP 202 Accepted.
    """
    job = JobService.create_job(db=db, job_in=job_in)
    background_tasks.add_task(JobService.process_job_background, job.id)
    
    return JobCreateResponse(
        job_id=job.id,
        status=job.status,
        total_count=job.total_count,
        message="Certificate generation started"
    )

@router.get("", response_model=List[JobStatusResponse])
@router.get("/", response_model=List[JobStatusResponse], include_in_schema=False)
def list_jobs(db: Session = Depends(get_db)):
    """
    List all certificate generation jobs.
    """
    jobs = db.query(CertificateJob).order_by(CertificateJob.created_at.desc()).all()
    results = []
    for j in jobs:
        progress_pct = (j.processed_count / j.total_count * 100.0) if j.total_count > 0 else 0.0
        results.append(JobStatusResponse(
            job_id=j.id,
            title=j.title,
            event_name=j.event_name,
            issue_date=j.issue_date,
            status=j.status,
            total_count=j.total_count,
            processed_count=j.processed_count,
            success_count=j.success_count,
            failed_count=j.failed_count,
            progress_percentage=round(progress_pct, 2),
            created_at=j.created_at,
            updated_at=j.updated_at,
            recipients=[]
        ))
    return results

@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Retrieve job status, progress percentage, and recipient certificate details.
    Returns HTTP 404 if job_id does not exist.
    """
    job = db.query(CertificateJob).filter(CertificateJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    progress_pct = (job.processed_count / job.total_count * 100.0) if job.total_count > 0 else 0.0

    recipient_responses = []
    for rec in job.records:
        download_url = f"/api/v1/certificates/{rec.id}/download" if rec.file_path else None
        rec_dto = RecipientStatusResponse(
            certificate_id=rec.id,
            name=rec.recipient_name,
            email=rec.recipient_email,
            status=rec.status,
            error_message=rec.error_message,
            certificate_code=rec.certificate_code,
            download_url=download_url
        )
        recipient_responses.append(rec_dto)

    return JobStatusResponse(
        job_id=job.id,
        title=job.title,
        event_name=job.event_name,
        issue_date=job.issue_date,
        status=job.status,
        total_count=job.total_count,
        processed_count=job.processed_count,
        success_count=job.success_count,
        failed_count=job.failed_count,
        progress_percentage=round(progress_pct, 2),
        created_at=job.created_at,
        updated_at=job.updated_at,
        recipients=recipient_responses
    )

import os
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal
from app.models import CertificateJob, CertificateRecord, JobStatus, RecordStatus
from app.schemas import JobCreateRequest
from app.services.certificate_generator import CertificateGeneratorService

logger = logging.getLogger(__name__)

class JobService:
    @staticmethod
    def create_job(db: Session, job_in: JobCreateRequest) -> CertificateJob:
        """
        Creates a new CertificateJob and associated CertificateRecords.
        Generates readable certificate codes (e.g., CERT-2026-000001).
        """
        job = CertificateJob(
            title=job_in.title,
            event_name=job_in.event_name,
            issue_date=job_in.issue_date,
            status=JobStatus.PENDING,
            total_count=len(job_in.recipients),
            processed_count=0,
            success_count=0,
            failed_count=0
        )
        db.add(job)
        db.flush() # Populate job.id

        # Determine year for certificate code
        year = datetime.utcnow().year
        if job_in.issue_date and len(job_in.issue_date) >= 4 and job_in.issue_date[:4].isdigit():
            year = job_in.issue_date[:4]

        # Short job identifier to guarantee unique code across multiple jobs
        job_hex = job.id.replace("-", "")[:4].upper()

        for idx, recipient in enumerate(job_in.recipients, start=1):
            cert_code = f"CERT-{year}-{job_hex}{idx:04d}"
            rec = CertificateRecord(
                job_id=job.id,
                recipient_name=recipient.recipient_name,
                recipient_email=recipient.recipient_email,
                status=RecordStatus.PENDING,
                certificate_code=cert_code,
                error_message="Fail trigger requested for testing" if recipient.fail_trigger else None
            )
            db.add(rec)

        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def process_job_background(job_id: str, db: Optional[Session] = None):
        """
        Processes each recipient certificate in an isolated try-except block.
        Ensures individual failures do not stop other valid certificates.
        """
        close_db_at_end = False
        if db is None:
            db = SessionLocal()
            close_db_at_end = True

        try:
            job = db.query(CertificateJob).filter(CertificateJob.id == job_id).first()
            if not job:
                logger.error(f"Job {job_id} not found for background processing.")
                return

            job.status = JobStatus.PROCESSING
            db.commit()

            records = db.query(CertificateRecord).filter(CertificateRecord.job_id == job_id).all()
            
            for record in records:
                try:
                    output_filename = f"{record.certificate_code}.pdf"
                    output_path = os.path.join(settings.MEDIA_DIR, output_filename)
                    
                    fail_trigger = record.error_message == "Fail trigger requested for testing"
                    if fail_trigger:
                        record.error_message = None

                    CertificateGeneratorService.generate_pdf(
                        recipient_name=record.recipient_name,
                        title=job.title,
                        event_name=job.event_name,
                        issue_date=job.issue_date or "",
                        certificate_code=record.certificate_code,
                        output_path=output_path,
                        fail_trigger=fail_trigger
                    )

                    record.status = RecordStatus.SUCCESS
                    record.file_path = output_path
                    record.error_message = None
                    job.success_count += 1

                except Exception as e:
                    logger.warning(f"Failed to generate certificate for record {record.id}: {e}")
                    record.status = RecordStatus.FAILED
                    record.error_message = str(e)
                    job.failed_count += 1

                finally:
                    job.processed_count += 1
                    db.commit()

            # Dynamic job status resolution
            if job.failed_count == 0:
                job.status = JobStatus.COMPLETED
            elif job.success_count > 0:
                job.status = JobStatus.PARTIALLY_FAILED
            else:
                job.status = JobStatus.FAILED

            db.commit()
            logger.info(f"Job {job_id} finished with status {job.status}")

        except Exception as global_err:
            logger.error(f"Fatal error in background job {job_id}: {global_err}")
        finally:
            if close_db_at_end:
                db.close()

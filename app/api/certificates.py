import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import CertificateRecord, RecordStatus

router = APIRouter(prefix="/certificates", tags=["Certificates"])

@router.get("/{certificate_id}/download")
def download_certificate(certificate_id: str, db: Session = Depends(get_db)):
    """
    Download a single generated certificate PDF by certificate ID.
    Returns HTTP 404 if not found, or HTTP 409 Conflict if generation failed.
    """
    record = db.query(CertificateRecord).filter(CertificateRecord.id == certificate_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found"
        )

    if record.status != RecordStatus.SUCCESS or not record.file_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Certificate was not generated because processing failed"
        )

    if not os.path.exists(record.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate file missing on storage"
        )

    filename = f"{record.certificate_code}.pdf"
    
    return FileResponse(
        path=record.file_path,
        filename=filename,
        media_type="application/pdf"
    )

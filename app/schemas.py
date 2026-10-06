from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

class RecipientInput(BaseModel):
    recipient_name: str = Field(..., min_length=1, description="Recipient full name")
    recipient_email: EmailStr = Field(..., description="Valid recipient email address")
    fail_trigger: bool = Field(False, description="Internal flag to simulate certificate generation failure for testing")

    @field_validator("recipient_name")
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Recipient name cannot be blank")
        return v.strip()

class JobCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, description="Job / Certificate Title")
    event_name: str = Field(..., min_length=1, description="Name of the course or event")
    issue_date: Optional[str] = Field(None, description="Date of issuance e.g. '2026-10-07'")
    recipients: List[RecipientInput] = Field(..., min_length=1, max_length=1000, description="List of recipients (1 to 1000)")

    @field_validator("title", "event_name")
    def field_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be blank")
        return v.strip()

    @field_validator("issue_date")
    def validate_issue_date(cls, v: Optional[str]) -> Optional[str]:
        if v:
            try:
                # Validate date string format YYYY-MM-DD or standard parseable date
                date.fromisoformat(v)
            except ValueError:
                raise ValueError("issue_date must be a valid date format (YYYY-MM-DD)")
        return v

    @field_validator("recipients")
    def check_duplicate_emails(cls, recipients: List[RecipientInput]) -> List[RecipientInput]:
        seen_emails = set()
        for r in recipients:
            email_lower = r.recipient_email.lower()
            if email_lower in seen_emails:
                raise ValueError(f"Duplicate recipient email detected: '{r.recipient_email}'")
            seen_emails.add(email_lower)
        return recipients

class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    total_count: int
    message: str = "Certificate generation started"

    model_config = ConfigDict(from_attributes=True)

class RecipientStatusResponse(BaseModel):
    certificate_id: str
    name: str
    email: str
    status: str
    error_message: Optional[str] = None
    certificate_code: str
    download_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class JobStatusResponse(BaseModel):
    job_id: str
    title: str
    event_name: str
    issue_date: Optional[str] = None
    status: str
    total_count: int
    processed_count: int
    success_count: int
    failed_count: int
    progress_percentage: float
    created_at: datetime
    updated_at: datetime
    recipients: List[RecipientStatusResponse] = []

    model_config = ConfigDict(from_attributes=True)

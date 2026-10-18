from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import Job, User
from ..serializers import job_out

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}")
def read_job(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job or job.company_id != user.company_id:
        raise HTTPException(404, "المهمة مش موجودة")
    return job_out(job)

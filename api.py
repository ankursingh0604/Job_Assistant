import os
import uuid
import json
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from sqlalchemy.orm import Session

load_dotenv()

from database import init_db, get_db, Application
from parsers import parse_resume_pdf, parse_job_description
from job_agent import agent

init_db()

app = FastAPI(
    title="AI Job Application Assistant",
    description="Analyzes job fit, scores matches, and writes tailored cover letters",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# In-memory store for pending sessions waiting for human approval
# key = thread_id, value = intermediate state
pending_sessions = {}

# ── Response Models ───────────────────────────────────────────────────────────

class IntermediateResponse(BaseModel):
    thread_id: str
    company: str
    role: str
    match_score: float
    match_reasons: str
    skills_to_highlight: str
    status: str = "awaiting_approval"

class ApprovalRequest(BaseModel):
    thread_id: str
    human_feedback: Optional[str] = ""

class FinalResponse(BaseModel):
    application_id: int
    company: str
    role: str
    match_score: float
    match_reasons: str
    skills_to_highlight: str
    cover_letter: str

class ApplicationUpdate(BaseModel):
    status: str
    notes: str = ""

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "AI Job Application Assistant API", "status": "running"}


@app.post("/analyze", response_model=IntermediateResponse)
async def analyze_application(
    resume: UploadFile = File(...),
    jd_text: str = Form(...),
    company_name: str = Form(...),
):
    """
    Step 1 — Run agent until HITL interrupt.
    Returns match score and skills to highlight.
    Waits for human approval before writing cover letter.
    """
    resume_bytes = await resume.read()

    # Parse resume and JD
    resume_text, resume_data = parse_resume_pdf(resume_bytes)
    jd_data = parse_job_description(jd_text)

    role_title = jd_data.get("role_title", "Software Engineer")
    company = company_name or jd_data.get("company", "Unknown Company")

    # Unique thread ID for this session
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Run agent — will pause before write_cover_letter node
    agent.invoke(
        {
            "resume_text": resume_text,
            "resume_data": resume_data,
            "jd_text": jd_text,
            "jd_data": jd_data,
            "company_name": company,
            "role_title": role_title,
            "match_score": None,
            "match_reasons": None,
            "skills_to_highlight": None,
            "cover_letter": None,
            "company_research": None,
            "human_feedback": None,
            "messages": []
        },
        config=config
    )

    # Get state after interrupt
    state = agent.get_state(config)
    values = state.values

    # Store session for approval step
    pending_sessions[thread_id] = {
        "config": config,
        "company": company,
        "role": role_title,
        "resume_data": resume_data,
        "jd_data": jd_data,
        "match_score": values.get("match_score", 0),
        "match_reasons": values.get("match_reasons", ""),
        "skills_to_highlight": values.get("skills_to_highlight", ""),
    }

    return IntermediateResponse(
        thread_id=thread_id,
        company=company,
        role=role_title,
        match_score=values.get("match_score", 0),
        match_reasons=values.get("match_reasons", ""),
        skills_to_highlight=values.get("skills_to_highlight", ""),
        status="awaiting_approval"
    )


@app.post("/approve", response_model=FinalResponse)
async def approve_and_generate(
    request: ApprovalRequest,
    db: Session = Depends(get_db)
):
    """
    Step 2 — Human approves and optionally adds feedback.
    Agent resumes and writes the cover letter.
    """
    thread_id = request.thread_id

    if thread_id not in pending_sessions:
        raise HTTPException(status_code=404, detail="Session not found or already completed")

    session = pending_sessions[thread_id]
    config = session["config"]

    # Inject human feedback into state before resuming
    agent.update_state(
        config,
        {"human_feedback": request.human_feedback or ""},
        as_node="skills_highlight"
    )

    # Resume agent — writes cover letter now
    result = agent.invoke(None, config=config)

    # Save to database
    application = Application(
        company=session["company"],
        role=session["role"],
        jd_text=session.get("jd_data", {}).get("role_title", ""),
        match_score=result.get("match_score", 0),
        match_reasons=result.get("match_reasons", ""),
        cover_letter=result.get("cover_letter", ""),
        skills_to_highlight=result.get("skills_to_highlight", ""),
        status="pending"
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    # Clean up session
    del pending_sessions[thread_id]

    return FinalResponse(
        application_id=application.id,
        company=session["company"],
        role=session["role"],
        match_score=result.get("match_score", 0),
        match_reasons=result.get("match_reasons", ""),
        skills_to_highlight=result.get("skills_to_highlight", ""),
        cover_letter=result.get("cover_letter", "")
    )


@app.get("/applications")
def get_applications(db: Session = Depends(get_db)):
    applications = db.query(Application).order_by(Application.applied_at.desc()).all()
    return [
        {
            "id": a.id,
            "company": a.company,
            "role": a.role,
            "match_score": a.match_score,
            "status": a.status,
            "applied_at": a.applied_at.isoformat() if a.applied_at else None,
            "notes": a.notes
        }
        for a in applications
    ]


@app.get("/applications/{application_id}")
def get_application(application_id: int, db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return {
        "id": application.id,
        "company": application.company,
        "role": application.role,
        "match_score": application.match_score,
        "match_reasons": application.match_reasons,
        "cover_letter": application.cover_letter,
        "skills_to_highlight": application.skills_to_highlight,
        "status": application.status,
        "applied_at": application.applied_at.isoformat() if application.applied_at else None,
        "notes": application.notes
    }


@app.patch("/applications/{application_id}")
def update_application(
    application_id: int,
    update: ApplicationUpdate,
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    valid_statuses = ["pending", "applied", "interview", "rejected", "offer"]
    if update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid_statuses}")
    application.status = update.status
    if update.notes:
        application.notes = update.notes
    db.commit()
    return {"message": "Updated successfully", "status": update.status}


@app.delete("/applications/{application_id}")
def delete_application(application_id: int, db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    db.delete(application)
    db.commit()
    return {"message": "Deleted successfully"}

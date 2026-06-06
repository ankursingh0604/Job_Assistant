import os
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.utils.function_calling import convert_to_openai_function
from langchain_core.output_parsers.openai_functions import JsonOutputFunctionsParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
import tempfile

# Pydantic schemas 

class Education(BaseModel):
    """Educational qualification"""
    degree: str = Field(description="Degree name e.g. B.Tech, MBA")
    institution: str = Field(description="University or college name")
    year: Optional[str] = Field(description="Year of completion or expected year")
    gpa: Optional[str] = Field(description="GPA or percentage if mentioned")

class Project(BaseModel):
    """A project from the resume"""
    name: str = Field(description="Project name")
    description: str = Field(description="What the project does")
    tech_stack: List[str] = Field(description="Technologies used")
    link: Optional[str] = Field(description="GitHub or live link if mentioned")

class ResumeData(BaseModel):
    """Extract all structured information from a resume"""
    name: str = Field(description="Candidate full name")
    email: Optional[str] = Field(description="Email address")
    phone: Optional[str] = Field(description="Phone number")
    location: Optional[str] = Field(description="City or country")
    summary: Optional[str] = Field(description="Professional summary or objective")
    skills: List[str] = Field(description="All technical skills mentioned")
    education: List[Education] = Field(description="Educational qualifications")
    projects: List[Project] = Field(description="All projects mentioned")
    experience: Optional[List[str]] = Field(description="Work experience entries if any")
    certifications: Optional[List[str]] = Field(description="Certifications or courses completed")

class JDRequirements(BaseModel):
    """Extract structured requirements from a job description"""
    role_title: str = Field(description="Job title")
    company: Optional[str] = Field(description="Company name if mentioned")
    required_skills: List[str] = Field(description="Must-have technical skills")
    preferred_skills: Optional[List[str]] = Field(description="Nice-to-have skills")
    experience_required: Optional[str] = Field(description="Years of experience required")
    responsibilities: Optional[List[str]] = Field(description="Key job responsibilities")  # ← add Optional
    location: Optional[str] = Field(description="Job location or remote policy")

# Parser functions 

def get_llm():
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
        temperature=0
    )

def parse_resume_pdf(file_bytes: bytes) -> tuple[str, ResumeData]:
    """Load PDF bytes → extract text → parse into ResumeData"""
    # Write to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    # Extract text
    loader = PyPDFLoader(tmp_path)
    docs = loader.load()
    resume_text = "\n\n".join(d.page_content for d in docs)

    # Parse with extraction chain
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extract all information from this resume carefully. "
                   "If a field is not present use null or empty list."),
        ("human", "{resume_text}")
    ])

    model = get_llm()
    chain = (
        prompt
        | model.bind(
            functions=[convert_to_openai_function(ResumeData)],
            function_call={"name": "ResumeData"}
        )
        | JsonOutputFunctionsParser()
    )

    parsed = chain.invoke({"resume_text": resume_text})
    return resume_text, parsed

def parse_job_description(jd_text: str) -> JDRequirements:
    """Parse job description text into structured JDRequirements"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extract all requirements from this job description carefully."),
        ("human", "{jd_text}")
    ])

    model = get_llm()
    chain = (
        prompt
        | model.bind(
            functions=[convert_to_openai_function(JDRequirements)],
            function_call={"name": "JDRequirements"}
        )
        | JsonOutputFunctionsParser()
    )

    return chain.invoke({"jd_text": jd_text})

import os
from typing import TypedDict, Annotated, Optional
import operator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AnyMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.tools.tavily_search import TavilySearchResults

# State 

class ApplicationState(TypedDict):
    # Inputs
    resume_text: str
    resume_data: dict
    jd_text: str
    jd_data: dict
    company_name: str
    role_title: str

    # Computed
    match_score: Optional[float]
    match_reasons: Optional[str]
    skills_to_highlight: Optional[str]
    cover_letter: Optional[str]
    company_research: Optional[str]

    # Human in the loop — user adds context before cover letter is written
    human_feedback: Optional[str]

    # Messages
    messages: Annotated[list[AnyMessage], operator.add]

# LLM 

def get_llm(temperature=0.3):
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
        temperature=temperature
    )

# Nodes

def research_company_node(state: ApplicationState) -> dict:
    """Search for company information using Tavily"""
    print(f"Researching {state['company_name']}...")
    search = TavilySearchResults(max_results=3)
    try:
        results = search.invoke(
            f"{state['company_name']} company culture tech stack engineering team 2026"
        )
        research = "\n\n".join(
            f"Source: {r['url']}\n{r['content']}"
            for r in results
        )
    except Exception:
        research = f"Could not find specific information about {state['company_name']}."
    return {"company_research": research}


def score_match_node(state: ApplicationState) -> dict:
    """Score how well the resume matches the JD"""
    print("Scoring match...")
    resume_data = state["resume_data"]
    jd_data = state["jd_data"]

    candidate_skills = [s.lower() for s in resume_data.get("skills", [])]
    candidate_projects = [
        skill.lower()
        for p in resume_data.get("projects", [])
        for skill in p.get("tech_stack", [])
    ]
    all_candidate_skills = list(set(candidate_skills + candidate_projects))
    required_skills = [s.lower() for s in jd_data.get("required_skills", [])]
    preferred_skills = [s.lower() for s in jd_data.get("preferred_skills", []) or []]

    def skills_match(jd_skill, candidate_skills):
        jd_skill = jd_skill.lower().strip()
        for cs in candidate_skills:
            cs = cs.lower().strip()
            if jd_skill == cs:
                return True
            if jd_skill in cs or cs in jd_skill:
                return True
            aliases = {
                "ml": ["machine learning"],
                "ai": ["artificial intelligence"],
                "nlp": ["natural language processing"],
                "llm": ["langchain", "langgraph", "groq", "llama"],
                "vector db": ["faiss", "pinecone", "weaviate", "chroma"],
                "embeddings": ["huggingface", "sentence-transformers"],
                "api": ["fastapi", "rest api", "flask"],
                "mlops": ["langsmith", "docker", "deployment"],
                "automation": ["langgraph", "agents", "langchain"],
                "deep learning": ["pytorch", "tensorflow", "huggingface"],
            }
            for alias_key, alias_vals in aliases.items():
                if jd_skill == alias_key and any(v in cs for v in alias_vals):
                    return True
                if jd_skill in alias_vals and alias_key in cs:
                    return True
        return False

    required_matches = [s for s in required_skills if skills_match(s, all_candidate_skills)]
    preferred_matches = [s for s in preferred_skills if skills_match(s, all_candidate_skills)]

    required_score = (len(required_matches) / len(required_skills) * 70) if required_skills else 35
    preferred_score = (len(preferred_matches) / len(preferred_skills) * 20) if preferred_skills else 10
    project_bonus = min(len(resume_data.get("projects", [])) * 2.5, 10)
    match_score = min(round(required_score + preferred_score + project_bonus, 1), 100)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert recruiter. Analyze the candidate's fit for this role. "
                   "Be specific and honest. Format as bullet points."),
        ("human", (
            f"Resume Skills: {', '.join(all_candidate_skills[:20])}\n"
            f"Projects: {[p.get('name') for p in resume_data.get('projects', [])]}\n\n"
            f"Required Skills: {', '.join(required_skills)}\n"
            f"Preferred Skills: {', '.join(preferred_skills)}\n"
            f"Role: {state['role_title']} at {state['company_name']}\n\n"
            f"Match Score: {match_score}%\n\n"
            "Provide:\n"
            "✅ Strengths (what matches well)\n"
            "⚠️ Gaps (what's missing)\n"
            "💡 Recommendation (should they apply?)"
        ))
    ])

    llm = get_llm(temperature=0.1)
    chain = prompt | llm | StrOutputParser()
    reasons = chain.invoke({})

    return {"match_score": match_score, "match_reasons": reasons}


def skills_highlight_node(state: ApplicationState) -> dict:
    """Identify which skills and projects to highlight"""
    print("Identifying skills to highlight...")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a career coach helping a candidate tailor their application. "
                   "Be specific and actionable."),
        ("human", (
            f"Candidate Skills: {state['resume_data'].get('skills', [])}\n"
            f"Candidate Projects: {[p.get('name') + ': ' + p.get('description', '') for p in state['resume_data'].get('projects', [])]}\n\n"
            f"Job Role: {state['role_title']} at {state['company_name']}\n"
            f"Required Skills: {state['jd_data'].get('required_skills', [])}\n"
            f"Key Responsibilities: {state['jd_data'].get('responsibilities', [])[:3] if state['jd_data'].get('responsibilities') else []}\n\n"
            "List exactly:\n"
            "1. Top 5 skills to emphasize in this application\n"
            "2. Which 2-3 projects are most relevant and why\n"
            "3. One sentence positioning statement for this specific role"
        ))
    ])

    llm = get_llm(temperature=0.2)
    chain = prompt | llm | StrOutputParser()
    highlights = chain.invoke({})
    return {"skills_to_highlight": highlights}


def write_cover_letter_node(state: ApplicationState) -> dict:
    """Write a tailored cover letter using human feedback if provided"""
    print("Writing cover letter...")

    resume_data = state["resume_data"]
    company_research = state.get("company_research", "")
    human_feedback = state.get("human_feedback", "") or ""

    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an expert cover letter writer. Write professional, "
            "compelling cover letters that get interviews. "
            "Never use generic phrases like 'I am writing to express my interest'. "
            "Start with a strong hook. Be specific. Keep it under 300 words."
        )),
        ("human", (
            f"Candidate Name: {resume_data.get('name', 'Candidate')}\n"
            f"Candidate Skills: {', '.join(resume_data.get('skills', [])[:10])}\n"
            f"Key Projects: {[p.get('name') for p in resume_data.get('projects', [])]}\n"
            f"Education: {resume_data.get('education', [{}])[0].get('degree', '')} from "
            f"{resume_data.get('education', [{}])[0].get('institution', '')}\n\n"
            f"Role: {state['role_title']}\n"
            f"Company: {state['company_name']}\n"
            f"Key Requirements: {', '.join(state['jd_data'].get('required_skills', [])[:6])}\n"
            f"Responsibilities: {state['jd_data'].get('responsibilities', [])[:2] if state['jd_data'].get('responsibilities') else []}\n\n"
            f"Company Research: {company_research[:500] if company_research else 'N/A'}\n\n"
            f"Skills to Highlight: {state.get('skills_to_highlight', '')[:300]}\n\n"
            f"Additional instructions from candidate: {human_feedback if human_feedback else 'None'}\n\n"
            "Write a tailored, professional cover letter:"
        ))
    ])

    llm = get_llm(temperature=0.7)
    chain = prompt | llm | StrOutputParser()
    cover_letter = chain.invoke({})
    return {"cover_letter": cover_letter}


# Build Graph 

def build_agent():
    graph = StateGraph(ApplicationState)

    graph.add_node("research_company", research_company_node)
    graph.add_node("score_match", score_match_node)
    graph.add_node("skills_highlight", skills_highlight_node)
    graph.add_node("write_cover_letter", write_cover_letter_node)

    graph.set_entry_point("research_company")

    graph.add_edge("research_company", "score_match")
    graph.add_edge("score_match", "skills_highlight")
    graph.add_edge("skills_highlight", "write_cover_letter")
    graph.add_edge("write_cover_letter", END)

    memory = MemorySaver()

    # HUMAN IN THE LOOP — pause before writing cover letter
    return graph.compile(
        checkpointer=memory,
        interrupt_before=["write_cover_letter"]
    )


agent = build_agent()

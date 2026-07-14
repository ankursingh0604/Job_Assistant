# 🎯 AI Job Application Assistant

An intelligent agent that analyzes your fit for any job, scores your match, researches the company, and writes a tailored cover letter — all in one click.

Built with LangGraph multi-node agent, LangChain extraction, FastAPI, and LangSmith tracing.

🚀 [Live Demo](https://jobassistant-gvx3nckjd46vercbcttdgg.streamlit.app/) &nbsp;|&nbsp; 🔌 [API](https://jobassistant-production-efe1.up.railway.app)

---

## What it does

Upload your resume + paste any job description and the agent:

1. **Researches the company** — searches the web for culture, tech stack, recent news
2. **Scores your match** — analyzes skill overlap between your resume and the JD
3. **Pauses for human review** — shows you the analysis before writing anything ← Human in the Loop
4. **Takes your instructions** — you guide the cover letter before it's written
5. **Writes a cover letter** — tailored to the specific role, company, and your instructions
6. **Tracks applications** — SQLite database with status tracking (pending → applied → interview → offer)

---

## Demo

![AI Job Application Assistant Demo]

---

## Architecture

```
Resume PDF + Job Description
         ↓
   LangGraph Agent
         ↓
┌─────────────────────────────────────┐
│ Node 1: Research Company            │ ← Tavily web search
│ Node 2: Score Match                 │ ← Extraction + LLM analysis
│ Node 3: Skills Highlight            │ ← LLM with context
│         ↓ PAUSE (Human in the Loop) │ ← Human reviews + adds instructions
│ Node 4: Write Cover Letter          │ ← LLM with human guidance
└─────────────────────────────────────┘
         ↓
   FastAPI Backend (Railway)
         ↓
   SQLite Application Tracker
         ↓
   Streamlit Frontend (Streamlit Cloud)
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Agent Framework | LangGraph |
| LLM | LLaMA 3.3 70B via Groq API |
| Resume Parsing | LangChain Extraction + Pydantic |
| Company Research | Tavily Search API |
| Backend | FastAPI + SQLAlchemy |
| Database | SQLite |
| Frontend | Streamlit |
| Backend Deployment | Railway |
| Frontend Deployment | Streamlit Cloud |

---

## What makes this different from a basic LLM app

- **LangGraph agent** — multi-node pipeline where each step builds context for the next
- **Human in the Loop** — agent pauses mid-execution using `interrupt_before`, waits for your input, then resumes with your guidance injected into the state
- **Extraction over plain prompting** — uses structured Pydantic schemas to parse resumes, not just free-form text
- **Company research** — agent searches the web so cover letters reference real company context
- **Production ready** — FastAPI backend, Railway deployment, application tracker with full CRUD.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/analyze` | Run agent until HITL pause — returns match score |
| POST | `/approve` | Resume agent with human feedback — returns cover letter |
| GET | `/applications` | Get all tracked applications |
| GET | `/applications/{id}` | Get one application with full details |
| PATCH | `/applications/{id}` | Update status and notes |
| DELETE | `/applications/{id}` | Delete an application |

---

## Setup

1. Clone the repo
```bash
git clone https://github.com/ankursingh0604/Job_Assistant
cd Job_Assistant
```

2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Create `.env` file
```
GROQ_API_KEY=your-groq-api-key
TAVILY_API_KEY=your-tavily-api-key
LANGCHAIN_TRACING_V2=false
```

5. Run the API
```bash
uvicorn api:app --reload
```

6. Run the frontend (new terminal)
```bash
streamlit run app.py
```

---

## Project Structure

```
Job_Assistant/
├── agents/
│   └── job_agent.py      ← LangGraph agent with 4 nodes + HITL
├── utils/
│   ├── parsers.py         ← Resume + JD extraction with Pydantic
│   └── database.py        ← SQLite models with SQLAlchemy
├── api.py                 ← FastAPI backend with two-step HITL endpoints
├── app.py                 ← Streamlit frontend
├── requirements.txt
└── Dockerfile
```

---

## Author

**Ankur Singh** — CS undergrad building RAG systems and AI agents

[GitHub](https://github.com/ankursingh0604) • [X](https://x.com/ankur_builds)

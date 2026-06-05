import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="AI Job Assistant",
    page_icon="🎯",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
    * { font-family: 'DM Sans', sans-serif; }
    h1, h2, h3 { font-family: 'Syne', sans-serif !important; }
    .block-container { padding: 2rem 3rem; max-width: 1200px; }
    .hero {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1025 50%, #0f1a1a 100%);
        border: 1px solid #2a2a3e;
        border-radius: 16px;
        padding: 2.5rem;
        margin-bottom: 2rem;
    }
    .hero-title { font-family: 'Syne', sans-serif !important; font-size: 2.4rem; font-weight: 800; color: #f0f0f8; margin: 0 0 0.5rem 0; }
    .hero-sub { font-size: 1rem; color: #8888aa; margin: 0; font-weight: 300; }
    .score-card { background: linear-gradient(135deg, #0f1a0f, #0a1410); border: 1px solid #1a3a2a; border-radius: 12px; padding: 1.5rem; text-align: center; }
    .score-number { font-family: 'Syne', sans-serif; font-size: 3.5rem; font-weight: 800; line-height: 1; margin-bottom: 0.25rem; }
    .score-label { font-size: 0.8rem; color: #668866; text-transform: uppercase; letter-spacing: 0.1em; }
    .result-section { background: #0f0f1a; border: 1px solid #1e1e2e; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; }
    .result-title { font-family: 'Syne', sans-serif; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 1rem; color: #8888cc; }
    .hitl-box { background: #0f1a0f; border: 1px solid #2a5a2a; border-radius: 12px; padding: 1.5rem; margin: 1rem 0; }
    .hitl-title { font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 700; color: #44ee88; margin-bottom: 0.5rem; }
    .hitl-sub { font-size: 0.85rem; color: #668866; margin-bottom: 1rem; }
    .cover-letter-box { background: #080810; border: 1px solid #1e1e2e; border-radius: 10px; padding: 1.5rem; font-size: 0.9rem; line-height: 1.8; color: #c0c0d8; white-space: pre-wrap; }
    div[data-testid="stButton"] > button { background: linear-gradient(135deg, #6b3faa, #3f6baa); color: white; border: none; border-radius: 8px; font-family: 'Syne', sans-serif; font-weight: 600; padding: 0.6rem 1.5rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <div class="hero-title">🎯 AI Job Application Assistant</div>
    <p class="hero-sub">Upload your resume · Paste a job description · Review your match · Get a tailored cover letter</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🔍 Analyze New Application", "📋 My Applications"])

# Tab 1 

with tab1:

    # Input form (shown when no pending session) 
    if "pending_session" not in st.session_state:

        col1, col2 = st.columns([1, 1], gap="large")

        with col1:
            st.markdown("#### 📄 Your Resume")
            resume_file = st.file_uploader("Upload Resume PDF", type=["pdf"], label_visibility="collapsed")
            if resume_file:
                st.success(f"✅ {resume_file.name}")

            st.markdown("#### 🏢 Company")
            company_name = st.text_input("Company name", placeholder="e.g. Anthropic, OpenAI, Stripe...", label_visibility="collapsed")

        with col2:
            st.markdown("#### 📋 Job Description")
            jd_text = st.text_area("Paste the full job description", height=220, placeholder="Paste the complete job description here...", label_visibility="collapsed")

        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("🚀 Analyze My Fit", use_container_width=True)

        if analyze_btn:
            if not resume_file:
                st.error("Please upload your resume PDF")
            elif not jd_text.strip():
                st.error("Please paste the job description")
            elif not company_name.strip():
                st.error("Please enter the company name")
            else:
                with st.spinner("🤖 Researching company, scoring match, identifying highlights... (30-60 seconds)"):
                    try:
                        response = requests.post(
                            f"{API_URL}/analyze",
                            files={"resume": (resume_file.name, resume_file.getvalue(), "application/pdf")},
                            data={"jd_text": jd_text, "company_name": company_name},
                            timeout=120
                        )
                        if response.status_code == 200:
                            st.session_state["pending_session"] = response.json()
                            st.rerun()
                        else:
                            st.error(f"Error: {response.text}")
                    except requests.exceptions.ConnectionError:
                        st.error("Cannot connect to API. Run: `uvicorn api:app --reload`")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

    #  Human in the loop review 
    else:
        session = st.session_state["pending_session"]
        score = session["match_score"]
        score_color = "#44ee88" if score >= 70 else "#ccaa44" if score >= 50 else "#cc4444"
        score_emoji = "🟢" if score >= 70 else "🟡" if score >= 50 else "🔴"

        st.markdown(f"### Review: **{session['role']}** at **{session['company']}**")

        # Score + match analysis
        col_score, col_match = st.columns([1, 3])
        with col_score:
            st.markdown(f"""
            <div class="score-card">
                <div class="score-number" style="color:{score_color}">{score}%</div>
                <div class="score-label">Match Score {score_emoji}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_match:
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            st.markdown('<div class="result-title">📊 Match Analysis</div>', unsafe_allow_html=True)
            st.markdown(session["match_reasons"])
            st.markdown('</div>', unsafe_allow_html=True)

        # Skills to highlight
        st.markdown('<div class="result-section">', unsafe_allow_html=True)
        st.markdown('<div class="result-title">⭐ Skills & Projects to Highlight</div>', unsafe_allow_html=True)
        st.markdown(session["skills_to_highlight"])
        st.markdown('</div>', unsafe_allow_html=True)

        # Human in the loop box
        st.markdown("""
        <div class="hitl-box">
            <div class="hitl-title">✋ Your Turn — Guide the Cover Letter</div>
            <div class="hitl-sub">Review the analysis above. Add any specific instructions before the AI writes your cover letter.</div>
        </div>
        """, unsafe_allow_html=True)

        human_feedback = st.text_area(
            "Instructions for cover letter (optional)",
            placeholder='e.g. "Emphasize my LangGraph experience", "Keep it under 200 words", "Mention I am open to relocation"...',
            height=100,
            label_visibility="collapsed"
        )

        col_approve, col_restart = st.columns([3, 1])

        with col_approve:
            approve_btn = st.button("✅ Generate Cover Letter", use_container_width=True)

        with col_restart:
            if st.button("🔄 Start Over", use_container_width=True):
                del st.session_state["pending_session"]
                if "final_result" in st.session_state:
                    del st.session_state["final_result"]
                st.rerun()

        if approve_btn:
            with st.spinner("✍️ Writing your tailored cover letter..."):
                try:
                    response = requests.post(
                        f"{API_URL}/approve",
                        json={
                            "thread_id": session["thread_id"],
                            "human_feedback": human_feedback
                        },
                        timeout=60
                    )
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state["final_result"] = result
                        del st.session_state["pending_session"]
                        st.rerun()
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    # Final results with cover letter 
    if "final_result" in st.session_state:
        result = st.session_state["final_result"]
        score = result["match_score"]
        score_color = "#44ee88" if score >= 70 else "#ccaa44" if score >= 50 else "#cc4444"

        st.markdown("---")
        st.markdown(f"### ✅ Complete: **{result['role']}** at **{result['company']}**")

        col_score, col_match = st.columns([1, 3])
        with col_score:
            st.markdown(f"""
            <div class="score-card">
                <div class="score-number" style="color:{score_color}">{score}%</div>
                <div class="score-label">Match Score</div>
            </div>
            """, unsafe_allow_html=True)
        with col_match:
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            st.markdown('<div class="result-title">📊 Match Analysis</div>', unsafe_allow_html=True)
            st.markdown(result["match_reasons"])
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="result-section">', unsafe_allow_html=True)
        st.markdown('<div class="result-title">✍️ Your Tailored Cover Letter</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="cover-letter-box">{result["cover_letter"]}</div>', unsafe_allow_html=True)

        col_dl, col_new = st.columns([1, 1])
        with col_dl:
            st.download_button(
                "⬇️ Download Cover Letter",
                data=result["cover_letter"],
                file_name=f"cover_letter_{result['company'].lower().replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True
            )
        with col_new:
            if st.button("🔍 Analyze Another Job", use_container_width=True):
                del st.session_state["final_result"]
                st.rerun()

        st.markdown(f"*Saved as application #{result['application_id']}*")

# Applications tracker 

with tab2:
    st.markdown("#### 📋 Application Tracker")

    if st.button("🔄 Refresh"):
        st.rerun()

    try:
        response = requests.get(f"{API_URL}/applications", timeout=10)
        if response.status_code == 200:
            applications = response.json()

            if not applications:
                st.info("No applications tracked yet. Analyze your first job above!")
            else:
                total = len(applications)
                offers = sum(1 for a in applications if a["status"] == "offer")
                interviews = sum(1 for a in applications if a["status"] == "interview")
                applied = sum(1 for a in applications if a["status"] == "applied")
                avg_score = sum(a["match_score"] or 0 for a in applications) / total

                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Total", total)
                c2.metric("Applied", applied)
                c3.metric("Interviews", interviews)
                c4.metric("Offers 🎉", offers)
                c5.metric("Avg Score", f"{avg_score:.0f}%")

                st.markdown("---")

                for app in applications:
                    score = app["match_score"] or 0
                    status = app["status"]
                    with st.expander(f"**{app['company']}** — {app['role']} | Score: {score:.0f}% | {status.upper()}"):
                        col_l, col_r = st.columns([2, 1])
                        with col_l:
                            if app.get("notes"):
                                st.markdown(f"**Notes:** {app['notes']}")
                            st.markdown(f"*Added: {app['applied_at'][:10] if app['applied_at'] else 'N/A'}*")
                        with col_r:
                            new_status = st.selectbox(
                                "Update status",
                                ["pending", "applied", "interview", "rejected", "offer"],
                                index=["pending", "applied", "interview", "rejected", "offer"].index(status),
                                key=f"status_{app['id']}"
                            )
                            notes_input = st.text_input("Notes", key=f"notes_{app['id']}")
                            if st.button("Update", key=f"update_{app['id']}"):
                                update_resp = requests.patch(
                                    f"{API_URL}/applications/{app['id']}",
                                    json={"status": new_status, "notes": notes_input},
                                    timeout=10
                                )
                                if update_resp.status_code == 200:
                                    st.success("Updated!")
                                    st.rerun()

    except requests.exceptions.ConnectionError:
        st.warning("Start the API server: `uvicorn api:app --reload`")
    except Exception as e:
        st.error(f"Error: {str(e)}")

import os
import textwrap
from datetime import datetime

import streamlit as st
from google import genai


# ----------------------------- App configuration -----------------------------
st.set_page_config(
    page_title="AI Learning Roadmap Generator",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

MODEL_NAME = "gemini-3.8-flash"


# ----------------------------- Gemini helpers --------------------------------
def get_api_key():
    """Read the Gemini key from Streamlit secrets or a local environment variable."""
    try:
        secret_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        secret_key = ""

    return secret_key or os.getenv("GEMINI_API_KEY", "")


@st.cache_resource(show_spinner=False)
def get_gemini_client(api_key: str):
    """Create and cache the Gemini client for this API key."""
    return genai.Client(api_key=api_key)


def build_prompt(field: str, level: str, duration: str, hours_per_week: int, goal: str) -> str:
    """Create a focused prompt that asks Gemini for a practical, time-aware roadmap."""
    goal_text = goal.strip() if goal.strip() else "Build practical, job-relevant skills."
    return textwrap.dedent(
        f"""
        You are an experienced learning-path designer and technical mentor.

        Create a realistic, actionable learning roadmap using these learner details:
        - Learning field: {field}
        - Current skill level: {level}
        - Available learning time: {duration}
        - Study commitment: {hours_per_week} hours per week
        - Learner's goal: {goal_text}

        Requirements:
        1. Start with a short assessment of what this learner's level means.
        2. Break the available time into sequential phases. Make the phase durations
           add up to the requested total duration as closely as possible.
        3. For every phase, include: topics to learn, why they matter, practical
           exercises, and a small deliverable or project.
        4. Include a weekly study routine that fits the stated hours per week.
        5. Include 3 portfolio projects in increasing difficulty, with a short
           description of what each project should demonstrate.
        6. Include recommended learning resources by name and type (official docs,
           books, courses, or practice platforms). Do not invent URLs. If unsure of
           a specific resource, name the resource category instead.
        7. Include checkpoints to measure progress and common mistakes to avoid.
        8. Finish with a concise "Your first 7 days" action plan.
        9. Be specific to the selected field; avoid generic filler and avoid claiming
           that mastery or employment is guaranteed.
        10. Use clear Markdown headings, tables only when they improve readability,
            and concise explanations suitable for a motivated learner.

        If the selected duration is very short, prioritize fundamentals and a small
        achievable outcome rather than pretending the learner can master the field.
        """
    ).strip()


def generate_roadmap(client, prompt: str) -> str:
    """Call Gemini and return the generated roadmap text."""
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )
    roadmap = getattr(response, "text", None)
    if not roadmap or not roadmap.strip():
        raise ValueError("Gemini returned an empty response. Please try again.")
    return roadmap.strip()


# ----------------------------- User interface --------------------------------
st.title("🧭 AI Learning Roadmap Generator")
st.caption("Turn a learning goal into a practical, step-by-step plan powered by Gemini.")

with st.sidebar:
    st.subheader("About this app")
    st.write(
        "Choose a field, your current level, and the time you can commit. "
        "Gemini will create a structured roadmap with phases, projects, and checkpoints."
    )
    st.divider()
    st.caption(f"Model: `{MODEL_NAME}`")
    st.caption("Keep your API key private. Never paste it into the source code.")

api_key = get_api_key()

if not api_key:
    st.warning(
        "Gemini API key not found. Add `GEMINI_API_KEY` to "
        "`.streamlit/secrets.toml` or your environment variables before generating a roadmap."
    )

with st.form("roadmap_form"):
    st.subheader("Tell us what you want to learn")

    field = st.text_input(
        "Learning field or skill",
        placeholder="e.g. Data Science, Python, UI/UX Design, Cybersecurity",
        max_chars=100,
    )

    col1, col2 = st.columns(2)
    with col1:
        level = st.selectbox(
            "Current skill level",
            ["Beginner", "Intermediate", "Advanced"],
            help="Choose the level that best describes your current knowledge.",
        )
    with col2:
        duration = st.selectbox(
            "Time available to learn",
            ["2 weeks", "1 month", "2 months", "3 months", "6 months", "12 months"],
            index=3,
        )

    col3, col4 = st.columns(2)
    with col3:
        hours_per_week = st.slider(
            "Study hours per week",
            min_value=2,
            max_value=40,
            value=10,
            step=1,
        )
    with col4:
        goal = st.text_input(
            "Your specific goal (optional)",
            placeholder="e.g. Build a portfolio and qualify for internships",
            max_chars=200,
        )

    submitted = st.form_submit_button("✨ Generate my roadmap", type="primary", use_container_width=True)

if submitted:
    if not field.strip():
        st.error("Please enter a learning field or skill.")
    elif not api_key:
        st.error("Add your Gemini API key first, then run the app again.")
    else:
        prompt = build_prompt(field.strip(), level, duration, hours_per_week, goal)
        try:
            client = get_gemini_client(api_key)
            with st.spinner("Building your personalized learning roadmap..."):
                result = generate_roadmap(client, prompt)

            st.session_state["roadmap_result"] = result
            st.session_state["roadmap_details"] = {
                "field": field.strip(),
                "level": level,
                "duration": duration,
                "hours_per_week": hours_per_week,
            }
        except Exception as exc:
            # Keep the detailed exception in server logs, but show a safe, useful message.
            print(f"Roadmap generation failed: {type(exc).__name__}: {exc}")
            error_name = type(exc).__name__
            if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                st.error(
                    "Gemini's request limit has been reached. Wait a little and try again, "
                    "or check your API quota and billing in Google AI Studio."
                )
            elif "503" in str(exc) or "UNAVAILABLE" in str(exc):
                st.error(
                    "Gemini is temporarily busy or unavailable. Wait a few moments and retry."
                )
            elif "API_KEY" in str(exc).upper() or "PERMISSION_DENIED" in str(exc).upper():
                st.error(
                    "Gemini rejected the API key. Check that it is correct and that the "
                    "Gemini API is enabled for the associated project."
                )
            else:
                st.error(
                    f"Roadmap generation failed ({error_name}). Check your connection, "
                    "API key, and Gemini quota, then try again."
                )

if st.session_state.get("roadmap_result"):
    st.divider()
    details = st.session_state.get("roadmap_details", {})
    st.subheader("Your learning roadmap")
    if details:
        st.caption(
            f"{details.get('field', 'Learning plan')} · {details.get('level', '')} · "
            f"{details.get('duration', '')} · {details.get('hours_per_week', '')} hours/week"
        )

    st.markdown(st.session_state["roadmap_result"])

    safe_field = "".join(
        character.lower() if character.isalnum() else "_"
        for character in details.get("field", "learning_roadmap")
    ).strip("_") or "learning_roadmap"
    file_name = f"{safe_field}_roadmap.md"

    st.download_button(
        label="⬇️ Download roadmap as Markdown",
        data=st.session_state["roadmap_result"],
        file_name=file_name,
        mime="text/markdown",
        use_container_width=True,
    )

    if st.button("Start a new roadmap"):
        st.session_state.pop("roadmap_result", None)
        st.session_state.pop("roadmap_details", None)
        st.rerun()

st.divider()
st.caption("Generated plans are learning suggestions. Adjust them to your pace and verify resources before relying on them.")

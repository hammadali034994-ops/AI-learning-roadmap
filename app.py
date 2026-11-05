"""AI Learning Roadmap Generator

A Streamlit app that uses a Gemini Flash model to build a personalised
learning roadmap from a domain, a skill level and the time available.
"""

import json
import os
import re

import streamlit as st
from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-2.5-flash"
SKILL_LEVELS = ["Beginner", "Intermediate", "Advanced"]
TIME_UNITS = ["Weeks", "Months"]

SYSTEM_INSTRUCTION = (
    "You are an expert learning coach and curriculum designer. "
    "You create realistic, well-structured, practical learning roadmaps. "
    "You always reply with valid JSON only, with no extra commentary."
)


# --------------------------------------------------------------------------
# Helper functions (no Streamlit calls, so they are easy to test)
# --------------------------------------------------------------------------
def build_prompt(domain: str, level: str, duration: int, unit: str, hours_per_week: int) -> str:
    """Build the prompt that is sent to Gemini."""
    total_weeks = duration if unit == "Weeks" else duration * 4
    total_hours = total_weeks * hours_per_week
    return f"""Create a learning roadmap with these details:

- Domain / topic: {domain}
- Current skill level: {level}
- Time available: {duration} {unit.lower()} (about {total_weeks} weeks)
- Study time per week: {hours_per_week} hours (about {total_hours} hours in total)

Rules:
1. Fit the plan into the available time. Split it into logical phases and
   make sure the phase durations add up to roughly {total_weeks} weeks.
2. Match the {level} level: skip what a {level.lower()} learner already knows.
3. Include concrete topics, a hands-on project for each phase, and
   well-known free or popular resources (official docs, courses, books).
   Do not invent URLs; give resource names only.
4. Be realistic about what can be learned in {total_hours} hours.

Return ONLY JSON with exactly this structure:
{{
  "title": "string",
  "summary": "2-3 sentence overview of the roadmap",
  "phases": [
    {{
      "name": "string",
      "duration": "e.g. Week 1-2",
      "goal": "string",
      "topics": ["string"],
      "project": "string",
      "resources": ["string"]
    }}
  ],
  "final_tips": ["string"]
}}"""


def parse_roadmap(text: str) -> dict:
    """Turn the model's text into a roadmap dict.

    Handles ```json fences and extra text around the JSON object.
    Raises ValueError if the text cannot be parsed into a valid roadmap.
    """
    if not text or not text.strip():
        raise ValueError("The model returned an empty response.")

    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("The model response was not valid JSON.")
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError("The model response was not valid JSON.") from exc

    if not isinstance(data, dict) or not isinstance(data.get("phases"), list) or not data["phases"]:
        raise ValueError("The roadmap is missing its phases.")
    return data


def _as_list(value) -> list:
    """Return value as a list of strings (tolerates a string, None or a list)."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if str(v).strip()]
    return [str(value)]


def roadmap_to_markdown(roadmap: dict) -> str:
    """Convert a roadmap dict into a Markdown document (used for download)."""
    lines = [f"# {roadmap.get('title') or 'Learning Roadmap'}", ""]
    if roadmap.get("summary"):
        lines += [str(roadmap["summary"]), ""]

    for i, phase in enumerate(roadmap.get("phases", []), start=1):
        if not isinstance(phase, dict):
            continue
        name = phase.get("name") or f"Phase {i}"
        duration = phase.get("duration")
        lines.append(f"## Phase {i}: {name}" + (f" ({duration})" if duration else ""))
        if phase.get("goal"):
            lines += ["", f"**Goal:** {phase['goal']}"]
        topics = _as_list(phase.get("topics"))
        if topics:
            lines += ["", "**Topics**"] + [f"- {t}" for t in topics]
        if phase.get("project"):
            lines += ["", f"**Project:** {phase['project']}"]
        resources = _as_list(phase.get("resources"))
        if resources:
            lines += ["", "**Resources**"] + [f"- {r}" for r in resources]
        lines.append("")

    tips = _as_list(roadmap.get("final_tips"))
    if tips:
        lines += ["## Final tips"] + [f"- {t}" for t in tips] + [""]
    return "\n".join(lines)


def generate_roadmap(api_key: str, model: str, prompt: str) -> dict:
    """Call Gemini and return the parsed roadmap dict."""
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            temperature=0.7,
        ),
    )
    return parse_roadmap(response.text)


def get_default_api_key() -> str:
    """Read the API key from Streamlit secrets or the environment."""
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:  # no secrets file present
        key = ""
    return key or os.environ.get("GEMINI_API_KEY", "")


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
def render_roadmap(roadmap: dict) -> None:
    st.header(roadmap.get("title") or "Your Learning Roadmap")
    if roadmap.get("summary"):
        st.write(roadmap["summary"])

    for i, phase in enumerate(roadmap.get("phases", []), start=1):
        if not isinstance(phase, dict):
            continue
        name = phase.get("name") or f"Phase {i}"
        duration = phase.get("duration")
        label = f"Phase {i}: {name}" + (f"  |  {duration}" if duration else "")
        with st.expander(label, expanded=(i == 1)):
            if phase.get("goal"):
                st.markdown(f"**Goal:** {phase['goal']}")
            topics = _as_list(phase.get("topics"))
            if topics:
                st.markdown("**Topics**")
                st.markdown("\n".join(f"- {t}" for t in topics))
            if phase.get("project"):
                st.markdown(f"**Project:** {phase['project']}")
            resources = _as_list(phase.get("resources"))
            if resources:
                st.markdown("**Resources**")
                st.markdown("\n".join(f"- {r}" for r in resources))

    tips = _as_list(roadmap.get("final_tips"))
    if tips:
        st.subheader("Final tips")
        st.markdown("\n".join(f"- {t}" for t in tips))


def main() -> None:
    st.set_page_config(page_title="AI Learning Roadmap Generator", page_icon="🗺️", layout="centered")
    st.title("🗺️ AI Learning Roadmap Generator")
    st.caption("Tell me what you want to learn and how much time you have. I'll build your roadmap.")

    with st.sidebar:
        st.header("Settings")
        api_key = st.text_input(
            "Gemini API key",
            type="password",
            value=get_default_api_key(),
            help="Get a free key at https://aistudio.google.com/apikey",
        )
        model = st.text_input(
            "Gemini model",
            value=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL),
            help="Any Gemini Flash model name, e.g. gemini-2.5-flash",
        )

    with st.form("roadmap_form"):
        domain = st.text_input("What do you want to learn?", placeholder="e.g. Machine Learning, Web Development, Data Analysis")
        level = st.selectbox("Your current skill level", SKILL_LEVELS)
        col1, col2, col3 = st.columns(3)
        duration = col1.number_input("Time to learn", min_value=1, max_value=52, value=8, step=1)
        unit = col2.selectbox("Unit", TIME_UNITS)
        hours = col3.number_input("Hours per week", min_value=1, max_value=80, value=6, step=1)
        submitted = st.form_submit_button("Generate roadmap", type="primary")

    if submitted:
        domain = domain.strip()
        if not domain:
            st.error("Please enter a domain or topic.")
        elif not api_key.strip():
            st.error("Please add your Gemini API key in the sidebar.")
        elif not model.strip():
            st.error("Please enter a Gemini model name in the sidebar.")
        else:
            prompt = build_prompt(domain, level, int(duration), unit, int(hours))
            try:
                with st.spinner("Building your roadmap..."):
                    roadmap = generate_roadmap(api_key.strip(), model.strip(), prompt)
                st.session_state["roadmap"] = roadmap
                st.session_state["domain"] = domain
            except ValueError as exc:
                st.session_state.pop("roadmap", None)
                st.error(f"Could not read the AI response: {exc} Please try again.")
            except Exception as exc:  # network, quota, bad key, bad model name...
                st.session_state.pop("roadmap", None)
                st.error(f"Gemini request failed: {exc}")

    roadmap = st.session_state.get("roadmap")
    if roadmap:
        render_roadmap(roadmap)
        file_name = re.sub(r"[^a-z0-9]+", "_", st.session_state.get("domain", "roadmap").lower()).strip("_") or "roadmap"
        st.download_button(
            "Download as Markdown",
            data=roadmap_to_markdown(roadmap),
            file_name=f"{file_name}_roadmap.md",
            mime="text/markdown",
        )


if __name__ == "__main__":
    main()

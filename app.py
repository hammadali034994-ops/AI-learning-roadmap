"""AI Learning Roadmap Generator

A Streamlit app that uses a Gemini Flash model to build a personalised
learning roadmap from a domain, a skill level, the time available and
(optionally) your goal, background, learning style and budget.
"""

import json
import os
import re

import streamlit as st
from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-3.8-flash"
# Tried in order if the chosen model returns "404 NOT_FOUND" (model retired/renamed).
FALLBACK_MODELS = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-flash-latest"]

SKILL_LEVELS = ["Beginner", "Intermediate", "Advanced"]
TIME_UNITS = ["Weeks", "Months", "Years"]
MAX_TOTAL_WEEKS = 260  # 5 years
MAX_TEXT_LEN = 400

GOAL_TYPES = [
    "No specific goal",
    "Get a job",
    "Switch careers",
    "Get a promotion / grow in my current job",
    "Build a project or startup",
    "Pass an exam / get certified",
    "Academic study / research",
    "Hobby / personal interest",
]
LEARNING_STYLES = ["Video courses", "Reading / documentation", "Hands-on projects", "Interactive exercises"]
BUDGET_OPTIONS = ["Free resources only", "Free + paid resources are fine"]

SYSTEM_INSTRUCTION = (
    "You are an expert learning coach and curriculum designer. "
    "You create realistic, well-structured, practical learning roadmaps. "
    "You always reply with valid JSON only, with no extra commentary."
)


# --------------------------------------------------------------------------
# Helper functions (no Streamlit calls, so they are easy to test)
# --------------------------------------------------------------------------
def to_weeks(duration: int, unit: str) -> int:
    """Convert a duration in weeks / months / years into whole weeks."""
    if unit == "Weeks":
        return int(duration)
    if unit == "Months":
        return max(1, round(duration * 4.345))
    if unit == "Years":
        return int(duration) * 52
    raise ValueError(f"Unknown time unit: {unit}")


def clean_text(value, max_len: int = MAX_TEXT_LEN) -> str:
    """Strip, collapse whitespace and limit the length of free text input."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()[:max_len]


def build_prompt(
    domain: str,
    level: str,
    duration: int,
    unit: str,
    hours_per_week: int,
    goal_type: str = "No specific goal",
    goal_text: str = "",
    known: str = "",
    styles=None,
    budget: str = BUDGET_OPTIONS[0],
    notes: str = "",
) -> str:
    """Build the prompt that is sent to Gemini."""
    total_weeks = to_weeks(duration, unit)
    total_hours = total_weeks * hours_per_week
    unit_label = unit.lower()
    if duration == 1:
        unit_label = unit_label.rstrip("s")

    if total_weeks <= 4:
        phase_hint = "3 to 4"
    elif total_weeks <= 26:
        phase_hint = "4 to 6"
    else:
        phase_hint = "6 to 8"

    optional = []
    if goal_type and goal_type != GOAL_TYPES[0]:
        optional.append(f"- Main purpose: {goal_type}")
    if clean_text(goal_text):
        optional.append(f"- Specific goal: {clean_text(goal_text)}")
    if clean_text(known):
        optional.append(f"- What the learner already knows: {clean_text(known)}")
    styles = [s for s in (styles or []) if s in LEARNING_STYLES]
    if styles:
        optional.append(f"- Preferred learning style: {', '.join(styles)}")
    optional.append(f"- Budget: {budget}")
    if clean_text(notes):
        optional.append(f"- Extra notes: {clean_text(notes)}")
    optional_block = "\n".join(optional)

    return f"""Create a learning roadmap with these details:

- Domain / topic: {clean_text(domain)}
- Current skill level: {level}
- Time available: {duration} {unit_label} (about {total_weeks} weeks)
- Study time per week: {hours_per_week} hours (about {total_hours} hours in total)
{optional_block}

Rules:
1. Fit the plan into the available time. Use {phase_hint} phases and make sure
   the phase durations add up to roughly {total_weeks} weeks.
2. Match the {level} level: skip what a learner at this level already knows.
3. Tailor the plan to the learner's purpose, background, learning style and budget
   when they are given.
4. Each phase needs concrete topics, a hands-on project, a milestone that shows the
   phase is complete, and well-known resources (official docs, courses, books).
   Do not invent URLs; give resource names only.
5. Be realistic about what can be learned in {total_hours} hours.

Return ONLY JSON with exactly this structure:
{{
  "title": "string",
  "summary": "2-3 sentence overview of the roadmap",
  "prerequisites": ["string"],
  "phases": [
    {{
      "name": "string",
      "duration": "e.g. Week 1-2",
      "goal": "string",
      "topics": ["string"],
      "project": "string",
      "milestone": "string",
      "resources": ["string"]
    }}
  ],
  "final_tips": ["string"]
}}"""


def parse_roadmap(text) -> dict:
    """Turn the model's text into a roadmap dict.

    Handles ```json fences and extra text around the JSON object.
    Raises ValueError if the text cannot be parsed into a valid roadmap.
    """
    if not text or not str(text).strip():
        raise ValueError("The model returned an empty response.")

    cleaned = str(text).strip()
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


def roadmap_to_markdown(roadmap: dict, profile: dict = None) -> str:
    """Convert a roadmap dict into a Markdown document (used for download)."""
    lines = [f"# {roadmap.get('title') or 'Learning Roadmap'}", ""]
    if profile:
        lines += [f"*{profile.get('level', '')} level | {profile.get('time_label', '')} | "
                  f"{profile.get('hours_per_week', '')} h/week*", ""]
    if roadmap.get("summary"):
        lines += [str(roadmap["summary"]), ""]

    prereqs = _as_list(roadmap.get("prerequisites"))
    if prereqs:
        lines += ["## Before you start"] + [f"- {p}" for p in prereqs] + [""]

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
            lines += ["", "**Topics**"] + [f"- [ ] {t}" for t in topics]
        if phase.get("project"):
            lines += ["", f"**Project:** {phase['project']}"]
        if phase.get("milestone"):
            lines += ["", f"**Milestone:** {phase['milestone']}"]
        resources = _as_list(phase.get("resources"))
        if resources:
            lines += ["", "**Resources**"] + [f"- {r}" for r in resources]
        lines.append("")

    tips = _as_list(roadmap.get("final_tips"))
    if tips:
        lines += ["## Final tips"] + [f"- {t}" for t in tips] + [""]
    return "\n".join(lines)


def _is_model_not_found(exc: Exception) -> bool:
    return getattr(exc, "code", None) == 404 or "NOT_FOUND" in str(exc)


def generate_roadmap(api_key: str, model: str, prompt: str) -> tuple:
    """Call Gemini and return (roadmap_dict, model_used).

    - If the chosen model is not found (retired or renamed), the fallback
      models are tried automatically.
    - If the model's answer is not valid JSON, it is asked once more.
    - Any other error is raised immediately.
    """
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        temperature=0.7,
    )
    candidates = [model] + [m for m in FALLBACK_MODELS if m != model]
    last_error = None
    for name in candidates:
        not_found = False
        parse_error = None
        for _attempt in range(2):
            try:
                response = client.models.generate_content(model=name, contents=prompt, config=config)
            except Exception as exc:
                if _is_model_not_found(exc):
                    last_error, not_found = exc, True
                    break
                raise
            try:
                text = response.text
            except Exception:
                text = None
            try:
                return parse_roadmap(text), name
            except ValueError as exc:
                parse_error = exc
        if not not_found:
            raise parse_error
    raise last_error


def get_default_api_key() -> str:
    """Read the API key from the environment or Streamlit secrets."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        return key
    try:
        return str(st.secrets.get("GEMINI_API_KEY", ""))
    except Exception:  # no secrets file present
        return ""


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
def topic_key(rid: int, phase_idx: int, topic_idx: int) -> str:
    return f"topic_{rid}_{phase_idx}_{topic_idx}"


def render_roadmap(roadmap: dict, profile: dict, rid: int) -> None:
    st.header(roadmap.get("title") or "Your Learning Roadmap")

    c1, c2, c3 = st.columns(3)
    c1.metric("Level", profile.get("level", "-"))
    c2.metric("Duration", profile.get("time_label", "-"))
    c3.metric("Total study time", f"~{profile.get('total_hours', 0)} h")

    if roadmap.get("summary"):
        st.write(roadmap["summary"])

    prereqs = _as_list(roadmap.get("prerequisites"))
    if prereqs:
        with st.expander("Before you start"):
            st.markdown("\n".join(f"- {p}" for p in prereqs))

    phases = [p for p in roadmap.get("phases", []) if isinstance(p, dict)]
    total_topics = sum(len(_as_list(p.get("topics"))) for p in phases)
    done = sum(
        1
        for i, p in enumerate(phases)
        for j, _ in enumerate(_as_list(p.get("topics")))
        if st.session_state.get(topic_key(rid, i, j), False)
    )
    if total_topics:
        st.progress(done / total_topics, text=f"Progress: {done} of {total_topics} topics completed")

    for i, phase in enumerate(phases):
        name = phase.get("name") or f"Phase {i + 1}"
        duration = phase.get("duration")
        label = f"Phase {i + 1}: {name}" + (f"  |  {duration}" if duration else "")
        with st.expander(label, expanded=(i == 0)):
            if phase.get("goal"):
                st.markdown(f"**Goal:** {phase['goal']}")
            topics = _as_list(phase.get("topics"))
            if topics:
                st.markdown("**Topics** (tick them off as you learn)")
                for j, topic in enumerate(topics):
                    st.checkbox(topic, key=topic_key(rid, i, j))
            if phase.get("project"):
                st.markdown(f"**Project:** {phase['project']}")
            if phase.get("milestone"):
                st.markdown(f"**Milestone:** {phase['milestone']}")
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
    st.title("🗺️ Learning Roadmap Generator")
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
            help="Any Gemini Flash model name, e.g. gemini-3.8-flash",
        )

    with st.form("roadmap_form"):
        domain = st.text_input(
            "What do you want to learn?",
            placeholder="e.g. Data Science, Web Development, Digital Marketing",
            max_chars=100,
        )
        level = st.selectbox("Your current skill level", SKILL_LEVELS)
        col1, col2, col3 = st.columns(3)
        duration = col1.number_input("Time to learn", min_value=1, max_value=60, value=8, step=1)
        unit = col2.selectbox("Unit", TIME_UNITS)
        hours = col3.number_input("Hours per week", min_value=1, max_value=80, value=6, step=1)

        with st.expander("Optional: personalise your roadmap"):
            goal_type = st.selectbox("Why are you learning this?", GOAL_TYPES)
            goal_text = st.text_input(
                "Your specific goal",
                placeholder="e.g. Become a junior data analyst at a bank",
                max_chars=MAX_TEXT_LEN,
            )
            known = st.text_input(
                "What do you already know?",
                placeholder="e.g. Basic Python, Excel",
                max_chars=MAX_TEXT_LEN,
            )
            styles = st.multiselect("How do you like to learn?", LEARNING_STYLES)
            budget = st.radio("Budget for resources", BUDGET_OPTIONS)
            notes = st.text_area(
                "Anything else the AI should know?",
                placeholder="e.g. I work full-time and can only study at night",
                max_chars=MAX_TEXT_LEN,
                height=80,
            )
        submitted = st.form_submit_button("Generate roadmap", type="primary")

    if submitted:
        domain = clean_text(domain, 100)
        total_weeks = to_weeks(int(duration), unit)
        if not domain:
            st.error("Please enter a domain or topic.")
        elif total_weeks > MAX_TOTAL_WEEKS:
            st.error("Please choose a time of 5 years or less.")
        elif not api_key.strip():
            st.error("Please add your Gemini API key in the sidebar.")
        elif not model.strip():
            st.error("Please enter a Gemini model name in the sidebar.")
        else:
            prompt = build_prompt(
                domain, level, int(duration), unit, int(hours),
                goal_type, goal_text, known, styles, budget, notes,
            )
            try:
                with st.spinner("Building your roadmap..."):
                    roadmap, used_model = generate_roadmap(api_key.strip(), model.strip(), prompt)
                unit_label = unit.lower().rstrip("s") if int(duration) == 1 else unit.lower()
                st.session_state["roadmap"] = roadmap
                st.session_state["domain"] = domain
                st.session_state["rid"] = st.session_state.get("rid", 0) + 1
                st.session_state["profile"] = {
                    "level": level,
                    "time_label": f"{int(duration)} {unit_label}",
                    "hours_per_week": int(hours),
                    "total_hours": total_weeks * int(hours),
                }
                if used_model != model.strip():
                    st.info(
                        f"Model '{model.strip()}' was not found, so '{used_model}' was used instead. "
                        "Update the model name in the sidebar to hide this message."
                    )
            except ValueError as exc:
                st.session_state.pop("roadmap", None)
                st.error(f"Could not read the AI response: {exc} Please try again.")
            except Exception as exc:  # network, quota, bad key, bad model name...
                st.session_state.pop("roadmap", None)
                st.error(f"Gemini request failed: {exc}")

    roadmap = st.session_state.get("roadmap")
    if roadmap:
        profile = st.session_state.get("profile", {})
        render_roadmap(roadmap, profile, st.session_state.get("rid", 0))
        file_name = re.sub(r"[^a-z0-9]+", "_", st.session_state.get("domain", "roadmap").lower()).strip("_") or "roadmap"
        st.download_button(
            "Download as Markdown",
            data=roadmap_to_markdown(roadmap, profile),
            file_name=f"{file_name}_roadmap.md",
            mime="text/markdown",
        )


if __name__ == "__main__":
    main()

import streamlit as st
from google import genai
from google.genai import types

# Configure the page
st.set_page_config(page_title="AI Learning Roadmap Generator", page_icon="🧠")

st.title("🧠 AI Learning Roadmap Generator")
st.markdown("Generate a personalized learning path based on your current level and available time.")

# Sidebar for inputs
with st.sidebar:
    st.header("Your Profile")
    skill_level = st.selectbox(
        "Current Skill Level",
        ("Beginner", "Intermediate", "Advanced")
    )
    time_commitment = st.text_input(
        "Time to Learn (e.g., '10 hours/week', '2 months', '1 hour/day')",
        "5 hours/week"
    )
    domain = st.text_input(
        "Domain of Interest",
        "Machine Learning"
    )
    generate_btn = st.button("Generate Roadmap", type="primary")

# Function to call Gemini
def generate_roadmap(level, time, domain, api_key):
    try:
        # Initialize client with the API key
        client = genai.Client(api_key=api_key)
        
        # Construct the prompt
        prompt = f"""
        You are an expert technical mentor. Create a detailed learning roadmap for someone who wants to learn {domain}.
        
        Their current level is: {level}.
        They can dedicate: {time}.
        
        The roadmap should be structured as follows:
        1. **Prerequisites**: What they need to know before starting (if any).
        2. **Core Topics**: The essential concepts they must master.
        3. **Project Ideas**: 2-3 hands-on projects to solidify learning.
        4. **Resources**: Recommended types of resources (documentation, courses, books) without specific URLs.
        5. **Timeline**: A suggested breakdown based on their time commitment.
        
        Make the tone encouraging and the structure clear using Markdown headings and bullet points.
        """
        
        # Use the Flash model as requested
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt,
        )
        
        return response.text
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Main logic
if generate_btn:
    if not domain.strip():
        st.warning("Please enter a domain to learn.")
    else:
        # Check for API key in secrets (for deployment) or environment
        api_key = st.secrets.get("GEMINI_API_KEY", None)
        
        if not api_key:
            st.error("API Key not found. Please set GEMINI_API_KEY in your Streamlit secrets.")
        else:
            with st.spinner("Crafting your personalized roadmap..."):
                roadmap = generate_roadmap(skill_level, time_commitment, domain, api_key)
                st.markdown("---")
                st.markdown(roadmap)
else:
    st.info("👈 Enter your details in the sidebar and click 'Generate Roadmap' to start.")

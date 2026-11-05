# 🗺️ AI Learning Roadmap Generator

A Streamlit app that uses Google's **Gemini Flash** model to generate a personalised learning roadmap.

You enter:
- the **domain** you want to learn (e.g. Data Science, Web Development)
- your **skill level** (Beginner / Intermediate / Advanced)
- the **time** you have (weeks, months or years) and **hours per week**
- *(optional)* your goal, background, learning style, budget and notes

You get a phased roadmap with topics, a hands-on project and resources for each phase, plus final tips. You can download it as a Markdown file.

## Features
- Phase-by-phase roadmap fitted to your available time (weeks, months or years, up to 5 years)
- Content adjusted to your skill level
- **Optional personalisation:** your purpose (job, career switch, exam...), a specific goal, what you already know, learning style, budget and extra notes
- Topic checklist with a **progress bar**, plus a project and a milestone for every phase
- Download the roadmap as a `.md` file
- Configurable Gemini model, with automatic fallback if a model is retired
- Clear error messages (missing key, bad key, quota, invalid response)

## Project structure
```
.
├── app.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Run locally

1. Get a free API key: https://aistudio.google.com/apikey
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Provide your key (pick one):
   - Paste it in the app sidebar, **or**
   - Set an environment variable:
     ```bash
     export GEMINI_API_KEY="your_key"      # Windows PowerShell: $env:GEMINI_API_KEY="your_key"
     ```
   - Or create `.streamlit/secrets.toml`:
     ```toml
     GEMINI_API_KEY = "your_key"
     ```
4. Start the app:
   ```bash
   streamlit run app.py
   ```

## Changing the model
The default model is `gemini-3.8-flash`. If a model is retired ("404 NOT_FOUND"), the app automatically tries newer fallback models. You can also change the model in the sidebar, or set the `GEMINI_MODEL` environment variable. See the list of current model names at https://ai.google.dev/gemini-api/docs/models

## Deploy on Streamlit Community Cloud
1. Push this project to a public GitHub repo.
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **Create app**, choose your repo, branch `main` and main file `app.py`.
4. Open **Advanced settings → Secrets** and add:
   ```toml
   GEMINI_API_KEY = "your_key"
   ```
5. Click **Deploy**.

## Security
Never commit your API key. `.gitignore` already excludes `.env` and `.streamlit/secrets.toml`.

## License
MIT

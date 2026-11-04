# AI Learning Roadmap Generator

A Streamlit application that creates personalized learning roadmaps with Google's Gemini Flash model.

## Features

- Collects a learning field or skill.
- Supports Beginner, Intermediate, and Advanced levels.
- Lets users choose a learning duration from 2 weeks to 12 months.
- Accounts for weekly study hours and an optional personal goal.
- Generates learning phases, topics, exercises, projects, resources, progress checkpoints, and a first-week action plan.
- Lets users download the generated roadmap as a Markdown file.
- Reads the Gemini API key securely from Streamlit secrets or an environment variable.
- Handles common Gemini API errors such as quota limits and temporary unavailability.

## Project structure

```text
ai-learning-roadmap-generator/
├── app.py
├── README.md
└── requirements.txt
```

## Requirements

- Python 3.10 or newer
- A Google Gemini API key from Google AI Studio
- Internet connection

## 1. Clone or download the project

If the project is already on your computer, open its folder in VS Code. Otherwise:

```bash
git clone https://github.com/YOUR-USERNAME/ai-learning-roadmap-generator.git
cd ai-learning-roadmap-generator
```

## 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```cmd
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Get your Gemini API key

1. Open [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Create or select a project and generate an API key.
4. Copy the key. Do not share it or commit it to GitHub.

### Configure the key locally

Create a folder named `.streamlit` in the project root. Inside it, create `secrets.toml`:

```toml
GEMINI_API_KEY = "paste-your-real-api-key-here"
```

The app also accepts an environment variable named `GEMINI_API_KEY`.

**Important:** Never commit `.streamlit/secrets.toml` to GitHub.

## 5. Run the application

From the project root:

```bash
streamlit run app.py
```

Streamlit will print a local URL, usually `http://localhost:8501`. Open it in your browser.

## 6. Push the project to GitHub

Create a new empty repository on GitHub named `ai-learning-roadmap-generator`. Do not add a README from GitHub if you already have this README locally.

Create a `.gitignore` file in the project root with:

```gitignore
.venv/
__pycache__/
*.py[cod]
.streamlit/secrets.toml
.env
```

Then run these commands in the project folder:

```bash
git init
git add app.py README.md requirements.txt .gitignore
git commit -m "Build AI learning roadmap generator"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/ai-learning-roadmap-generator.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username. If Git says the remote already exists, use `git remote set-url origin https://github.com/YOUR-USERNAME/ai-learning-roadmap-generator.git`.

## 7. Deploy on Streamlit Community Cloud

1. Push your project to GitHub.
2. Visit [Streamlit Community Cloud](https://share.streamlit.io/) and sign in with GitHub.
3. Select **Create app**.
4. Choose your repository, the `main` branch, and `app.py` as the main file.
5. Open **Advanced settings** and add this under **Secrets**:

   ```toml
   GEMINI_API_KEY = "paste-your-real-api-key-here"
   ```

6. Select a supported Python version (Python 3.11 or 3.12 is a sensible choice).
7. Click **Deploy** and wait for the app to build.

Your app will receive a public `streamlit.app` URL. Keep the API key in Streamlit Secrets, not in your GitHub repository.

## Troubleshooting

- **API key not found:** Check the spelling `GEMINI_API_KEY` and confirm that your local `secrets.toml` is in `.streamlit/`.
- **401 / 403 or permission error:** Confirm the key is valid and the Gemini API is enabled for its Google project.
- **429 / quota error:** Check your Google AI Studio usage and quota. Wait before retrying if you have reached a rate limit.
- **503 / unavailable:** Gemini may be temporarily busy. Wait and retry.
- **Module not found:** Activate the virtual environment and run `pip install -r requirements.txt` again.
- **Deployment build failure:** Check that `requirements.txt` is in the repository root and review the Streamlit app logs.

## Model configuration

The model is configured near the top of `app.py`:

```python
MODEL_NAME = "gemini-3.8-flash"
```

If that model is not available to your API key or region, replace it with a currently supported Flash model listed in Google AI Studio.

## Current limitations

- Roadmaps are AI-generated suggestions and may need review.
- The app does not save user accounts or previously generated roadmaps after a session ends.
- The app does not verify that every named learning resource is current or free.

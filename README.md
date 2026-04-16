# Idea Validator (Flask)

A Flask-based web app that transforms a raw startup idea into a market-informed SRS document with downloadable `.docx` output.

## Flow

1. Idea Input -> `Start Analysis`
2. Stage 1: Market Analysis -> competitor intelligence + summary
3. Stage 2: Improvements -> user selects AI-generated suggestions
4. Stage 3: SRS Generate -> full markdown SRS + download as Word file

## Tech Stack

- Python
- Flask
- HTML/CSS/JS frontend
- LLM API (OpenAI-compatible chat endpoint)
- `python-docx` for Word export

## Project Structure

- `app.py` - Flask backend routes and LLM integration
- `templates/index.html` - UI layout
- `static/styles.css` - styling
- `static/app.js` - frontend logic and API calls
- `.env.example` - environment variable template
- `requirements.txt` - Python dependencies

## Setup

1. Create virtual environment and activate it.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment:

- Copy `.env.example` to `.env`
- Set your API key in `GROQ_API_KEY`
- Optionally adjust `GROQ_BASE_URL` and `MODEL`

Example `.env`:

```env
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_API_KEY=your_gsk_key_here
MODEL=groq/compound
```

4. Run app:

```bash
python app.py
```

5. Open browser:

- http://127.0.0.1:5000

## API Endpoints

- `POST /api/stage1` -> market analysis + structured JSON
- `POST /api/stage2` -> improvement suggestions JSON
- `POST /api/stage3` -> SRS markdown generation
- `POST /api/download` -> return `.docx` file built from SRS markdown

## Notes

- Keep API key in `.env` only; do not hardcode it in source files.
- The model must return valid JSON for Stage 1 structure and Stage 2 suggestions.
- The app includes a fallback JSON extractor for responses wrapped in extra text.

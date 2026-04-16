import io
import json
import os
import re
from datetime import datetime

import requests
from docx import Document
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)


MARKET_RESEARCH_SYSTEM_PROMPT = """You are a senior market research analyst.

Task:
Analyze the given product idea and find real-world competitors, SaaS products, or GitHub repositories.

RULES:
- Only include real and verifiable products
- Do NOT hallucinate or create fake companies
- If unsure, do NOT include the entry
- Prefer well-known or easily verifiable tools
- Focus on real-world implementations
"""

STRUCTURE_ANALYSIS_SYSTEM_PROMPT = """You are a professional product analyst.

Task:
Convert the provided market research into structured product intelligence.

RULES:
- Do NOT invent any data
- Only use information present in the research
- If data is missing, infer carefully or leave minimal
- Ensure all URLs are from the research
"""

SUGGESTIONS_SYSTEM_PROMPT = """You are a startup innovation strategist.

Task:
Generate 5 high-impact improvements based on competitor gaps and market opportunities.

RULES:
- Do NOT give generic suggestions (e.g., \"improve UI\", \"add AI\")
- Each suggestion must be specific, actionable, and realistic
- Base suggestions on competitor weaknesses or missing features
- Focus on differentiation and uniqueness
"""

SRS_SYSTEM_PROMPT = """You are a senior software architect.

Task:
Generate a complete Software Requirements Specification (SRS) document.

RULES:
- Must be detailed and professional
- Must include technical depth
- Must be in Markdown format
- Avoid generic statements
- Be specific to the product
"""


def get_env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    return value.strip() if value else ""


def get_client_config() -> dict:
    base_url = get_env("LLM_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    llm_api_key = get_env("LLM_API_KEY")
    openrouter_api_key = get_env("OPENROUTER_API_KEY")
    groq_api_key = get_env("GROQ_API_KEY")
    grok_api_key = get_env("GROK_API_KEY")

    # Choose a provider-specific key first to avoid mixing credentials
    # (for example, gsk_* key with OpenRouter base URL).
    if "openrouter" in base_url:
        api_key = openrouter_api_key or llm_api_key
    elif "groq" in base_url:
        api_key = groq_api_key or llm_api_key
    elif "x.ai" in base_url:
        api_key = grok_api_key or llm_api_key
    else:
        api_key = llm_api_key or openrouter_api_key or groq_api_key or grok_api_key

    if not api_key:
        raise ValueError(
            "Missing API key. Set LLM_API_KEY or provider-specific key in .env "
            "(OPENROUTER_API_KEY / GROQ_API_KEY / GROK_API_KEY)."
        )

    return {
        "api_key": api_key,
        "base_url": base_url,
        "market_model": get_env("MARKET_MODEL", "groq/compound"),
        "srs_model": get_env("SRS_MODEL", "openai/gpt-oss-120b"),
    }


def call_chat_model(model: str, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    config = get_client_config()
    base_url = config["base_url"]
    api_key = config["api_key"]
    model_candidates = [model]

    # Route groq/* model IDs directly to Groq's OpenAI-compatible endpoint.
    if model.startswith("groq/"):
        groq_model = model.split("/", 1)[1].strip()
        base_url = get_env("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
        api_key = get_env("GROQ_API_KEY") or get_env("LLM_API_KEY")
        if not api_key:
            raise ValueError("Missing Groq key. Set GROQ_API_KEY (or LLM_API_KEY with gsk_* key) in .env")

        model_candidates = [groq_model]
        if groq_model == "compound":
            model_candidates.append("compound-beta")

    url = f"{base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    if "openrouter" in base_url:
        headers["HTTP-Referer"] = "http://localhost:5000"
        headers["X-Title"] = "Idea Validator"

    last_error = None
    for candidate_model in model_candidates:
        payload = {
            "model": candidate_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }

        response = requests.post(url, headers=headers, json=payload, timeout=90)
        if response.status_code >= 400:
            last_error = response
            # If one alias fails on 400, try next candidate.
            if response.status_code == 400 and candidate_model != model_candidates[-1]:
                continue
            response.raise_for_status()

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError):
            raise ValueError(f"Unexpected model response format: {json.dumps(data)[:500]}")

    if last_error is not None:
        last_error.raise_for_status()

    raise ValueError("Model call failed before receiving a response.")


def parse_json_output(text: str) -> dict:
    text = text.strip()
    if not text:
        raise ValueError("Model returned empty response when JSON was expected.")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("Could not find JSON object in model output.")

    extracted = match.group(0)
    return json.loads(extracted)


def normalize_features(raw_features):
    if isinstance(raw_features, list):
        return [str(item).strip() for item in raw_features if str(item).strip()]

    if isinstance(raw_features, str):
        tokens = re.split(r"[\n,]", raw_features)
        return [token.strip() for token in tokens if token.strip()]

    return []


def market_research_user_prompt(raw_idea: str, features: list[str]) -> str:
    feature_block = "\n".join([f"- {item}" for item in features]) if features else "- Not provided"
    return f"""INPUT:
Product Idea:
\"\"\"
{raw_idea}
\"\"\"

Current Features:
{feature_block}

OUTPUT:
Provide structured information for at least 3-5 competitors including:
- Product name
- Working URL
- Problem they solve
- Solution approach
- Main features
- Relation to this idea
- Similarity score (0-10)

Also include:
- Market summary
- Differentiation insight
"""


def structure_analysis_user_prompt(raw_idea: str, features: list[str], research_text: str) -> str:
    return f"""INPUT:
Original Idea:
\"\"\"
{raw_idea}
\"\"\"

Features:
{json.dumps(features, ensure_ascii=True)}

Market Research:
\"\"\"
{research_text}
\"\"\"

OUTPUT:
Return ONLY valid JSON:

{{
  \"title\": \"\",
  \"problem\": \"\",
  \"solution\": \"\",
  \"analysis\": {{
    \"competitors\": [
      {{
        \"name\": \"\",
        \"url\": \"\",
        \"similarityScore\": 0,
        \"problem\": \"\",
        \"solution\": \"\",
        \"mainFeatures\": [],
        \"relationToIdea\": \"\"
      }}
    ],
    \"summary\": \"\",
    \"differentiationFactor\": \"\"
  }}
}}
"""


def suggestions_user_prompt(title: str, problem: str, solution: str, summary: str, competitors: list[dict]) -> str:
    return f"""INPUT:
Title: {title}
Problem: {problem}
Solution: {solution}
Market Summary: {summary}
Competitors:
{json.dumps(competitors, ensure_ascii=True, indent=2)}

OUTPUT:
Return ONLY valid JSON:

{{
  \"suggestions\": [
    {{
      \"id\": \"\",
      \"type\": \"feature | strategic | technical\",
      \"title\": \"\",
      \"description\": \"\",
      \"sourceInspiration\": \"\"
    }}
  ]
}}
"""


def srs_user_prompt(title: str, problem: str, solution: str, final_features: list[str]) -> str:
    return f"""INPUT:
Title: {title}
Problem: {problem}
Solution: {solution}
Final Features:
{json.dumps(final_features, ensure_ascii=True, indent=2)}

OUTPUT FORMAT:

# Software Requirements Specification

## 1. Introduction
- Purpose
- Scope
- Intended Audience

## 2. Overall Description
- Product Perspective
- Product Functions
- User Classes

## 3. External Interface Requirements
- User Interfaces
- Software Interfaces
- Communication Interfaces

## 4. System Features
- Detailed feature descriptions

## 5. Non-Functional Requirements
- Performance
- Security
- Scalability
- Reliability

Ensure the document is detailed enough for developers to start implementation.
"""


def markdown_to_docx(markdown_text: str, title: str) -> io.BytesIO:
    doc = Document()
    doc.add_heading(title or "Software Requirements Specification", 0)

    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("### "):
            doc.add_heading(stripped[4:].strip(), level=3)
        elif stripped.startswith("## "):
            doc.add_heading(stripped[3:].strip(), level=2)
        elif stripped.startswith("# "):
            doc.add_heading(stripped[2:].strip(), level=1)
        elif re.match(r"^[-*]\s+", stripped):
            doc.add_paragraph(re.sub(r"^[-*]\s+", "", stripped), style="List Bullet")
        elif re.match(r"^\d+\.\s+", stripped):
            doc.add_paragraph(re.sub(r"^\d+\.\s+", "", stripped), style="List Number")
        else:
            doc.add_paragraph(stripped)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/stage1")
def stage1_market_analysis():
    try:
        payload = request.get_json(force=True)
        raw_idea = str(payload.get("rawIdea", "")).strip()
        features = normalize_features(payload.get("features", []))

        if not raw_idea:
            return jsonify({"error": "rawIdea is required"}), 400

        config = get_client_config()

        research_text = call_chat_model(
            model=config["market_model"],
            system_prompt=MARKET_RESEARCH_SYSTEM_PROMPT,
            user_prompt=market_research_user_prompt(raw_idea, features),
            temperature=0.2,
        )

        structured_raw = call_chat_model(
            model=config["market_model"],
            system_prompt=STRUCTURE_ANALYSIS_SYSTEM_PROMPT,
            user_prompt=structure_analysis_user_prompt(raw_idea, features, research_text),
            temperature=0.1,
        )

        structured = parse_json_output(structured_raw)

        return jsonify(
            {
                "researchText": research_text,
                "structured": structured,
            }
        )

    except requests.HTTPError as exc:
        details = ""
        try:
            details = exc.response.text[:1000] if exc.response is not None else ""
        except Exception:
            pass
        return jsonify({"error": "LLM API request failed", "details": details}), 502
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/stage2")
def stage2_improvements():
    try:
        payload = request.get_json(force=True)

        title = str(payload.get("title", "")).strip()
        problem = str(payload.get("problem", "")).strip()
        solution = str(payload.get("solution", "")).strip()
        summary = str(payload.get("summary", "")).strip()
        competitors = payload.get("competitors", [])

        if not title:
            return jsonify({"error": "title is required"}), 400

        config = get_client_config()

        suggestions_raw = call_chat_model(
            model=config["srs_model"],
            system_prompt=SUGGESTIONS_SYSTEM_PROMPT,
            user_prompt=suggestions_user_prompt(title, problem, solution, summary, competitors),
            temperature=0.4,
        )

        suggestions = parse_json_output(suggestions_raw)
        return jsonify(suggestions)

    except requests.HTTPError as exc:
        details = ""
        try:
            details = exc.response.text[:1000] if exc.response is not None else ""
        except Exception:
            pass
        return jsonify({"error": "LLM API request failed", "details": details}), 502
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/stage3")
def stage3_generate_srs():
    try:
        payload = request.get_json(force=True)

        title = str(payload.get("title", "")).strip()
        problem = str(payload.get("problem", "")).strip()
        solution = str(payload.get("solution", "")).strip()
        final_features = normalize_features(payload.get("finalFeatures", []))

        if not title:
            return jsonify({"error": "title is required"}), 400

        config = get_client_config()

        srs_markdown = call_chat_model(
            model=config["srs_model"],
            system_prompt=SRS_SYSTEM_PROMPT,
            user_prompt=srs_user_prompt(title, problem, solution, final_features),
            temperature=0.2,
        )

        return jsonify({"srsMarkdown": srs_markdown})

    except requests.HTTPError as exc:
        details = ""
        try:
            details = exc.response.text[:1000] if exc.response is not None else ""
        except Exception:
            pass
        return jsonify({"error": "LLM API request failed", "details": details}), 502
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/download")
def download_srs_docx():
    try:
        payload = request.get_json(force=True)
        srs_markdown = str(payload.get("srsMarkdown", "")).strip()
        title = str(payload.get("title", "Software Requirements Specification")).strip()

        if not srs_markdown:
            return jsonify({"error": "srsMarkdown is required"}), 400

        file_buffer = markdown_to_docx(srs_markdown, title)

        safe_title = re.sub(r"[^a-zA-Z0-9_-]+", "_", title).strip("_") or "srs"
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_name = f"{safe_title}_{timestamp}.docx"

        return send_file(
            file_buffer,
            as_attachment=True,
            download_name=file_name,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

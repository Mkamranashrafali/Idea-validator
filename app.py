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
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

app = Flask(__name__)


MARKET_RESEARCH_SYSTEM_PROMPT = """You are a senior product-focused market research analyst specializing in SaaS and tech ecosystems.

Your goal is NOT just to list competitors, but to deeply analyze the market landscape of the given product idea.

Task:
Analyze the product idea and identify highly relevant, real-world competitors including SaaS products, startups, and open-source GitHub projects.

STRICT RULES:
- Only include REAL, verifiable, and existing products
- Do NOT hallucinate or invent names, links, or companies
- If you are not confident about a product, SKIP it
- Prioritize products that are functionally similar (not just loosely related)
- Focus on products solving the SAME or CLOSELY RELATED problem
- Prefer well-known tools, funded startups, or active GitHub projects
- Avoid outdated or dead products unless highly relevant

ANALYSIS DEPTH:
For each competitor:
- Understand their CORE purpose (not surface-level)
- Focus on their MAIN value proposition
- Identify their key features (not generic ones)
- Clearly explain how they overlap with the user's idea
- Be precise in similarity scoring (0 = unrelated, 10 = nearly identical)

INPUT:
Product Idea:


Current Features:
{features}

OUTPUT REQUIREMENTS:
- Find 3–5 HIGHLY RELEVANT competitors (quality > quantity)
- Provide:
  - Product name
  - Working URL (accurate)
  - Problem they solve
  - Solution approach
  - Main features (concise and meaningful)
  - Relation to this idea (clear comparison)
  - Similarity score (0–10)

Additionally:
- Provide a concise MARKET SUMMARY explaining the current landscape
- Clearly explain the DIFFERENTIATION FACTOR (what makes this idea unique or competitive)

IMPORTANT:
Focus on DEPTH, ACCURACY, and RELEVANCE over quantity.
"""

STRUCTURE_ANALYSIS_SYSTEM_PROMPT = """You are a senior product analyst and data structuring expert.

Your goal is to convert unstructured market research into clean, accurate, and structured product intelligence.

Task:
Extract and transform the provided market research into a well-defined JSON structure.

STRICT RULES:
- Do NOT hallucinate or invent any data
- ONLY use information explicitly present in the research
- If a field is missing, infer carefully OR keep it minimal (do not fabricate)
- Ensure all URLs are EXACTLY as given in the research (no modification)
- Maintain consistency across all competitor entries
- Similarity scores must remain unchanged (do not alter values)

DATA QUALITY RULES:
- Keep text concise, clear, and professional
- Avoid vague or generic descriptions
- Normalize competitor data (same structure for all)
- Extract meaningful feature lists (avoid filler points)

INPUT:
Original Idea:


Features:
{features}

Market Research:


OUTPUT REQUIREMENTS:
- Generate a clean and professional project TITLE
- Extract a clear and focused PROBLEM statement
- Extract a strong and practical SOLUTION
- Structure all competitors into consistent format
- Provide a meaningful MARKET SUMMARY
- Provide a clear DIFFERENTIATION FACTOR

OUTPUT FORMAT:
Return ONLY valid JSON (no markdown, no explanation, no extra text)
"""

SUGGESTIONS_SYSTEM_PROMPT = """You are a senior startup innovation strategist and product thinker.

Your goal is to generate HIGH-IMPACT, NON-OBVIOUS improvements that can make a product stand out in a competitive market.

Task:
Based on the provided product idea and its competitor analysis, generate 5 powerful improvements.

STRICT RULES:
- Do NOT give generic suggestions (e.g., "improve UI", "add AI", "make it faster")
- Each suggestion must be SPECIFIC, ACTIONABLE, and PRACTICAL
- Focus on real differentiation, not minor enhancements
- Base ideas on competitor weaknesses, missing features, or unexplored opportunities
- Avoid obvious or commonly used startup ideas
- Think like a founder trying to WIN the market

QUALITY REQUIREMENTS:
- Each suggestion should feel like a strong product decision
- Prefer ideas that combine multiple concepts (feature + strategy + tech)
- Highlight opportunities competitors have missed
- Suggestions should be implementable (not futuristic fantasy)
"""

SRS_SYSTEM_PROMPT = """You are a senior software architect with experience in designing production-grade systems.

Your goal is to generate a COMPLETE, DETAILED, and IMPLEMENTATION-READY Software Requirements Specification (SRS).

Task:
Create a full SRS document based on the given product idea, refined problem, solution, and final features.

STRICT RULES:
- The document MUST be detailed and professionally structured
- Avoid generic or vague statements
- Be highly specific to the product context
- Include technical depth that developers can directly use
- Do NOT write filler content
- Do NOT repeat the same ideas in different wording

QUALITY REQUIREMENTS:
- Clearly define system behavior and features
- Include real-world technical considerations (APIs, data flow, architecture hints)
- Write in a way that a developer can start building from this document
- Break down features into meaningful functional requirements
- Mention constraints, assumptions, and dependencies where relevant

OUTPUT FORMAT:

# Software Requirements Specification

## 1. Introduction
- Purpose
- Scope
- Intended Audience

## 2. Overall Description
- Product Perspective
- Core System Workflow
- User Classes and Characteristics
- Assumptions and Dependencies

## 3. System Architecture Overview
- High-level architecture (e.g., client-server, microservices)
- Key components/modules
- Data flow description

## 4. External Interface Requirements
- User Interfaces
- Software Interfaces (APIs, third-party integrations)
- Communication Interfaces

## 5. System Features
- Detailed feature breakdown
- Functional requirements for each feature
- Edge cases and expected behavior

## 6. Non-Functional Requirements
- Performance
- Scalability
- Security
- Reliability
- Maintainability

## 7. Constraints
- Technical constraints
- Business constraints

IMPORTANT:
- The output must be clean Markdown
- The document should be detailed enough for direct development use
"""


def get_env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    return value.strip() if value else ""


def clamp_text(text: str, max_chars: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n\n[Truncated to fit request size limits.]"


def compact_features(features: list[str], max_items: int = 20, max_chars_per_item: int = 220) -> list[str]:
    compacted = []
    for item in features[:max_items]:
        compacted.append(clamp_text(str(item), max_chars_per_item))
    return [item for item in compacted if item]


def compact_competitors(competitors: list[dict], max_items: int = 8, max_chars_per_field: int = 420) -> list[dict]:
    compacted = []
    for comp in competitors[:max_items]:
        if not isinstance(comp, dict):
            continue

        compacted.append(
            {
                "name": clamp_text(str(comp.get("name", "")), max_chars_per_field),
                "url": clamp_text(str(comp.get("url", "")), max_chars_per_field),
                "similarityScore": comp.get("similarityScore", 0),
                "problem": clamp_text(str(comp.get("problem", "")), max_chars_per_field),
                "solution": clamp_text(str(comp.get("solution", "")), max_chars_per_field),
                "mainFeatures": compact_features(comp.get("mainFeatures", []), max_items=8, max_chars_per_item=140),
                "relationToIdea": clamp_text(str(comp.get("relationToIdea", "")), max_chars_per_field),
            }
        )
    return compacted


def get_client_config() -> dict:
    base_url = get_env("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    api_key = get_env("GROQ_API_KEY")
    model = get_env("MODEL", "groq/compound")

    if not api_key:
        raise ValueError("Missing API key. Set GROQ_API_KEY in .env")

    if not model:
        raise ValueError("Missing model. Set MODEL in .env (example: openai/gpt-oss-120b).")

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
    }


def call_chat_model(model: str, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    config = get_client_config()
    base_url = config["base_url"]
    api_key = config["api_key"]

    requested_model = model.strip()
    model_candidates = [requested_model]

    # Groq accepts fully-qualified IDs like "groq/compound".
    # Keep the requested model first, then try practical fallbacks.
    if requested_model == "groq/compound":
        model_candidates.extend([
            "groq/compound-mini",
            "llama-3.3-70b-versatile",
        ])

    # De-duplicate while preserving order.
    model_candidates = list(dict.fromkeys(model_candidates))

    # Prepare progressively smaller prompt variants to recover from
    # provider-side request size limits.
    prompt_variants = [user_prompt]
    for max_chars in (12000, 8000, 5000, 3000):
        if len(user_prompt) > max_chars:
            prompt_variants.append(clamp_text(user_prompt, max_chars))
    prompt_variants = list(dict.fromkeys(prompt_variants))

    url = f"{base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error = None
    for model_index, candidate_model in enumerate(model_candidates):
        for prompt_index, candidate_prompt in enumerate(prompt_variants):
            payload = {
                "model": candidate_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": candidate_prompt},
                ],
                "temperature": temperature,
            }

            response = requests.post(url, headers=headers, json=payload, timeout=90)
            if response.status_code >= 400:
                last_error = response

                error_code = ""
                error_message = ""
                try:
                    error_payload = response.json().get("error", {})
                    error_code = str(error_payload.get("code", "")).strip().lower()
                    error_message = str(error_payload.get("message", "")).strip().lower()
                except Exception:
                    pass

                is_too_large = (
                    response.status_code == 413
                    or error_code == "request_too_large"
                    or "request entity too large" in error_message
                )

                # Retry same model with a smaller prompt variant if available.
                if is_too_large and prompt_index < len(prompt_variants) - 1:
                    continue

                # Try next fallback model on client-side 400 responses.
                if response.status_code == 400 and model_index < len(model_candidates) - 1:
                    break

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

    def _extract_json_candidate(raw: str) -> str:
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
        if fenced:
            return fenced.group(1).strip()

        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            return match.group(0).strip()

        return raw.strip()

    def _sanitize_json_candidate(raw: str) -> str:
        # Escape invalid backslashes that often appear in LLM-generated JSON strings.
        sanitized = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', raw)
        # Remove trailing commas before closing braces/brackets.
        sanitized = re.sub(r",\s*([}\]])", r"\1", sanitized)
        return sanitized

    candidate = _extract_json_candidate(text)

    for attempt in (candidate, _sanitize_json_candidate(candidate)):
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            continue

    raise ValueError("Could not parse valid JSON from model output.")


def normalize_features(raw_features):
    if isinstance(raw_features, list):
        return [str(item).strip() for item in raw_features if str(item).strip()]

    if isinstance(raw_features, str):
        tokens = re.split(r"[\n,]", raw_features)
        return [token.strip() for token in tokens if token.strip()]

    return []


def market_research_user_prompt(raw_idea: str, features: list[str]) -> str:
    raw_idea = clamp_text(raw_idea, 4500)
    features = compact_features(features, max_items=20, max_chars_per_item=180)
    feature_block = "\n".join([f"- {item}" for item in features]) if features else "- Not provided"
    return f"""INPUT:
Product Idea:
\"\"\"
{raw_idea}
\"\"\"

Current Features:
{feature_block}

OUTPUT REQUIREMENTS:
Provide structured information for 3-5 highly relevant competitors including:
- Product name
- Working URL
- Problem they solve
- Solution approach
- Main features (concise and meaningful)
- Relation to this idea
- Similarity score (0-10)

Also include:
- Market summary (concise landscape view)
- Differentiation factor (what makes this idea unique or competitive)
"""


def structure_analysis_user_prompt(raw_idea: str, features: list[str], research_text: str) -> str:
    raw_idea = clamp_text(raw_idea, 4500)
    features = compact_features(features, max_items=20, max_chars_per_item=180)
    research_text = clamp_text(research_text, 16000)
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

OUTPUT REQUIREMENTS:
- Generate a clean and professional project title
- Extract a clear problem statement
- Extract a practical solution
- Structure competitor data consistently
- Include summary and differentiation factor

OUTPUT FORMAT:
Return ONLY valid JSON (no markdown, no explanation, no extra text):

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
    title = clamp_text(title, 300)
    problem = clamp_text(problem, 1800)
    solution = clamp_text(solution, 1800)
    summary = clamp_text(summary, 2400)
    competitors = compact_competitors(competitors, max_items=8, max_chars_per_field=420)
    return f"""INPUT:
Title: {title}
Problem: {problem}
Solution: {solution}
Market Summary: {summary}
Competitors:
{json.dumps(competitors, ensure_ascii=True, indent=2)}

OUTPUT REQUIREMENTS:
Generate exactly 5 suggestions.

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
    title = clamp_text(title, 300)
    problem = clamp_text(problem, 2000)
    solution = clamp_text(solution, 2000)
    final_features = compact_features(final_features, max_items=30, max_chars_per_item=220)
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
- Core System Workflow
- User Classes and Characteristics
- Assumptions and Dependencies

## 3. System Architecture Overview
- High-level architecture
- Key components/modules
- Data flow description

## 4. External Interface Requirements
- User Interfaces
- Software Interfaces (APIs, third-party integrations)
- Communication Interfaces

## 5. System Features
- Detailed feature breakdown
- Functional requirements for each feature
- Edge cases and expected behavior

## 6. Non-Functional Requirements
- Performance
- Scalability
- Security
- Reliability
- Maintainability

## 7. Constraints
- Technical constraints
- Business constraints

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


@app.get("/api/health")
def health_check():
    return jsonify({"status": "ok"})


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
            model=config["model"],
            system_prompt=MARKET_RESEARCH_SYSTEM_PROMPT,
            user_prompt=market_research_user_prompt(raw_idea, features),
            temperature=0.2,
        )

        structured_raw = call_chat_model(
            model=config["model"],
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
            model=config["model"],
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
            model=config["model"],
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

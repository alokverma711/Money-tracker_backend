import json
import re
import os
from google import genai
from google.genai import types # Added for configuration types
from django.conf import settings
from .prompts import CATEGORY_PROMPT, INSIGHT_PROMPT

# Configure API key if available
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    try:
        # NEW SYNTAX: Initialize the Client object
        client = genai.Client(api_key=api_key)
        print("Success: Google AI Client configured.")
    except Exception as e:
        print(f"Warning: Failed to initialize Google AI Client: {e}")
        client = None
else:
    print("Warning: GEMINI_API_KEY not found in .env. AI features will be disabled.")
    client = None


def _safe_load_json(text: str):
    # Try to safely parse JSON from `text`
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # find a {...} substring (greedy inner match)
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    m2 = re.search(r"\[.*\]", text, flags=re.DOTALL)
    if m2:
        try:
            return json.loads(m2.group(0))
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError("Could not decode JSON", text, 0)


def suggest_category(description: str, amount: float, model_name: str = "gemini-2.5-flash"):
    if not description:
        return None

    if not client:
        print("AI: GOOGLE_API_KEY not configured, skipping category suggestion.")
        return None

    prompt = CATEGORY_PROMPT.format(
        description=description.replace('"', '\\"'),
        amount=amount,
    )

    try:
        # NEW SYNTAX: Call via client.models.generate_content
        response = client.models.generate_content(
            model=model_name, 
            contents=prompt
        )

        raw_text = response.text
        text = re.sub(r'```json\s*|```', '', raw_text).strip()
        
        print("=== Gemini raw response ===")
        print(text)
        print("=== end raw response ===")

        data = json.loads(text)
        category = data.get("category") or data.get("Category")

        if category:
            return {"category": category}

        print("AI: no valid 'category' key found in parsed JSON.")
        return None

    except Exception as e:
        print("Google AI error in suggest_category():", repr(e))
        return None

def generate_insights(summary: dict, previous_total: float | None = None, model_name: str = "gemini-2.5-flash"):
    if not isinstance(summary, dict):
        print("generate_insights: invalid 'summary' input (not a dict).")
        return None

    if not client:
        print("AI: Client not configured, skipping insights generation.")
        return None

    by_cat = summary.get("by_category", [])
    try:
        by_cat_json = json.dumps(by_cat)
    except Exception:
        by_cat_json = "[]"

    prompt = INSIGHT_PROMPT.format(
        period=str(summary.get("period", "monthly")),
        start=str(summary.get("start", "")),
        end=str(summary.get("end", "")),
        total=summary.get("total", 0),
        by_category_json=by_cat_json,
        previous_total=(previous_total if previous_total is not None else "null"),
    )

    try:
        # NEW SYNTAX: Call via client.models.generate_content
        response = client.models.generate_content(
            model=model_name, 
            contents=prompt
        )

        text = response.text
        if text:
            text = text.strip()

        print("=== Gemini insight raw response ===")
        print(text)
        print("=== end insight raw response ===")

        try:
            data = _safe_load_json(text)
        except json.JSONDecodeError:
            return {"text": text}

        if isinstance(data, dict) and "text" in data and isinstance(data["text"], str):
            return {"text": data["text"].strip()}

        if isinstance(data, dict):
            for candidate_key in ("insight", "summary", "text", "result"):
                v = data.get(candidate_key)
                if isinstance(v, str) and v.strip():
                    return {"text": v.strip()}

        if isinstance(data, str) and data.strip():
            return {"text": data.strip()}

        print("generate_insights: no usable 'text' in model output.")
        return None

    except Exception as e:
        print("Google AI error in generate_insights():", repr(e))
        return None
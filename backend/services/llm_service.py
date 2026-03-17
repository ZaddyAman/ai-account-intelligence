"""LLM service — supports Kilo Code API (primary) and Gemini (fallback).

Improvements over v1:
- Exponential backoff on rate-limit errors (2^attempt × 2s)
- Prompt-level TTL cache so identical calls in batch mode are not duplicated
- Semaphore raised to 5 concurrent calls
"""

import asyncio
import hashlib
import json
import re
import httpx
from backend.config import (
    GEMINI_API_KEY, GEMINI_MODEL,
    KILO_API_KEY, KILO_MODEL,
    LLM_PROVIDER,
)
from backend.services.cache_service import llm_cache

# Limit concurrent LLM calls to avoid rate limits
_semaphore = asyncio.Semaphore(5)


# ── Kilo Code API (OpenAI-compatible) ─────────────────────────────

async def _kilo_query(prompt: str, system_instruction: str = "") -> str:
    """Call Kilo Code API (OpenAI-compatible endpoint)."""
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.kilo.ai/api/gateway/chat/completions",
            headers={
                "Authorization": f"Bearer {KILO_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": KILO_MODEL,
                "messages": messages,
                "temperature": 0.3,
                "stream": False,
            },
        )
        data = resp.json()
        if "choices" in data and data["choices"]:
            message = data["choices"][0].get("message", {})
            content = message.get("content", "")

            # Some free models (e.g. minimax) return content as a list of parts
            if not content and isinstance(message.get("content"), list):
                parts = message.get("content") or []
                for part in parts:
                    if isinstance(part, dict) and part.get("type") == "text":
                        content = part.get("text", "")
                        break

            # Strip <think>...</think> reasoning tags if present
            if content and "<think>" in content:
                content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

            return content.strip() if content else ""
        elif "error" in data:
            print(f"[KILO ERROR] {data['error']}")
            return ""
        return ""


# ── Gemini ────────────────────────────────────────────────────────

async def _gemini_query(prompt: str, system_instruction: str = "") -> str:
    """Call Google Gemini API."""
    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=GEMINI_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_instruction or None,
            temperature=0.3,
        ),
    )
    return response.text.strip()


# ── Cache key ──────────────────────────────────────────────────────

def _prompt_cache_key(prompt: str, system_instruction: str) -> str:
    raw = f"{LLM_PROVIDER}||{system_instruction}||{prompt}"
    return hashlib.sha256(raw.encode()).hexdigest()


# ── Public API ────────────────────────────────────────────────────

async def llm_query(prompt: str, system_instruction: str = "") -> str:
    """Send a prompt to the configured LLM with retry logic and caching."""
    # Check cache
    ck = _prompt_cache_key(prompt, system_instruction)
    cached = llm_cache.get(ck)
    if cached is not None:
        return cached

    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with _semaphore:
                if LLM_PROVIDER == "kilo":
                    result = await _kilo_query(prompt, system_instruction)
                else:
                    result = await _gemini_query(prompt, system_instruction)
            if result:
                llm_cache.set(ck, result)
            return result
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower():
                # Exponential backoff: 2s, 4s, 8s
                wait_time = (2 ** attempt) * 2
                print(f"[LLM RATE LIMIT] Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                print(f"[LLM ERROR] {e}")
                return ""
    print("[LLM ERROR] Max retries exceeded")
    return ""


async def llm_json_query(prompt: str, system_instruction: str = "") -> dict:
    """Send a prompt and parse the JSON response."""
    full_system = (
        (system_instruction + "\n\n" if system_instruction else "")
        + "IMPORTANT: Respond ONLY with valid JSON. No markdown, no code fences, no explanations, no extra text. Just the JSON object."
    )
    raw = await llm_query(prompt, full_system)
    if not raw:
        return {}
    # Strip any markdown code fences
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)
    # Try to find JSON within the response
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start:end])
            except json.JSONDecodeError:
                pass
        print(f"[LLM JSON PARSE ERROR] Raw output:\n{raw[:300]}")
        return {}

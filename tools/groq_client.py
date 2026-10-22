import os
import re
import time
import threading
from dotenv import load_dotenv
from openai import OpenAI
from openai import OpenAIError
import sys

# Force UTF-8 encoding for standard output/error on Windows to prevent console print crashes with emojis/unicode
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Load environment variables from .env file
load_dotenv(override=True)

# -----------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------
PRIMARY_MODEL  = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"
ADDITIONAL_MODELS = ["mixtral-8x7b-32768", "gemma2-9b-it"]

MAX_COMPLETION_TOKENS = 4000
PROMPT_CHAR_LIMIT = 28_000

MAX_RETRIES = 3
BASE_DELAY  = 4   # seconds for first retry

_rate_limit_lock = threading.Lock()
_api_keys: list[str] | None = None

def _load_api_keys() -> list[str]:
    """
    Reads ALL Groq API keys defined in environment / .env file / SQLite auth database.
    Returns deduplicated list of valid Groq keys in priority order (primary, backup #2, backup #3, etc.).
    """
    keys = []
    raw_keys = []

    # Always fetch latest system settings from SQLite auth database
    settings = {}
    try:
        from database.auth_db import get_all_system_settings
        settings = get_all_system_settings()
    except Exception:
        pass

    primary = settings.get("GROQ_API_KEY", "").strip() or os.getenv("GROQ_API_KEY", "").strip()
    if primary and not primary.startswith("YOUR_"):
        raw_keys.append(primary)

    for i in range(2, 10):
        extra = settings.get(f"GROQ_API_KEY_{i}", "").strip() or os.getenv(f"GROQ_API_KEY_{i}", "").strip()
        if extra and not extra.startswith("YOUR_") and extra not in raw_keys:
            raw_keys.append(extra)

    for k in raw_keys:
        # Filter out keys that clearly belong to other providers (e.g., xai-, AIza, sk-)
        if k.startswith("xai-") or k.startswith("AIza") or (k.startswith("sk-") and not k.startswith("gsk_")):
            continue
        keys.append(k)

    return keys


def _make_client(api_key: str) -> OpenAI:
    """Returns an OpenAI SDK client pointed at the Groq API endpoint with strict timeout."""
    return OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        timeout=35.0,
        max_retries=1
    )


def _get_api_keys() -> list[str]:
    global _api_keys
    if _api_keys is None:
        load_dotenv(override=True)
        _api_keys = _load_api_keys()
    return _api_keys

def _invalidate_key_cache():
    """Call this when settings are updated or keys change."""
    global _api_keys
    _api_keys = None

def _parse_wait_seconds(error_message: str) -> float:
    match = re.search(r"try again in\s*(?:(\d+)m)?(\d+(?:\.\d+)?)s", str(error_message))
    if match:
        minutes = int(match.group(1)) if match.group(1) else 0
        seconds = float(match.group(2))
        return minutes * 60 + seconds
    return float(BASE_DELAY)

def _truncate_prompt(prompt: str) -> str:
    if len(prompt) <= PROMPT_CHAR_LIMIT:
        return prompt
    half = PROMPT_CHAR_LIMIT // 2
    return (
        prompt[:half]
        + "\n\n[... content truncated to fit token budget ...]\n\n"
        + prompt[-half:]
    )

def _is_daily_quota_error(error_str: str) -> bool:
    s = str(error_str).lower()
    if "429" in s or "rate_limit_exceeded" in s or "quota" in s:
        if any(term in s for term in ["tokens per day", "tpd", "requests per day", "rpd", "daily", "per day", "day"]):
            return True
        # If wait time is > 60 seconds (or minutes), it is a daily/long-term quota
        if _parse_wait_seconds(error_str) > 60:
            return True
    return False

def _is_per_minute_quota_error(error_str: str) -> bool:
    if _is_daily_quota_error(error_str):
        return False
    s = str(error_str).lower()
    return ("429" in s or "rate_limit_exceeded" in s) and _parse_wait_seconds(error_str) <= 60

def _is_permanent_error(error_str: str) -> bool:
    if "429" in error_str or "rate_limit_exceeded" in error_str:
        return False
    return (
        "400" in error_str
        or "401" in error_str
        or "invalid_api_key" in error_str
        or "model_decommissioned" in error_str
    )

# -----------------------------------------------------------------------
# Fallback Providers (Gemini & OpenAI & xAI)
# -----------------------------------------------------------------------

def _load_gemini_keys() -> list[str]:
    """Load all Gemini API keys from environment (GEMINI_API_KEY, GOOGLE_API_KEY, GEMINI_API_KEY_2, etc.)."""
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
        try:
            from database.auth_db import sync_settings_to_env
            sync_settings_to_env()
        except Exception:
            pass

    keys = []
    for var in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        primary = os.getenv(var, "").strip()
        if primary and not primary.startswith("YOUR_") and primary not in keys:
            keys.append(primary)
    for i in range(2, 10):
        extra = os.getenv(f"GEMINI_API_KEY_{i}", "").strip()
        if extra and not extra.startswith("YOUR_") and extra not in keys:
            keys.append(extra)
    return keys

def _try_gemini_fallback(prompt: str) -> str | None:
    gemini_keys = _load_gemini_keys()
    if not gemini_keys:
        return None
    
    import google.generativeai as genai
    
    candidate_models = ["gemini-flash-latest", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"]
    
    for key_idx, gemini_key in enumerate(gemini_keys):
        key_label = f"Gemini Key #{key_idx + 1}" if len(gemini_keys) > 1 else "Gemini key"
        genai.configure(api_key=gemini_key)
        
        for model_name in candidate_models:
            try:
                model = genai.GenerativeModel(model_name)
                resp = model.generate_content(prompt, request_options={"timeout": 30.0})
                if resp and resp.text:
                    print(f"[Groq Client] Successfully used Google Gemini model ({model_name}) with {key_label}.")
                    return resp.text
            except Exception as e:
                error_str = str(e)
                # Per-minute rate limit — wait briefly and retry same key
                if "429" in error_str and "per" in error_str.lower() and "minute" in error_str.lower():
                    wait_match = re.search(r"(\d+(?:\.\d+)?)s", error_str)
                    wait_secs = min(float(wait_match.group(1)) if wait_match else 5, 10)
                    print(f"[Gemini] ⏳ Per-minute limit on '{model_name}' ({key_label}). Waiting {wait_secs:.0f}s...")
                    time.sleep(wait_secs)
                    try:
                        resp = model.generate_content(prompt)
                        if resp and resp.text:
                            print(f"[Groq Client] Successfully used Google Gemini model ({model_name}) with {key_label} after wait.")
                            return resp.text
                    except Exception as e2:
                        print(f"[Gemini Model '{model_name}' Retry Error ({key_label})]: {e2}")
                # Daily quota or key-level quota — rotate to next key
                elif "429" in error_str or "quota" in error_str.lower():
                    print(f"[Gemini] ⚠️ Quota exhausted for '{model_name}' ({key_label}). Trying next key...")
                    break  # break out of model loop, try next key
                else:
                    print(f"[Gemini Model '{model_name}' Error ({key_label})]: {e}")
                    continue  # try next model with same key
        else:
            # All models failed for this key without quota error — don't try more keys
            continue
    
    return None

def _try_openai_fallback(prompt: str) -> str | None:
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_key or openai_key.startswith("YOUR_") or openai_key.startswith("xai-"):
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=MAX_COMPLETION_TOKENS
        )
        if resp.choices and resp.choices[0].message.content:
            print("[Groq Client] Successfully fell back to OpenAI GPT model.")
            return resp.choices[0].message.content
    except Exception as e:
        print(f"[OpenAI Fallback Error]: {e}")
    return None

def _try_xai_fallback(prompt: str) -> str | None:
    xai_key = os.getenv("XAI_API_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip() or os.getenv("GROQ_API_KEY", "").strip()
    if not xai_key or not xai_key.startswith("xai-"):
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=xai_key, base_url="https://api.x.ai/v1")
        for model in ["grok-4.5", "grok-2-1212", "grok-2", "grok-beta"]:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=MAX_COMPLETION_TOKENS
                )
                if resp.choices and resp.choices[0].message.content:
                    print(f"[Groq Client] Successfully used xAI Grok model ({model}).")
                    return resp.choices[0].message.content
            except Exception as e:
                print(f"[xAI Model '{model}' Error]: {e}")
                if "permission" in str(e).lower() or "403" in str(e) or "quota" in str(e).lower():
                    break
                continue
    except Exception as e:
        print(f"[xAI Fallback Error]: {e}")
    return None

def _try_deepseek_fallback(prompt: str) -> str | None:
    """Fallback to DeepSeek via official API or NVIDIA NIM when Groq and Gemini reach rate limits."""
    
    # Strategy 1: Try official DeepSeek API (sk-... keys → https://api.deepseek.com)
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if deepseek_key and not deepseek_key.startswith("YOUR_") and not deepseek_key.startswith("nvapi-"):
        try:
            from openai import OpenAI
            base_url = os.getenv("DEEPSEEK_BASE_URL", "").strip() or "https://api.deepseek.com"
            client = OpenAI(api_key=deepseek_key, base_url=base_url, timeout=25.0)
            for model in ["deepseek-chat", "deepseek-reasoner"]:
                try:
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=MAX_COMPLETION_TOKENS,
                        temperature=0.7
                    )
                    if resp.choices and resp.choices[0].message.content:
                        print(f"[Groq Client] Successfully used DeepSeek model ({model}) via official API.")
                        return resp.choices[0].message.content
                except Exception as e:
                    print(f"[DeepSeek Official '{model}' Error]: {e}")
                    err_lower = str(e).lower()
                    if "quota" in err_lower or "401" in err_lower or "402" in err_lower or "unauthorized" in err_lower or "balance" in err_lower or "insufficient" in err_lower:
                        break
                    continue
        except Exception as e:
            print(f"[DeepSeek Official Fallback Error]: {e}")

    # Strategy 2: Try NVIDIA NIM endpoint (nvapi-... keys → https://integrate.api.nvidia.com/v1)
    nvidia_key = os.getenv("NVIDIA_API_KEY", "").strip()
    if nvidia_key and nvidia_key.startswith("nvapi-"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=nvidia_key, base_url="https://integrate.api.nvidia.com/v1", timeout=25.0)
            for model in ["deepseek-ai/deepseek-v4.1-flash", "deepseek-ai/deepseek-v3", "deepseek-ai/deepseek-r1"]:
                try:
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=MAX_COMPLETION_TOKENS,
                        temperature=0.7
                    )
                    if resp.choices and resp.choices[0].message.content:
                        print(f"[Groq Client] Successfully used DeepSeek model ({model}) via NVIDIA NIM.")
                        return resp.choices[0].message.content
                except Exception as e:
                    print(f"[NVIDIA NIM '{model}' Error]: {e}")
                    err_lower = str(e).lower()
                    if "quota" in err_lower or "401" in err_lower or "unauthorized" in err_lower:
                        break
                    continue
        except Exception as e:
            print(f"[NVIDIA NIM Fallback Error]: {e}")

    return None


# -----------------------------------------------------------------------
# Core Public Function
# -----------------------------------------------------------------------

def ask_groq(prompt: str, max_tokens: int = MAX_COMPLETION_TOKENS) -> str:
    """
    Sends prompt to Groq API with multi-key rotation and multi-provider fallback.
    """
    prompt = _truncate_prompt(prompt)

    try:
        api_keys = _get_api_keys()
    except Exception as e:
        api_keys = []

    num_keys = len(api_keys)
    last_error = None
    exhausted_keys = 0

    if num_keys > 0:
        for key_idx, api_key in enumerate(api_keys):
            key_label = f"Key #{key_idx + 1}" if num_keys > 1 else "API key"
            client = _make_client(api_key)
            key_failed = False

            models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL] + ADDITIONAL_MODELS

            for model in models_to_try:
                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        response = client.chat.completions.create(
                            model=model,
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=max_tokens,
                            temperature=0.7,
                        )
                        if key_idx > 0:
                            print(f"[Groq Client] 🔑 Successfully completed request using Backup Key #{key_idx + 1}!")
                        return response.choices[0].message.content

                    except OpenAIError as e:
                        error_str = str(e)
                        last_error = e

                        if _is_daily_quota_error(error_str):
                            print(f"[Groq Client] ⚠️ Daily quota exhausted for '{model}' ({key_label}).")
                            key_failed = True
                            break

                        elif _is_permanent_error(error_str):
                            print(f"[Groq Client] ❌ Auth / Key error on '{model}' ({key_label}): {e}")
                            last_error = e
                            key_failed = True
                            break

                        elif _is_per_minute_quota_error(error_str):
                            wait_secs = min(_parse_wait_seconds(error_str), 6)
                            print(f"[Groq Client] ⏳ Per-minute limit on '{model}' ({key_label}). Waiting {wait_secs:.0f}s...")
                            time.sleep(wait_secs)

                        else:
                            delay = BASE_DELAY * (2 ** (attempt - 1))
                            print(f"[Groq Client] ⚠️ Transient error on '{model}' ({key_label}): {e}. Retrying in {delay}s...")
                            time.sleep(delay)

                    except Exception as e:
                        last_error = e
                        delay = BASE_DELAY * (2 ** (attempt - 1))
                        print(f"[Groq Client] ⚠️ Unexpected error ({attempt}): {e}. Retrying in {delay}s...")
                        time.sleep(delay)

                # If this key is exhausted or invalid, do not waste time trying other models on this dead key
                if key_failed:
                    break

            if key_failed:
                exhausted_keys += 1
                if key_idx + 1 < num_keys:
                    print(f"[Groq Client] 🔄 Automatically switching from {key_label} to Backup Key #{key_idx + 2}...")
                    continue


    # Try Gemini fallback
    gemini_res = _try_gemini_fallback(prompt)
    if gemini_res:
        return gemini_res

    # Try DeepSeek (NVIDIA NIM) fallback when Gemini limit is reached
    deepseek_res = _try_deepseek_fallback(prompt)
    if deepseek_res:
        return deepseek_res

    # Try xAI (Grok) fallback
    xai_res = _try_xai_fallback(prompt)
    if xai_res:
        return xai_res

    # Try OpenAI fallback
    openai_res = _try_openai_fallback(prompt)
    if openai_res:
        return openai_res

    # All providers failed or no keys set
    _invalidate_key_cache()

    has_any_key = (
        bool(os.getenv("GROQ_API_KEY"))
        or bool(os.getenv("GEMINI_API_KEY"))
        or bool(os.getenv("GOOGLE_API_KEY"))
        or bool(os.getenv("NVIDIA_API_KEY"))
        or bool(os.getenv("DEEPSEEK_API_KEY"))
        or bool(os.getenv("OPENAI_API_KEY"))
        or bool(os.getenv("XAI_API_KEY"))
    )

    if not has_any_key:
        return (
            "⚠️ **No API Key Configured.**\n\n"
            "Please go to the **Settings** tab in the sidebar and enter your **Groq API Key** "
            "(or Gemini / DeepSeek / OpenAI key) to enable AI research execution."
        )

    err_str = str(last_error) if last_error else ""
    if exhausted_keys > 0 and (exhausted_keys == num_keys or _is_daily_quota_error(err_str)):
        wait_hint = _parse_wait_seconds(err_str)
        minutes = int(wait_hint // 60)
        seconds = int(wait_hint % 60)
        return (
            f"⚠️ **Daily Groq API Quota Reached.**\n\n"
            f"Your key reached its daily limit. Resets in approximately **{minutes}m {seconds}s**.\n\n"
            f"Please enter a secondary Groq key or Gemini / OpenAI key in the **Settings** tab."
        )

    return (
        "⚠️ **Invalid API Key configured.**\n\n"
        "The API key in your **Settings** tab was rejected by the AI provider (e.g. invalid key format or wrong key for the provider).\n\n"
        "• **Groq keys** start with `gsk_` (get a free key at https://console.groq.com/keys)\n"
        "• **Gemini keys** start with `AIzaSy` or `AQ.` (get a free key at https://aistudio.google.com/app/apikey)"
    )

def get_groq_client() -> OpenAI:
    return _make_client(_get_api_keys()[0])

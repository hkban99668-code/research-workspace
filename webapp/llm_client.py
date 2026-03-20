"""
Unified LLM client — supports Anthropic API and OpenAI-compatible APIs (Qwen/DashScope, OpenAI, etc.)
Provider is auto-detected from model name, or can be specified explicitly.
"""
import requests

ANTHROPIC_API   = "https://api.anthropic.com/v1/messages"
QWEN_API_BASE   = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
OPENAI_API_BASE = "https://api.openai.com/v1/chat/completions"

_TIMEOUT = 120


def detect_provider(model: str) -> str:
    m = model.lower()
    if m.startswith("claude"):
        return "anthropic"
    if m.startswith("qwen") or m.startswith("qwq"):
        return "qwen"
    return "openai"


def call_llm(
    model: str,
    messages: list,
    system: str = "",
    api_key: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    provider: str = "",
    base_url: str = "",
) -> str:
    """
    Call LLM and return response text.
    Raises requests.HTTPError or RuntimeError on failure.
    """
    if not provider:
        provider = detect_provider(model)

    if provider == "anthropic":
        return _call_anthropic(model, messages, system, api_key, temperature, max_tokens)
    else:
        url = base_url or (QWEN_API_BASE if provider == "qwen" else OPENAI_API_BASE)
        return _call_openai_compat(model, messages, system, api_key, temperature, max_tokens, url)


def _call_anthropic(model, messages, system, api_key, temperature, max_tokens):
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    if system:
        payload["system"] = system

    resp = requests.post(
        ANTHROPIC_API,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json=payload,
        timeout=_TIMEOUT,
    )
    _raise_with_msg(resp)
    return resp.json()["content"][0]["text"]


def _call_openai_compat(model, messages, system, api_key, temperature, max_tokens, url):
    all_messages = []
    if system:
        all_messages.append({"role": "system", "content": system})
    all_messages.extend(messages)

    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": all_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=_TIMEOUT,
    )
    _raise_with_msg(resp)
    return resp.json()["choices"][0]["message"]["content"]


def _raise_with_msg(resp):
    if not resp.ok:
        try:
            err = resp.json()
            msg = (
                err.get("error", {}).get("message")
                or err.get("message")
                or str(err)
            )
        except Exception:
            msg = resp.text[:200]
        raise requests.HTTPError(f"[{resp.status_code}] {msg}", response=resp)

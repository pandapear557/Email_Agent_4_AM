"""
AI 제공자 계층 — 여러 AI를 같은 인터페이스로 갈아끼우고 테스트한다.

각 제공자는 generate(system, user, model, key) -> str 하나로 추상화된다.
새 제공자(OpenAI 등)를 붙이려면 아래 PROVIDERS 등록표에 항목 하나만 추가하면 되고,
app.py는 손대지 않는다. 이게 "엔진 교체 가능" 원칙의 AI 버전이다.

필요 시크릿(st.secrets) — 쓰려는 제공자 것만 있으면 된다:
  GEMINI_API_KEY    = "..."         # Google AI Studio (무료 티어) https://aistudio.google.com/apikey
  ANTHROPIC_API_KEY = "sk-ant-..."  # Anthropic Console            https://console.anthropic.com
"""

import streamlit as st


def _get_secret(name: str):
    """시크릿을 안전하게 읽는다(secrets.toml 부재 시 예외 대신 None)."""
    try:
        return st.secrets.get(name, None)
    except Exception:
        return None


# ----------------------------------------------------------------------------
# 제공자별 호출 함수 — 시그니처는 모두 (system, user, model, key) -> str 로 통일
# (SDK는 함수 안에서 지연 import → 안 쓰는 제공자 패키지가 없어도 앱은 뜬다)
# ----------------------------------------------------------------------------
def _gemini_generate(system: str, user: str, model: str, key: str) -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=key)
    resp = client.models.generate_content(
        model=model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=2000,
        ),
    )
    return (resp.text or "").strip()


def _anthropic_generate(system: str, user: str, model: str, key: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=key)
    resp = client.messages.create(
        model=model,
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()


# ----------------------------------------------------------------------------
# 제공자 등록표 — 새 AI는 여기 한 줄(블록) 추가하면 끝.
# ----------------------------------------------------------------------------
PROVIDERS = {
    "Gemini (Google)": {
        "secret": "GEMINI_API_KEY",
        "models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-1.5-flash"],
        "generate": _gemini_generate,
        "help": "Google AI Studio에서 무료 키 발급: https://aistudio.google.com/apikey",
    },
    "Claude (Anthropic)": {
        "secret": "ANTHROPIC_API_KEY",
        "models": ["claude-sonnet-4-6", "claude-opus-4-8", "claude-haiku-4-5-20251001"],
        "generate": _anthropic_generate,
        "help": "Anthropic Console에서 키 발급: https://console.anthropic.com",
    },
}

# 기본 제공자 = Gemini (무료 티어가 있어 키 없이도 바로 시작 가능)
DEFAULT_PROVIDER = "Gemini (Google)"


# ----------------------------------------------------------------------------
# app.py가 쓰는 공개 API
# ----------------------------------------------------------------------------
def provider_names() -> list:
    return list(PROVIDERS.keys())


def models_for(provider: str) -> list:
    return PROVIDERS[provider]["models"]


def secret_name(provider: str) -> str:
    return PROVIDERS[provider]["secret"]


def provider_help(provider: str) -> str:
    return PROVIDERS[provider].get("help", "")


def provider_ready(provider: str) -> bool:
    """선택된 제공자의 키가 설정돼 있으면 True."""
    return bool(_get_secret(secret_name(provider)))


def generate(provider: str, system: str, user: str, model: str) -> str:
    """선택된 제공자로 텍스트를 생성한다. 키 없으면 어디서 받는지까지 안내하는 에러."""
    spec = PROVIDERS.get(provider)
    if spec is None:
        raise ValueError(f"알 수 없는 AI 제공자: {provider}")
    key = _get_secret(spec["secret"])
    if not key:
        raise RuntimeError(
            f"{spec['secret']}가 없습니다. Secrets에 등록하세요. {spec.get('help', '')}"
        )
    return spec["generate"](system, user, model, key)

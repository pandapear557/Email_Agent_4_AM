"""
이력 영구 저장 — Supabase 백엔드 (엔진 교체 가능하게 분리된 저장소 계층).

대시보드의 실행 이력(runs)을 접속 세션이 아니라 외부 DB에 보관한다.
Supabase 시크릿이 없으면 모든 함수가 '비활성'으로 조용히 동작하므로,
(키 없는 단계에서도) 앱은 그대로 뜨고 이력만 세션 한정으로 남는다. = 점진적 도입.

필요 시크릿 (st.secrets):
  SUPABASE_URL = "https://xxxx.supabase.co"
  SUPABASE_KEY = "ey..."        # anon public key 로 충분 (RLS 정책은 schema 참고)

테이블 스키마는 supabase_schema.sql 참고. 저장소를 다른 엔진(Sheet 등)으로
바꾸더라도 아래 3개 함수 시그니처만 유지하면 app.py는 손대지 않아도 된다.
  db_enabled() -> bool
  load_runs()  -> list[dict] | None
  save_run(record: dict) -> bool
"""

import streamlit as st

# DB에 저장/복원하는 실행 기록 필드 (app.py의 record 구조와 일치)
RUN_FIELDS = (
    "time", "filename", "s_input", "s_draft", "s_format",
    "status", "draft_md", "gmail_html",
)


def _get_secret(name: str):
    """시크릿을 안전하게 읽는다(없으면 None). secrets.toml 부재 시 예외 방지."""
    try:
        return st.secrets.get(name, None)
    except Exception:
        return None


@st.cache_resource(show_spinner=False)
def _client():
    """Supabase 클라이언트(없으면 None). cache_resource로 세션 간 1개만 유지."""
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_KEY")
    if not url or not key:
        return None
    from supabase import create_client
    return create_client(url, key)


def db_enabled() -> bool:
    """Supabase 시크릿이 설정되어 영구 저장이 켜져 있으면 True."""
    return _client() is not None


def load_runs():
    """DB에서 실행 이력을 시간순(오래된→최신)으로 읽어온다.

    DB 미설정이면 None(=세션 모드로 폴백 신호). 설정됐는데 비었으면 [].
    """
    sb = _client()
    if sb is None:
        return None
    res = sb.table("runs").select("*").order("id", desc=False).execute()
    return res.data or []


def save_run(record: dict) -> bool:
    """실행 기록 한 건을 DB에 저장. 성공 True / 미설정 False / 실패는 예외."""
    sb = _client()
    if sb is None:
        return False
    row = {k: record.get(k) for k in RUN_FIELDS}
    sb.table("runs").insert(row).execute()
    return True

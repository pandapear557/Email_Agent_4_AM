"""
메일 초안 스튜디오 — 회의록을 메일 초안으로 바꾸는 파이프라인 + 대시보드.

흐름(엔진은 이 앱이 직접 돌림 = v1):
  1) 입력   : DocX/MD 업로드 -> 본문 텍스트 추출
  2) 초안   : Claude API가 지침대로 메일 초안(Markdown) 작성
  3) 서식   : Markdown -> Gmail 붙여넣기용 HTML

"현황" 탭이 곧 운용 대시보드: 실행 이력과 단계별 상태를 한 화면에서 본다.
나중에 백그라운드 자동화가 필요해지면 1~3단계만 n8n으로 넘기고
이 대시보드는 그 상태를 읽어다 그대로 보여주면 된다(대시보드는 안 바뀜).
"""

import io
import datetime as dt
import markdown as md_lib
import streamlit as st

import db  # 이력 영구 저장 계층 (Supabase). 미설정이면 자동으로 세션 모드.

# ----------------------------------------------------------------------------
# 기본 설정
# ----------------------------------------------------------------------------
st.set_page_config(page_title="메일 초안 스튜디오", page_icon="✉️", layout="wide")

DEFAULT_MODEL = "claude-sonnet-4-6"
MODELS = ["claude-sonnet-4-6", "claude-opus-4-8", "claude-haiku-4-5-20251001"]

DEFAULT_INSTRUCTIONS = (
    "당신은 사용자의 비서입니다. 아래 회의록을 바탕으로 한국어 업무 메일 초안을 씁니다.\n"
    "- 받는 사람이 5초 안에 핵심을 파악하게 첫 문단에 요점을 둔다.\n"
    "- 결정 사항, 요청 사항, 마감일을 명확히 구분한다.\n"
    "- 군더더기 없이 정중하고 간결하게.\n"
    "- 출력은 Markdown. 첫 줄은 '제목: ...' 형식의 메일 제목으로 시작한다."
)

def get_secret(name: str):
    """시크릿을 안전하게 읽는다.

    Streamlit은 secrets.toml이 아예 없으면 st.secrets 접근 시 예외를 던진다.
    키를 안 넣고 대시보드만 볼 때(예: Claude Desktop 수제작 단계)도 앱이
    떠야 하므로, 없으면 None을 돌려준다. 시크릿은 여전히 st.secrets로만 읽는다.
    """
    try:
        return st.secrets.get(name, None)
    except Exception:
        return None


# 실행 이력: Supabase가 설정돼 있으면 DB에서 복원, 아니면 세션 한정.
# 세션 첫 진입 때 한 번만 로드하고, 이후엔 메모리 + DB에 함께 적재한다.
if "runs" not in st.session_state:
    st.session_state.runs = []        # 완료/진행된 실행 기록
    st.session_state.db_error = None
    try:
        loaded = db.load_runs()       # DB 미설정이면 None
        if loaded is not None:
            st.session_state.runs = loaded
    except Exception as e:
        # 테이블 미생성 등 — 앱은 계속 뜨고 세션 모드로 동작
        st.session_state.db_error = str(e)
if "instructions" not in st.session_state:
    st.session_state.instructions = DEFAULT_INSTRUCTIONS


def persist_run(record: dict) -> None:
    """실행 기록을 화면(세션)과 DB에 함께 남긴다.

    DB 저장이 실패해도 화면 이력은 유지된다(운용이 멈추지 않게).
    DB 미설정이면 save_run이 조용히 False를 반환하고 세션에만 남는다.
    """
    st.session_state.runs.append(record)
    try:
        db.save_run(record)
    except Exception as e:
        st.warning(f"이력 DB 저장 실패(화면에는 남아 있음): {e}")


# ----------------------------------------------------------------------------
# 단계별 함수 (각 단계는 갈아끼울 수 있게 독립 함수로)
# ----------------------------------------------------------------------------
def parse_input(uploaded_file) -> str:
    """1단계: 업로드 파일에서 본문 텍스트(또는 Markdown)를 뽑아낸다."""
    name = uploaded_file.name.lower()
    data = uploaded_file.read()
    if name.endswith(".md") or name.endswith(".txt"):
        return data.decode("utf-8", errors="replace")
    if name.endswith(".docx"):
        from docx import Document  # python-docx
        doc = Document(io.BytesIO(data))
        lines = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(lines)
    raise ValueError(f"지원하지 않는 형식입니다: {uploaded_file.name} (DocX, MD, TXT만 됩니다)")


def draft_email(notes: str, context: str, model: str) -> str:
    """2단계: Claude가 회의록 + 추가 맥락으로 메일 초안(Markdown)을 만든다."""
    key = get_secret("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY가 없습니다. Streamlit Cloud 앱 설정의 Secrets에 등록하세요. "
            "(README의 Secrets 섹션 참고)"
        )
    import anthropic
    client = anthropic.Anthropic(api_key=key)
    user_content = f"# 회의록\n{notes}\n\n# 이번 메일 맥락\n{context or '(추가 맥락 없음)'}"
    resp = client.messages.create(
        model=model,
        max_tokens=2000,
        system=st.session_state.instructions,
        messages=[{"role": "user", "content": user_content}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()


def format_gmail_html(draft_md: str) -> str:
    """3단계: Markdown -> Gmail 붙여넣기용 HTML. Gmail은 <style>를 떼므로 인라인 스타일을 쓴다."""
    html = md_lib.markdown(draft_md, extensions=["extra", "sane_lists", "nl2br"])
    # 흔한 태그에 인라인 스타일을 얹어 Gmail에서도 모양이 유지되게 한다.
    inline = {
        "<h1>": '<h1 style="font:600 20px/1.4 Arial,sans-serif;margin:0 0 12px;">',
        "<h2>": '<h2 style="font:600 17px/1.4 Arial,sans-serif;margin:18px 0 8px;">',
        "<h3>": '<h3 style="font:600 15px/1.4 Arial,sans-serif;margin:14px 0 6px;">',
        "<p>": '<p style="font:14px/1.6 Arial,sans-serif;margin:0 0 10px;color:#202124;">',
        "<ul>": '<ul style="font:14px/1.6 Arial,sans-serif;margin:0 0 10px;padding-left:20px;">',
        "<ol>": '<ol style="font:14px/1.6 Arial,sans-serif;margin:0 0 10px;padding-left:20px;">',
        "<li>": '<li style="margin:0 0 4px;">',
        "<a ": '<a style="color:#1a73e8;text-decoration:none;" ',
    }
    for tag, styled in inline.items():
        html = html.replace(tag, styled)
    return f'<div style="font:14px/1.6 Arial,sans-serif;color:#202124;">{html}</div>'


# ----------------------------------------------------------------------------
# 사이드바 — 설정과 키 상태
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 설정")
    model = st.selectbox("초안 작성 모델", MODELS, index=MODELS.index(DEFAULT_MODEL))
    key_ok = bool(get_secret("ANTHROPIC_API_KEY"))
    st.markdown("**Claude API 키**")
    st.success("연결됨") if key_ok else st.warning("미설정 — Secrets에 등록 필요")
    st.markdown("**이력 저장소(DB)**")
    if db.db_enabled() and not st.session_state.get("db_error"):
        st.success("Supabase 연결됨 — 이력 영구 저장")
    elif db.db_enabled():
        # 설정은 됐는데 조회 실패 — 대개 테이블 미생성(schema SQL 미실행)
        st.warning(
            "Supabase 설정됨, 그러나 읽기 실패 — supabase_schema.sql을 "
            f"SQL Editor에 실행했는지 확인하세요.\n\n{st.session_state.db_error}"
        )
    else:
        st.info("미설정 — 이번 접속 세션에만 기록")
    st.markdown("---")
    st.markdown("### 작성 지침")
    st.caption("Claude Desktop의 프로젝트 지침에 해당. 여기서 바꾸면 다음 초안부터 반영됩니다.")
    st.session_state.instructions = st.text_area(
        "지침", value=st.session_state.instructions, height=220, label_visibility="collapsed"
    )


# ----------------------------------------------------------------------------
# 메인 — 두 탭: 현황(대시보드) / 새 초안 만들기
# ----------------------------------------------------------------------------
st.title("✉️ 메일 초안 스튜디오")

tab_dash, tab_run = st.tabs(["현황", "새 초안 만들기"])

# ---- 현황(운용 대시보드) ----------------------------------------------------
with tab_dash:
    runs = st.session_state.runs
    total = len(runs)
    done = sum(1 for r in runs if r["status"] == "완료")
    review = sum(1 for r in runs if r["status"] == "검토 대기")
    failed = sum(1 for r in runs if r["status"] == "실패")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 실행", total)
    c2.metric("완료", done)
    c3.metric("검토 대기", review)
    c4.metric("실패", failed)

    head_l, head_r = st.columns([4, 1])
    head_l.markdown("#### 실행 이력")
    # DB가 켜져 있으면 다른 기기/세션의 기록을 다시 불러올 수 있다.
    if db.db_enabled() and head_r.button("새로고침", use_container_width=True):
        try:
            st.session_state.runs = db.load_runs() or []
        except Exception as e:
            st.warning(f"새로고침 실패: {e}")
        st.rerun()
    if not runs:
        st.info("아직 실행 기록이 없습니다. '새 초안 만들기' 탭에서 회의록을 올려 시작하세요.")
    else:
        st.dataframe(
            [
                {
                    "시각": r["time"],
                    "파일": r["filename"],
                    "입력": r["s_input"],
                    "초안": r["s_draft"],
                    "서식": r["s_format"],
                    "상태": r["status"],
                }
                for r in reversed(runs)
            ],
            use_container_width=True,
            hide_index=True,
        )
        # 개별 실행 펼쳐서 결과 다시 보기
        for i, r in enumerate(reversed(runs)):
            if not r.get("draft_md"):
                continue
            with st.expander(f"{r['time']} · {r['filename']} — 초안 보기"):
                st.text_area("초안 (Markdown)", r["draft_md"], height=200, key=f"hist_md_{i}")
                if r.get("gmail_html"):
                    st.download_button(
                        "Gmail용 HTML 내려받기",
                        r["gmail_html"],
                        file_name="email.html",
                        mime="text/html",
                        key=f"hist_dl_{i}",
                    )

# ---- 새 초안 만들기 (파이프라인) -------------------------------------------
with tab_run:
    st.markdown("#### 1) 회의록 올리기")
    uploaded = st.file_uploader("DocX 또는 MD 파일", type=["docx", "md", "txt"])
    context = st.text_input(
        "이번 메일 맥락 (받는 사람·톤·핵심 요청 등 — 선택)",
        placeholder="예: 김부장님께, 정중하게, 다음 주 수요일 미팅 일정 확정 요청",
    )

    run = st.button("초안 만들기", type="primary", disabled=uploaded is None)

    if run and uploaded is not None:
        record = {
            "time": dt.datetime.now().strftime("%m-%d %H:%M"),
            "filename": uploaded.name,
            "s_input": "⏳", "s_draft": "⏳", "s_format": "⏳",
            "status": "진행 중", "draft_md": "", "gmail_html": "",
        }

        # 1단계: 입력
        try:
            with st.spinner("회의록 읽는 중…"):
                notes = parse_input(uploaded)
            record["s_input"] = "✅"
        except Exception as e:
            record["s_input"] = "⚠️"; record["status"] = "실패"
            persist_run(record)
            st.error(f"입력 단계 실패: {e}")
            st.stop()

        # 2단계: 초안
        try:
            with st.spinner("Claude가 초안 작성 중…"):
                draft_md = draft_email(notes, context, model)
            record["s_draft"] = "✅"; record["draft_md"] = draft_md
        except Exception as e:
            record["s_draft"] = "⚠️"; record["status"] = "실패"
            persist_run(record)
            st.error(f"초안 단계 실패: {e}")
            st.stop()

        # 3단계: 서식
        try:
            with st.spinner("Gmail 서식 입히는 중…"):
                gmail_html = format_gmail_html(draft_md)
            record["s_format"] = "✅"; record["gmail_html"] = gmail_html
        except Exception as e:
            record["s_format"] = "⚠️"; record["status"] = "검토 대기"
            persist_run(record)
            st.warning(f"서식 단계 실패(초안은 사용 가능): {e}")
            st.stop()

        record["status"] = "검토 대기"   # 메일은 보내기 전 사람이 검토하므로 '완료'가 아니라 '검토 대기'
        persist_run(record)

        # 결과 표시
        st.success("초안 생성 완료 — 검토 후 Gmail에 붙여넣으세요.")
        left, right = st.columns(2)
        with left:
            st.markdown("##### 초안 (Markdown)")
            st.text_area("draft", draft_md, height=360, label_visibility="collapsed")
        with right:
            st.markdown("##### Gmail 미리보기")
            st.markdown(
                f'<div style="border:1px solid #e0e0e0;border-radius:8px;padding:14px;">{gmail_html}</div>',
                unsafe_allow_html=True,
            )
            st.download_button(
                "Gmail용 HTML 내려받기", gmail_html, file_name="email.html", mime="text/html"
            )
            st.caption("내려받은 HTML을 브라우저로 열어 전체 복사 → Gmail 작성창에 붙여넣으면 서식이 유지됩니다.")

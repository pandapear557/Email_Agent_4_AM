# ✉️ 메일 초안 스튜디오 (Mail Draft Studio)

회의록(DocX/MD)을 업로드하면 → Claude가 업무 메일 초안을 쓰고 → Gmail 붙여넣기용 서식으로 바꿔주는,
**파이프라인 + 운용 대시보드**를 한 Streamlit 앱으로 묶은 도구.

## 흐름

```
업로드(DocX/MD) ─▶ [1 입력] 텍스트 추출 ─▶ [2 초안] Claude API ─▶ [3 서식] MD→Gmail HTML
                                                                       │
                                          "현황" 탭 = 운용 대시보드 ◀──┘
```

- **1 입력** `parse_input()` — DocX/MD/TXT에서 본문 텍스트 추출
- **2 초안** `draft_email()` — Claude API가 사이드바 지침대로 메일 초안(Markdown) 작성
- **3 서식** `format_gmail_html()` — Markdown → Gmail 붙여넣기용 인라인 스타일 HTML

각 단계는 독립 함수라 나중에 엔진(n8n 등)으로 갈아끼울 수 있습니다. 대시보드는 불변층입니다.

> 메일은 **사람이 검토 후 발송**합니다. 파이프라인은 "초안 + 검토 대기"까지만 자동화합니다.

## 화면

탭 2개로 구성됩니다.

- **현황** — 지표(총 실행/완료/검토 대기/실패) + 실행 이력 표 + 초안 다시 보기
- **새 초안 만들기** — 업로드 → 단계 실행 → 초안 + Gmail 미리보기 + HTML 내려받기

## 로컬 실행

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # 키 입력
streamlit run app.py
```

## Secrets

API 키는 코드에 절대 적지 않고 `st.secrets`로만 참조합니다.

| 이름 | 설명 | 없으면 |
| --- | --- | --- |
| `GEMINI_API_KEY` | Gemini 키 — [무료 발급](https://aistudio.google.com/apikey) | Gemini 선택 시 초안 생성만 막힘 |
| `ANTHROPIC_API_KEY` | Claude 키 (`sk-ant-...`) | Claude 선택 시 초안 생성만 막힘 |
| `SUPABASE_URL` | Supabase 프로젝트 URL | 이력이 세션 한정(영구 저장 안 됨) |
| `SUPABASE_KEY` | Supabase anon public key | 〃 |

모든 시크릿은 선택입니다. 없으면 해당 기능만 꺼지고 앱은 그대로 뜹니다(점진적 도입).
**AI 제공자는 쓰려는 것의 키만** 있으면 됩니다(예: Gemini만 쓰면 `GEMINI_API_KEY`만).

### AI 제공자 (여러 AI 갈아끼우기)

초안 작성 엔진은 `providers.py`로 분리돼 있어 사이드바에서 **제공자/모델을 골라 바로 비교 테스트**할 수 있습니다. 기본은 무료 티어가 있는 **Gemini**. 새 AI(OpenAI 등)를 붙이려면 `providers.py`의 `PROVIDERS` 등록표에 블록 하나만 추가하면 되고, `app.py`는 손대지 않습니다. 각 실행이 어떤 AI·모델로 만들어졌는지는 현황 이력에 함께 기록됩니다.

- **로컬**: `.streamlit/secrets.toml`에 입력 (이 파일은 `.gitignore`로 커밋 금지)
- **Streamlit Cloud**: 앱 설정 > **Secrets** 화면에 같은 내용 붙여넣기

## 이력 영구 저장 (Supabase)

기본은 실행 이력이 `st.session_state`에 있어 **새로고침하면 사라집니다.** Supabase를 붙이면 이력이 외부 DB에 남아 기기·세션을 넘어 유지됩니다.

1. <https://supabase.com> 가입 → **New project** 생성 (무료).
2. 좌측 **SQL Editor**에 이 레포의 [`supabase_schema.sql`](supabase_schema.sql) 내용을 붙여넣고 **Run** — `runs` 테이블이 생깁니다.
3. **Project Settings > API**에서 **Project URL**과 **anon public** 키 복사.
4. Secrets에 `SUPABASE_URL` / `SUPABASE_KEY` 등록 (로컬은 `secrets.toml`, Cloud는 Secrets 화면).
5. 앱 사이드바 "이력 저장소(DB)"가 **"Supabase 연결됨"** 초록이면 성공. "현황" 탭의 **새로고침** 버튼으로 다른 기기 기록도 불러옵니다.

**무료 한도**: DB 500MB(텍스트 이력엔 사실상 무제한) · 전송 5GB/월 · 활성 프로젝트 2개. 단, **7일간 요청이 없으면 프로젝트가 자동 일시정지**되니(데이터는 보존) 가끔 접속해 깨워 주세요.

> 저장소 계층은 `db.py`로 분리돼 있어, 나중에 Google Sheet 등 다른 엔진으로 바꿔도 `db_enabled()/load_runs()/save_run()` 세 함수만 맞추면 `app.py`는 손대지 않아도 됩니다.

## 배포 (Streamlit Community Cloud)

푸시하면 라이브 URL이 자동 갱신됩니다(= CD). 별도 CI/CD 불필요.

1. 레포를 GitHub에 올린다(비공개 가능).
2. <https://share.streamlit.io> → GitHub 로그인 → Create app → 레포/`app.py` 지정.
3. 앱 설정 **Secrets**에 `ANTHROPIC_API_KEY = "sk-ant-..."` 붙여넣기. **키 입력은 사용자가 직접** 한다.
4. 이후 푸시할 때마다 자동 갱신.

## 로드맵 (필요할 때만, 우선순위 순)

1. ✅ **이력 영구 저장 (완료)** — Supabase 백엔드(`db.py`). 위 "이력 영구 저장" 절 참고.
2. **Gmail 초안 자동 생성** — Gmail API(OAuth) 연결해 버튼 하나로 임시보관함에 초안 생성. 발송은 항상 사람 검토 후. (필요 시크릿: Google OAuth 클라이언트)
3. **Drive 자동 입력** — 업로드 대신 Drive 폴더 폴링/선택. `parse_input` 앞단만 교체.
4. **n8n 이관(선택)** — 무인 트리거 자동화가 필요해지면 1~3단계를 n8n 워크플로로 옮기고, 대시보드는 n8n 실행 상태를 읽어 표시.

## 작업 규칙

- **단계 함수 독립 유지** — `parse_input`/`draft_email`/`format_gmail_html` 시그니처를 깨지 말 것.
- **시크릿은 `st.secrets`로만** — 키·토큰을 코드/레포/로그에 노출 금지.
- **메일 발송 자동화 금지** — 파이프라인은 '초안 + 검토 대기'까지.
- **대시보드 불변 원칙** — 엔진을 바꿔도 "현황" 화면의 역할(지표 + 이력 + 초안 보기)은 유지.
- **UI 문구는 행동 중심** — 무슨 일이 일어나는지 그대로. 에러는 무엇이 왜 실패했고 어떻게 고치는지 안내.

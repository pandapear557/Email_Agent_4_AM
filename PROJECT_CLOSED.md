# 🗂️ PROJECT CLOSED — 메일 초안 스튜디오

> **상태: 종료 (보류)** · 종료일 2026-06-22
> 이 문서 하나로 프로젝트를 안전하게 접고, 나중에 그대로 재개할 수 있게 인계한다.

---

## 1. 이 프로젝트가 뭐였나

회의록(DocX/MD)을 업로드하면 → AI가 업무 메일 초안을 쓰고 → Gmail 붙여넣기용 서식으로
바꿔주는 **파이프라인 + 운용 대시보드**를 한 Streamlit 앱으로 묶은 내부 도구.

- 흐름: `업로드 → [1 입력] 텍스트 추출 → [2 초안] AI 작성 → [3 서식] Gmail HTML → 현황 대시보드`
- 스택: Streamlit(Community Cloud) · Python · Gemini/Claude API · Supabase · python-docx
- 코드 위치: 브랜치 `claude/gallant-bardeen-ijj12s`, 최종 커밋 `5fcf0e2`

## 2. 왜 종료했나 (진짜 이유)

**코드 문제가 아니라 접근성 문제였다.** 회사 노트북에서 GitHub 코드베이스 접근이 막혀
개발을 이어갈 수 없었음. 여기에 결제·배포 잡무가 겹쳐 동력이 떨어짐.

- Streamlit 로그인/배포가 매끄럽지 않았고, Supabase 연동도 끝맺지 못함.
- Claude API는 결제가 거부되어 사용 불가 → Gemini(무료 티어)로 전환해 둔 상태.
- 흩어진 리소스(호스팅·DB·API키)를 한 곳에서 관리하고 싶다는 필요를 확인함.

## 3. 리소스 & 과금 점검 (종료 시점)

**결론: 실질 과금 위험 0.** 전부 무료 티어이거나 결제가 안 되어 있음.

| 리소스 | 상태 | 정리 조치 |
| --- | --- | --- |
| Anthropic API | 결제 거부됨 → 크레딧 없음, 청구 불가 | 만든 키 있으면 폐기(위생) |
| Gemini API | 무료 티어 = $0 (카드 불필요) | 만든 키 있으면 폐기 |
| Supabase | 무료 티어 = $0, 7일 후 자동 정지 | 프로젝트 만들었으면 삭제 |
| Streamlit Cloud | 무료 = $0, 앱이 라이브 상태일 수 있음 | 앱 삭제 또는 그대로 둠(무료) |
| GitHub | 무료 = $0 | 아카이브(읽기전용) 권장 |

✅ **레포 히스토리 전체 감사: 실제 키·토큰이 커밋된 적 없음** (플레이스홀더뿐). 유출 없음.

### 종료 체크리스트 (원할 때 수행)
- [ ] Gemini/Anthropic에서 만든 API 키 폐기
- [ ] Supabase 프로젝트 삭제 (만들었다면)
- [ ] Streamlit 앱 삭제 (선택 — 무료라 안 지워도 과금은 없음)
- [ ] GitHub 레포 **Archive** (Settings 맨 아래) — 읽기전용으로 격리, 기록 보존
- [ ] (Public으로 바꿨다면) 다시 Private 전환

## 4. 무엇을 만들었나 (완료된 것)

- ✅ v1 스캐폴딩 — 입력/초안/서식 3단계 독립 함수 + 현황/새 초안 탭
- ✅ 키 없이도 부팅 (점진적 도입) — 시크릿 있는 기능만 켜짐
- ✅ 이력 영구 저장 계층 `db.py` (Supabase) — 미설정 시 세션 모드 폴백
- ✅ 멀티 AI 제공자 `providers.py` — 기본 Gemini(무료), Claude 선택, 등록표에 한 줄로 추가
- ✅ 배포 버전 표시 — 헤더 밑 회색 커밋 해시(어느 커밋이 떠 있는지 즉시 확인)
- ✅ 핵심 파이프라인 실제 코드로 검증 완료

### 파일 구조
```
app.py                 # Streamlit 앱 (대시보드 + 파이프라인)
providers.py           # AI 제공자 계층 (Gemini/Claude…)
db.py                  # 이력 영구 저장 계층 (Supabase)
supabase_schema.sql    # runs 테이블 + RLS
requirements.txt
README.md
architecture.html      # 아키텍처 + 제언 시각화
dashboard_preview.html # 대시보드 정적 미리보기
.streamlit/secrets.toml.example
```

## 5. 배운 것 (Lessons Learned)

**잘한 것**
- **엔진 추상화가 프로젝트를 살렸다.** Claude 결제가 막혔을 때 `providers.py` 한 파일만
  바꿔 Gemini로 전환. "단일 벤더 하드 의존 금지 + 무료 폴백" 설계가 실전에서 증명됨.
- **점진적 도입(키 없어도 부팅)** — 크레덴셜 없이도 개발·시연을 이어갈 수 있었음.
- **스코프 절제** — 1인 내부 도구에 KMS·CI/CD·n8n을 넣지 않은 판단이 옳았음.

**아팠던 것 → 다음엔 이렇게**
- **배포 검증 장치를 1일차에.** "헤더에 커밋 해시 표시"를 늦게 넣어, Streamlit이 옛 빌드를
  붙잡고 있는 걸 눈치채는 데 시간을 버림. 배포형 프로젝트는 버전 표시부터.
- **외부 결제 의존은 시작 전에 확인.** 유료 API를 전제로 진행하다 결제가 막혀 방향을 틀었음.
  무료 티어가 있는 옵션(Gemini)을 처음부터 기본값으로.
- **관리형 호스팅의 자동 재배포를 맹신하지 말 것.** Streamlit Cloud가 푸시를 자동 반영하지
  않는 케이스가 있었음.
- **근본 원인은 접근성.** 회사 노트북↔코드베이스 접근 제약을 먼저 풀었어야 함.

## 6. 재개할 때의 방향 (다음 아키텍처)

> **개발은 맥북, 배포는 회사 AWS, 회사 노트북은 브라우저로 URL만 연다.**

```
맥북 (개발 + git push) → GitHub → AWS App Runner (자동 빌드·배포) → HTTPS URL
                                       ↑
                          SSM Parameter Store (API 키) — 무료
```

- **호스팅**: Streamlit Cloud → **AWS App Runner** (소스 레포 모드로 시작하면 Docker 불필요)
- **키 관리**: 흩어진 키 → **SSM Parameter Store(무료)** 로 통합. App Runner가 환경변수로 참조
  (키가 코드·로그에 안 보이고 ARN 참조만 저장).
- **DB**: 필요해지면 RDS(Postgres), 아니면 생략.
- **코드 이식 비용 거의 0**: 키 읽기가 `get_secret()` 한 곳에 모여 있어
  `st.secrets.get()` → `os.environ.get()` 한 줄만 바꾸면 됨. `providers.py`/`db.py`는 그대로 재사용.

**회사 AWS 주의**: IAM 권한 확보, 퍼블릭 노출이 보안정책에 걸리는지, 회의록(기밀 가능)을
외부 AI로 보내는 데이터 거버넌스 — 배포 전 보안팀 확인 필수. 너무 잠겨 있으면 Lightsail이 우회로.

## 7. 재개 방법

```bash
git fetch origin claude/gallant-bardeen-ijj12s
git checkout claude/gallant-bardeen-ijj12s
# 로컬 실행
pip install -r requirements.txt
streamlit run app.py           # 키 없어도 대시보드는 뜸
```

재개 시 첫 작업: **App Runner 배포 준비** (`Dockerfile` + `apprunner.yaml` 추가,
`get_secret`을 환경변수 방식으로 전환). 그다음 SSM에 키 넣고 App Runner 생성 → URL 확보.

---

*마지막 상태: 코드 정상 동작 검증 완료, 전부 커밋·푸시됨(`5fcf0e2`), 과금 위험 없음, 유출 없음.*

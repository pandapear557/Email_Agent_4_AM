-- 메일 초안 스튜디오 — 실행 이력 테이블
-- Supabase 대시보드 > SQL Editor 에 붙여넣고 Run 하세요.

create table if not exists public.runs (
    id          bigint generated always as identity primary key,
    created_at  timestamptz not null default now(),
    time        text,          -- 표시용 시각 "MM-DD HH:MM"
    filename    text,
    provider    text,          -- 사용한 AI 제공자 (예: Gemini (Google))
    model       text,          -- 사용한 모델 (예: gemini-2.5-flash)
    s_input     text,          -- 단계 상태 이모지 (✅ ⏳ ⚠️)
    s_draft     text,
    s_format    text,
    status      text,          -- 진행 중 / 검토 대기 / 실패
    draft_md    text,          -- 초안 원문(Markdown)
    gmail_html  text           -- Gmail 붙여넣기용 HTML
);

-- 이미 테이블을 만든 뒤라면(구버전) 아래 두 컬럼만 추가됨. 새로 만들면 무시됨.
alter table public.runs add column if not exists provider text;
alter table public.runs add column if not exists model    text;

-- 최신순 조회를 위한 인덱스
create index if not exists runs_id_desc on public.runs (id desc);

-- RLS(행 수준 보안) 켜기.
alter table public.runs enable row level security;

-- anon public key 만으로 읽기/쓰기를 허용하는 정책.
-- ⚠️ 이 앱은 단일 사용자 내부 도구를 전제로 한다. 다중 사용자/민감정보로
--    확장한다면 이 정책을 인증 기반으로 좁히고 service_role 키를 서버에서만 써야 한다.
drop policy if exists "anon can read runs"  on public.runs;
drop policy if exists "anon can write runs" on public.runs;

create policy "anon can read runs"
    on public.runs for select
    to anon
    using (true);

create policy "anon can write runs"
    on public.runs for insert
    to anon
    with check (true);

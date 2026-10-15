-- ==============================================================
-- 로보그램 코딩캠프 수료증 발급 시스템 - Supabase SQL Schema
-- ==============================================================

-- 1. 교육기관(학교/캠프) 정보 테이블
CREATE TABLE IF NOT EXISTS camp_institutions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,                -- 학교 또는 교육기관명 (예: 감정초등학교)
    course_name VARCHAR(150) NOT NULL,               -- 수업 과목명 (예: 잼S & 로블록스 4기 기초 과정)
    start_date DATE NOT NULL,                         -- 교육 시작일 (예: 2026-04-04)
    end_date DATE NOT NULL,                           -- 교육 종료일 (예: 2026-04-24)
    total_hours INTEGER NOT NULL DEFAULT 8,           -- 총 수업시간 (예: 8시간)
    issue_start_at TIMESTAMPTZ NOT NULL,              -- 수료증 출력 시작일시 (예: 2026-04-20 09:00:00+09)
    issue_end_at TIMESTAMPTZ NOT NULL,                -- 수료증 출력 마감일시 (예: 2026-05-31 23:59:59+09)
    issuer_name VARCHAR(100) DEFAULT '(주)로보그램',    -- 발급 기관명
    is_active BOOLEAN DEFAULT TRUE,                   -- 활성화 여부
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 캠프 수료 학생 정보 테이블
CREATE TABLE IF NOT EXISTS camp_students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID REFERENCES camp_institutions(id) ON DELETE CASCADE,
    school_name VARCHAR(100) NOT NULL,                -- 소속 학교명 (조회 성능 및 편의용)
    student_id VARCHAR(50) NOT NULL,                  -- 학생 로그인 아이디
    password VARCHAR(100) NOT NULL,                   -- 학생 로그인 비밀번호
    name VARCHAR(50) NOT NULL,                         -- 학생 성명 (예: 홍인희)
    photo_url TEXT,                                   -- 학생 본인 사진 (스토리지 URL 또는 Base64)
    is_issued BOOLEAN DEFAULT FALSE,                  -- 수료증 출력 여부
    first_issued_at TIMESTAMPTZ,                      -- 최초 발급 일시
    print_count INTEGER DEFAULT 0,                    -- 출력/다운로드 횟수
    memo TEXT,                                        -- 관리자 메모
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(school_name, student_id)
);

-- 3. 인덱스 생성 (빠른 검색 및 로그인)
CREATE INDEX IF NOT EXISTS idx_camp_students_login ON camp_students(school_name, student_id);
CREATE INDEX IF NOT EXISTS idx_camp_institutions_name ON camp_institutions(name);

-- 4. RLS (Row Level Security) 설정
ALTER TABLE camp_institutions ENABLE ROW LEVEL SECURITY;
ALTER TABLE camp_students ENABLE ROW LEVEL SECURITY;

-- 누구나 학교 목록 및 기본 수료 정보를 조회할 수 있도록 허용 (학생 로그인 및 검증용)
CREATE POLICY "Public Read Institutions" ON camp_institutions
    FOR SELECT USING (true);

-- 관리자 키/Service Role 또는 Anon 인증에 따른 수정 권한 (기본 앱용)
CREATE POLICY "Allow All on Institutions" ON camp_institutions
    FOR ALL USING (true) WITH CHECK (true);

-- 학생 정보 조회 (로그인 시 필요)
CREATE POLICY "Public Read Students" ON camp_students
    FOR SELECT USING (true);

-- 학생 사진 업데이트 및 출력 횟수 증가 허용
CREATE POLICY "Allow All on Students" ON camp_students
    FOR ALL USING (true) WITH CHECK (true);

-- 5. 샘플 테스트 데이터 삽입
INSERT INTO camp_institutions (name, course_name, start_date, end_date, total_hours, issue_start_at, issue_end_at)
VALUES 
('감정초등학교', '잼S & 로블록스 4기 기초 과정', '2026-04-04', '2026-04-24', 8, '2026-04-01 00:00:00+09', '2026-12-31 23:59:59+09'),
('인천외국어고등학교', 'AI 데이터사이언스 & 파이썬 심화 캠프', '2026-05-01', '2026-05-15', 16, '2026-05-15 00:00:00+09', '2026-12-31 23:59:59+09')
ON CONFLICT (name) DO NOTHING;

INSERT INTO camp_students (institution_id, school_name, student_id, password, name)
SELECT id, '감정초등학교', 'student01', '1234', '홍인희'
FROM camp_institutions WHERE name = '감정초등학교'
ON CONFLICT (school_name, student_id) DO NOTHING;

INSERT INTO camp_students (institution_id, school_name, student_id, password, name)
SELECT id, '감정초등학교', 'student02', '1234', '김민준'
FROM camp_institutions WHERE name = '감정초등학교'
ON CONFLICT (school_name, student_id) DO NOTHING;

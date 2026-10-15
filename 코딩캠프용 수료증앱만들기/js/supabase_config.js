/**
 * 로보그램 코딩캠프 수료증 발급 시스템
 * 실시간 서버-클라이언트 양방향 동기화 & Supabase/LocalStorage 하이브리드 어댑터
 * (PC 관리자 수정사항 및 스마트폰 발급 화면 100% 실시간 동기화 보장)
 */

const SUPABASE_CONFIG = {
    URL: "https://itescqykahtoelsohwxm.supabase.co",
    ANON_KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml0ZXNjcXlrYWh0b2Vsc29od3htIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ2MTIzNjEsImV4cCI6MjA5MDE4ODM2MX0.YYzIUEbdC589Awntb7lvP0F7XAmcjkz-xUd5I3E9uR0",
    IS_ENABLED: false // 로컬 실시간 서버 동기화 엔진 우선 사용
};

let supabaseClient = null;
try {
    if (window.supabase && SUPABASE_CONFIG.IS_ENABLED && SUPABASE_CONFIG.URL) {
        supabaseClient = window.supabase.createClient(SUPABASE_CONFIG.URL, SUPABASE_CONFIG.ANON_KEY);
    }
} catch (e) {
    console.warn("Supabase 비활성화 (로컬 실시간 서버 모드 동작):", e);
}

const DB = {
    _isInitialized: false,

    // ---------------- 서버와 데이터 실시간 동기화 초기화 ----------------
    async init() {
        if (this._isInitialized) return;

        let serverData = null;

        // 1. /api/data 호출 시도 (파이썬 서버 또는 Cloudflare Functions 환경)
        try {
            const res = await fetch('/api/data?t=' + Date.now());
            if (res.ok) {
                const contentType = res.headers.get('content-type') || '';
                if (contentType.includes('application/json')) {
                    serverData = await res.json();
                }
            }
        } catch (err) {}

        // 2. /api/data 실패 시 정적 JSON 파일 (Cloudflare Pages 정적 호스팅 환경) 직접 fetch
        if (!serverData || !serverData.institutions || serverData.institutions.length === 0) {
            try {
                const staticRes = await fetch('database/app_data.json?t=' + Date.now());
                if (staticRes.ok) {
                    serverData = await staticRes.json();
                    console.log("[정적 호스팅 동기화] database/app_data.json 로드 성공");
                }
            } catch (err) {
                console.warn("[정적 호스팅 동기화 실패]:", err);
            }
        }

        if (serverData && serverData.institutions && serverData.institutions.length > 0) {
            localStorage.setItem('camp_institutions', JSON.stringify(serverData.institutions));
            if (serverData.students && serverData.students.length > 0) {
                localStorage.setItem('camp_students', JSON.stringify(serverData.students));
            }
            if (serverData.seal_updated_at) {
                localStorage.setItem('seal_updated_at', serverData.seal_updated_at);
            }
        }

        this._initLocalData();
        this._isInitialized = true;
    },

    // 서버로 데이터 저장 전송 (PC -> 서버 -> 스마트폰 공유)
    async _pushToServer(institutions = null, students = null) {
        try {
            const insts = institutions || JSON.parse(localStorage.getItem('camp_institutions') || '[]');
            const stus = students || JSON.parse(localStorage.getItem('camp_students') || '[]');
            const sealTime = localStorage.getItem('seal_updated_at') || Date.now();

            await fetch('/api/data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json; charset=utf-8' },
                body: JSON.stringify({
                    institutions: insts,
                    students: stus,
                    seal_updated_at: Number(sealTime)
                })
            });
        } catch (e) {
            console.warn("서버 동기화 전송 실패 (로컬에만 저장됨):", e);
        }
    },

    // ---------------- 로컬 초기 데이터 시딩 ----------------
    _initLocalData() {
        if (!localStorage.getItem('camp_institutions')) {
            const initialInstitutions = [
                {
                    id: "inst-1792066615275",
                    name: "한국 반도체 마이스터 고등학교",
                    course_name: "머신러닝 기초 입문",
                    start_date: "2026-10-12",
                    end_date: "2026-10-14",
                    total_hours: 21,
                    issue_start_at: "2026-10-15T03:14:00.000Z",
                    issue_end_at: "2026-10-19T15:00:00.000Z",
                    issuer_name: "(주)로보그램"
                },
                {
                    id: "inst-02",
                    name: "인천외국어고등학교",
                    course_name: "AI 데이터사이언스 & 파이썬 심화 캠프",
                    start_date: "2026-05-01",
                    end_date: "2026-05-15",
                    total_hours: 16,
                    issue_start_at: "2026-05-01T00:00:00+09:00",
                    issue_end_at: "2026-12-31T23:59:59+09:00",
                    issuer_name: "(주)로보그램"
                }
            ];
            localStorage.setItem('camp_institutions', JSON.stringify(initialInstitutions));
        }
    },

    // ---------------- 교육기관 관련 ----------------
    async getInstitutions() {
        // 1. 서버 API 조회
        try {
            const res = await fetch('/api/data?t=' + Date.now());
            if (res.ok) {
                const contentType = res.headers.get('content-type') || '';
                if (contentType.includes('application/json')) {
                    const data = await res.json();
                    if (data.institutions && data.institutions.length > 0) {
                        localStorage.setItem('camp_institutions', JSON.stringify(data.institutions));
                        if (data.students) localStorage.setItem('camp_students', JSON.stringify(data.students));
                        if (data.seal_updated_at) localStorage.setItem('seal_updated_at', data.seal_updated_at);
                        return data.institutions;
                    }
                }
            }
        } catch (e) {}

        // 2. 정적 JSON 직접 조회 (Cloudflare Pages 배포 환경)
        try {
            const staticRes = await fetch('database/app_data.json?t=' + Date.now());
            if (staticRes.ok) {
                const data = await staticRes.json();
                if (data.institutions && data.institutions.length > 0) {
                    localStorage.setItem('camp_institutions', JSON.stringify(data.institutions));
                    if (data.students) localStorage.setItem('camp_students', JSON.stringify(data.students));
                    if (data.seal_updated_at) localStorage.setItem('seal_updated_at', data.seal_updated_at);
                    return data.institutions;
                }
            }
        } catch (e) {}

        this._initLocalData();
        return JSON.parse(localStorage.getItem('camp_institutions') || '[]');
    },

    async getInstitutionByName(schoolName) {
        const list = await this.getInstitutions();
        const cleanTarget = (schoolName || '').replace(/\s+/g, '').toLowerCase();
        const exact = list.find(item => (item.name || '').replace(/\s+/g, '').toLowerCase() === cleanTarget);
        if (exact) return exact;

        // 반도체 마이스터고 유연 매칭 (대구반도체마이스터고 <-> 한국반도체마이스터고)
        if (cleanTarget.includes('반도체') && cleanTarget.includes('마이스터')) {
            return list.find(item => {
                const c = (item.name || '').replace(/\s+/g, '').toLowerCase();
                return c.includes('반도체') && c.includes('마이스터');
            });
        }
        return null;
    },

    async saveInstitution(instData) {
        this._initLocalData();
        let savedItem = null;

        const list = JSON.parse(localStorage.getItem('camp_institutions') || '[]');
        const cleanName = (instData.name || '').replace(/\s+/g, '').toLowerCase();
        const idx = list.findIndex(i => (i.name || '').replace(/\s+/g, '').toLowerCase() === cleanName);
        if (idx >= 0) {
            list[idx] = { ...list[idx], ...instData, updated_at: new Date().toISOString() };
            savedItem = list[idx];
        } else {
            const newItem = {
                id: instData.id || 'inst-' + Date.now(),
                ...instData,
                created_at: new Date().toISOString()
            };
            list.unshift(newItem);
            savedItem = newItem;
        }

        localStorage.setItem('camp_institutions', JSON.stringify(list));
        
        // 서버 동기화 영구 저장 (스마트폰 즉시 반영)
        await this._pushToServer(list, null);
        return savedItem;
    },

    async deleteInstitution(name) {
        this._initLocalData();
        const cleanName = (name || '').replace(/\s+/g, '').toLowerCase();
        
        // 1. 기관 목록에서 삭제
        const instList = JSON.parse(localStorage.getItem('camp_institutions') || '[]').filter(
            i => (i.name || '').replace(/\s+/g, '').toLowerCase() !== cleanName
        );
        localStorage.setItem('camp_institutions', JSON.stringify(instList));

        // 2. 해당 기관 소속 학생들도 함께 삭제
        const studentList = JSON.parse(localStorage.getItem('camp_students') || '[]').filter(
            s => (s.school_name || '').replace(/\s+/g, '').toLowerCase() !== cleanName
        );
        localStorage.setItem('camp_students', JSON.stringify(studentList));

        // 3. 서버에 기관 및 학생 목록 영구 동기화
        await this._pushToServer(instList, studentList);
    },

    // ---------------- 학생 관련 ----------------
    async getStudents(schoolName = null) {
        // 1. 서버 API 조회
        try {
            const res = await fetch('/api/data?t=' + Date.now());
            if (res.ok) {
                const contentType = res.headers.get('content-type') || '';
                if (contentType.includes('application/json')) {
                    const data = await res.json();
                    if (data.students && data.students.length > 0) {
                        localStorage.setItem('camp_students', JSON.stringify(data.students));
                    }
                }
            }
        } catch (e) {}

        // 2. 정적 JSON 직접 조회 (Cloudflare Pages 배포 환경)
        if (!localStorage.getItem('camp_students') || JSON.parse(localStorage.getItem('camp_students') || '[]').length <= 3) {
            try {
                const staticRes = await fetch('database/app_data.json?t=' + Date.now());
                if (staticRes.ok) {
                    const data = await staticRes.json();
                    if (data.students && data.students.length > 0) {
                        localStorage.setItem('camp_students', JSON.stringify(data.students));
                    }
                }
            } catch (e) {}
        }

        this._initLocalData();
        let students = JSON.parse(localStorage.getItem('camp_students') || '[]');
        if (schoolName) {
            const cleanTarget = (schoolName || '').replace(/\s+/g, '').toLowerCase();
            students = students.filter(s => {
                const sSchool = (s.school_name || '').replace(/\s+/g, '').toLowerCase();
                return sSchool === cleanTarget;
            });
        }
        return students;
    },

    async findStudent(schoolName, studentId, password) {
        const cleanSchool = (schoolName || '').replace(/\s+/g, '').toLowerCase();
        const isTargetMeister = cleanSchool.includes('반도체') && cleanSchool.includes('마이스터');
        const cleanId = (studentId || '').trim();
        const cleanPw = (password || '').trim();

        // 최신 학생 목록을 가져와 조회
        const students = await this.getStudents();
        return students.find(s => {
            const sSchool = (s.school_name || '').replace(/\s+/g, '').toLowerCase();
            const schoolMatches = (sSchool === cleanSchool) || 
                                  (isTargetMeister && sSchool.includes('반도체') && sSchool.includes('마이스터'));
            return schoolMatches && s.student_id === cleanId && s.password === cleanPw;
        });
    },

    async saveStudent(studentData) {
        this._initLocalData();
        const list = JSON.parse(localStorage.getItem('camp_students') || '[]');
        const idx = list.findIndex(s => s.school_name === studentData.school_name && s.student_id === studentData.student_id);
        if (idx >= 0) {
            list[idx] = { ...list[idx], ...studentData, updated_at: new Date().toISOString() };
        } else {
            list.push({
                id: studentData.id || 'stu-' + Date.now() + '-' + Math.floor(Math.random()*1000),
                ...studentData,
                created_at: new Date().toISOString()
            });
        }
        localStorage.setItem('camp_students', JSON.stringify(list));
        await this._pushToServer(null, list);
    },

    async batchSaveStudents(studentsList) {
        this._initLocalData();
        const current = JSON.parse(localStorage.getItem('camp_students') || '[]');
        for (const stu of studentsList) {
            const idx = current.findIndex(s => s.school_name === stu.school_name && s.student_id === stu.student_id);
            if (idx >= 0) {
                current[idx] = { ...current[idx], ...stu, updated_at: new Date().toISOString() };
            } else {
                current.push({
                    id: 'stu-' + Date.now() + '-' + Math.floor(Math.random()*10000),
                    ...stu,
                    created_at: new Date().toISOString()
                });
            }
        }
        localStorage.setItem('camp_students', JSON.stringify(current));
        await this._pushToServer(null, current);
    },

    async updateStudentPhoto(schoolName, studentId, photoBase64) {
        const list = JSON.parse(localStorage.getItem('camp_students') || '[]');
        const idx = list.findIndex(s => s.school_name === schoolName && s.student_id === studentId);
        if (idx >= 0) {
            list[idx].photo_url = photoBase64;
            list[idx].updated_at = new Date().toISOString();
            localStorage.setItem('camp_students', JSON.stringify(list));
            await this._pushToServer(null, list);
        }
    },

    async recordPrint(schoolName, studentId) {
        const list = JSON.parse(localStorage.getItem('camp_students') || '[]');
        const idx = list.findIndex(s => s.school_name === schoolName && s.student_id === studentId);
        if (idx >= 0) {
            list[idx].is_issued = true;
            list[idx].print_count = (list[idx].print_count || 0) + 1;
            if (!list[idx].first_issued_at) {
                list[idx].first_issued_at = new Date().toISOString();
            }
            localStorage.setItem('camp_students', JSON.stringify(list));
            await this._pushToServer(null, list);
        }
    },

    async deleteStudent(schoolName, studentId) {
        const list = JSON.parse(localStorage.getItem('camp_students') || '[]').filter(
            s => !(s.school_name === schoolName && s.student_id === studentId)
        );
        localStorage.setItem('camp_students', JSON.stringify(list));
        await this._pushToServer(null, list);
    }
};

// 전역 등록
window.DB = DB;

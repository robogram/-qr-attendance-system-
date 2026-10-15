/**
 * 로보그램 코딩캠프 수료증 발급 시스템 - 메인 애플리케이션
 * (학생 로그인, 발급 가능 기간 검증, 사진 업로드, 인쇄/다운로드 바인딩)
 */

const App = {
    currentStudent: null,
    currentInstitution: null,

    init: async () => {
        // 서버와 데이터 및 직인 실시간 동기화 초기화 (스마트폰 & PC 동일 데이터 보장)
        if (window.DB && window.DB.init) {
            await window.DB.init();
        }

        // 기관 목록 드롭다운 채우기
        await App.populateSchoolOptions();

        // 관리자 세션 체크
        if (window.AdminModule && window.AdminModule.checkAuth()) {
            const navBtn = document.getElementById('navAdminBtn');
            if (navBtn) navBtn.style.display = 'none';
            document.getElementById('navAdminLogoutBtn').style.display = 'inline-flex';
            document.getElementById('adminSection').style.display = 'block';
            document.getElementById('studentLoginCard').style.display = 'none';
            const secretFooter = document.getElementById('secretAdminFooter');
            if (secretFooter) secretFooter.style.display = 'none';
            await window.AdminModule.loadInstitutions();
            await window.AdminModule.loadStudents();
            return;
        }

        // 학생 세션 복원 (최신 기관 정보 및 과목/일정 실시간 반영)
        const cachedStudent = sessionStorage.getItem('current_student');
        if (cachedStudent) {
            App.currentStudent = JSON.parse(cachedStudent);
            const freshInst = await window.DB.getInstitutionByName(App.currentStudent.school_name);
            App.currentInstitution = freshInst || JSON.parse(sessionStorage.getItem('current_institution') || '{}');
            sessionStorage.setItem('current_institution', JSON.stringify(App.currentInstitution));
            App.showStudentDashboard();
        }
    },

    // ---------------- 학교 목록 드롭다운 ----------------
    populateSchoolOptions: async () => {
        const institutions = await window.DB.getInstitutions();
        const select = document.getElementById('studentSchoolSelect');
        if (select) {
            select.innerHTML = `<option value="">-- 학교 또는 교육기관을 선택하세요 --</option>` +
                institutions.map(inst => `<option value="${inst.name}">${inst.name}</option>`).join('');
        }
    },

    // ---------------- 학생 로그인 ----------------
    loginStudent: async (e) => {
        if (e) e.preventDefault();

        const schoolName = document.getElementById('studentSchoolSelect').value;
        const studentId = document.getElementById('studentIdInput').value.trim();
        const password = document.getElementById('studentPwInput').value.trim();

        if (!schoolName) {
            alert("소속 학교 또는 교육기관을 선택해주세요.");
            return;
        }
        if (!studentId || !password) {
            alert("아이디와 비밀번호를 모두 입력해주세요.");
            return;
        }

        const student = await window.DB.findStudent(schoolName, studentId, password);
        if (!student) {
            alert("일치하는 학생 정보가 없습니다.\n학교명, 아이디, 비밀번호를 다시 확인해주세요.");
            return;
        }

        const institution = await window.DB.getInstitutionByName(schoolName);
        if (!institution) {
            alert("해당 교육기관 정보를 찾을 수 없습니다.");
            return;
        }

        // 발급 기간 검증
        const validation = App.checkIssuePeriod(institution);
        if (!validation.canIssue) {
            alert(validation.message);
            // 기간 외라도 조회는 가능하게 할지, 안내 배너를 띄울지 결정
        }

        App.currentStudent = student;
        App.currentInstitution = institution;
        sessionStorage.setItem('current_student', JSON.stringify(student));
        sessionStorage.setItem('current_institution', JSON.stringify(institution));

        App.showStudentDashboard(validation);
    },

    // ---------------- 수료증 출력 가능 기간 체크 ----------------
    checkIssuePeriod: (institution) => {
        const now = new Date();
        const sDate = institution.issue_start_at ? new Date(institution.issue_start_at) : null;
        const eDate = institution.issue_end_at ? new Date(institution.issue_end_at) : null;

        const sStr = institution.issue_start_at ? institution.issue_start_at.substring(0, 16).replace('T', ' ') : '';
        const eStr = institution.issue_end_at ? institution.issue_end_at.substring(0, 16).replace('T', ' ') : '';

        if (sDate && now < sDate) {
            return {
                canIssue: false,
                type: 'waiting',
                message: `📢 현재 수료증 발급 준비 기간입니다.\n발급 시작일시: ${sStr}`
            };
        }
        if (eDate && now > eDate) {
            return {
                canIssue: false,
                type: 'expired',
                message: `⚠️ 수료증 출력 가능 기간이 마감되었습니다.\n발급 종료일시: ${eStr}`
            };
        }

        return {
            canIssue: true,
            type: 'active',
            message: `✅ 수료증 발급 가능 기간입니다 (~ ${eStr}까지)`
        };
    },

    // ---------------- 학생 대시보드 화면 전환 ----------------
    showStudentDashboard: (validation = null) => {
        if (!validation) {
            validation = App.checkIssuePeriod(App.currentInstitution);
        }

        document.getElementById('studentLoginCard').style.display = 'none';
        document.getElementById('adminSection').style.display = 'none';
        const secretFooter = document.getElementById('secretAdminFooter');
        if (secretFooter) secretFooter.style.display = 'none';
        document.getElementById('studentDashboard').style.display = 'block';
        document.getElementById('navStudentLogoutBtn').style.display = 'inline-flex';

        // 학생 정보 텍스트 바인딩
        document.getElementById('dashStudentName').textContent = App.currentStudent.name;
        document.getElementById('dashSchoolName').textContent = App.currentInstitution.name;
        document.getElementById('dashCourseName').textContent = App.currentInstitution.course_name;

        // 발급 기간 안내 배너
        const alertBox = document.getElementById('issuePeriodAlert');
        if (alertBox) {
            if (!validation.canIssue) {
                alertBox.className = "alert-banner " + (validation.type === 'waiting' ? 'alert-warning' : 'alert-error');
                alertBox.innerHTML = `<strong>안내:</strong> ${validation.message}`;
                alertBox.style.display = 'flex';
                // 출력 버튼 비활성화
                document.getElementById('btnPrintA4').disabled = true;
                document.getElementById('btnDownloadPNG').disabled = true;
                document.getElementById('btnPrintA4').style.opacity = '0.5';
                document.getElementById('btnDownloadPNG').style.opacity = '0.5';
            } else {
                alertBox.className = "alert-banner alert-success";
                alertBox.innerHTML = `<span>${validation.message}</span>`;
                alertBox.style.display = 'flex';
                document.getElementById('btnPrintA4').disabled = false;
                document.getElementById('btnDownloadPNG').disabled = false;
                document.getElementById('btnPrintA4').style.opacity = '1';
                document.getElementById('btnDownloadPNG').style.opacity = '1';
            }
        }

        // 사진 썸네일 업데이트
        App.updatePhotoThumbnail();

        // 수료증 렌더링
        window.CertificateEngine.renderCertificate(App.currentStudent, App.currentInstitution);
    },

    updatePhotoThumbnail: () => {
        const thumb = document.getElementById('photoPreviewThumb');
        const emptySvg = document.getElementById('photoEmptySvg');
        if (App.currentStudent.photo_url) {
            thumb.src = App.currentStudent.photo_url;
            thumb.style.display = 'block';
            if (emptySvg) emptySvg.style.display = 'none';
        } else {
            thumb.style.display = 'none';
            if (emptySvg) emptySvg.style.display = 'block';
        }
    },

    // ---------------- 학생 사진 업로드 및 EXIF/비율 최적화 ----------------
    handlePhotoUpload: async (file) => {
        if (!file) return;

        // 용량 체크 (최대 10MB)
        if (file.size > 10 * 1024 * 1024) {
            alert("사진 용량은 최대 10MB 이하만 지원됩니다.");
            return;
        }

        const reader = new FileReader();
        reader.onload = async (e) => {
            const img = new Image();
            img.onload = async () => {
                // 3:4 여권/증명사진 비율로 리사이즈 및 캔버스 압축 (가로 300 x 세로 400)
                const targetW = 300;
                const targetH = 400;
                const canvas = document.createElement('canvas');
                canvas.width = targetW;
                canvas.height = targetH;
                const ctx = canvas.getContext('2d');

                // 중앙 크롭 비율 계산
                const imgRatio = img.width / img.height;
                const targetRatio = targetW / targetH;
                let sx, sy, sw, sh;

                if (imgRatio > targetRatio) {
                    sh = img.height;
                    sw = img.height * targetRatio;
                    sx = (img.width - sw) / 2;
                    sy = 0;
                } else {
                    sw = img.width;
                    sh = img.width / targetRatio;
                    sx = 0;
                    sy = (img.height - sh) / 2;
                }

                ctx.drawImage(img, sx, sy, sw, sh, 0, 0, targetW, targetH);
                const compressedBase64 = canvas.toDataURL('image/jpeg', 0.88);

                // DB 업데이트
                App.currentStudent.photo_url = compressedBase64;
                sessionStorage.setItem('current_student', JSON.stringify(App.currentStudent));
                await window.DB.updateStudentPhoto(
                    App.currentStudent.school_name,
                    App.currentStudent.student_id,
                    compressedBase64
                );

                // UI 갱신
                App.updatePhotoThumbnail();
                window.CertificateEngine.renderCertificate(App.currentStudent, App.currentInstitution);
                alert("사진이 성공적으로 등록되었습니다!");
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    },

    // ---------------- 시크릿 관리자 모드 (3초 롱프레스) ----------------
    openAdminAuthModal: () => {
        const modal = document.getElementById('adminAuthModal');
        const input = document.getElementById('adminSecretPwInput');
        const err = document.getElementById('adminAuthError');
        if (!modal) return;
        if (err) err.style.display = 'none';
        if (input) input.value = '';
        modal.style.display = 'flex';
        setTimeout(() => {
            if (input) input.focus();
        }, 80);
    },

    closeAdminAuthModal: () => {
        const modal = document.getElementById('adminAuthModal');
        if (modal) modal.style.display = 'none';
    },

    submitAdminAuth: () => {
        const input = document.getElementById('adminSecretPwInput');
        const err = document.getElementById('adminAuthError');
        if (!input) return;
        const pw = input.value.trim();

        if (window.AdminModule && window.AdminModule.login(pw)) {
            App.closeAdminAuthModal();
            App.enterAdminMode();
        } else {
            if (err) err.style.display = 'block';
            input.select();
        }
    },

    enterAdminMode: () => {
        const navAdminBtn = document.getElementById('navAdminBtn');
        if (navAdminBtn) navAdminBtn.style.display = 'none';
        const navAdminLogoutBtn = document.getElementById('navAdminLogoutBtn');
        if (navAdminLogoutBtn) navAdminLogoutBtn.style.display = 'inline-flex';

        document.getElementById('studentLoginCard').style.display = 'none';
        const dash = document.getElementById('studentDashboard');
        if (dash) dash.style.display = 'none';
        const secretFooter = document.getElementById('secretAdminFooter');
        if (secretFooter) secretFooter.style.display = 'none';

        document.getElementById('adminSection').style.display = 'block';
        window.AdminModule.loadInstitutions();
        window.AdminModule.loadStudents();
    },

    initSecretAdminTrigger: () => {
        const banner = document.getElementById('secretAdminBanner');
        const progress = document.getElementById('secretHoldProgress');
        const hint = document.getElementById('secretHoldHint');
        if (!banner || !progress) return;

        let holdTimer = null;
        const HOLD_TIME_MS = 2500; // 2.5초 (관리자 체감상 가장 자연스럽고 신속함)

        const startHold = (e) => {
            if (e.type === 'mousedown' && e.button !== 0) return;

            banner.classList.add('holding');
            if (hint) hint.classList.add('active');

            progress.style.transition = `width ${HOLD_TIME_MS}ms cubic-bezier(0.1, 0.7, 0.1, 1)`;
            progress.style.width = '100%';

            holdTimer = setTimeout(() => {
                endHold();
                if (navigator.vibrate) {
                    try { navigator.vibrate(100); } catch(err){}
                }
                App.openAdminAuthModal();
            }, HOLD_TIME_MS);
        };

        const endHold = () => {
            if (holdTimer) {
                clearTimeout(holdTimer);
                holdTimer = null;
            }
            banner.classList.remove('holding');
            if (hint) hint.classList.remove('active');
            progress.style.transition = 'none';
            progress.style.width = '0%';
        };

        // PC 마우스 이벤트
        banner.addEventListener('mousedown', startHold);
        window.addEventListener('mouseup', endHold);
        banner.addEventListener('mouseleave', endHold);

        // 스마트폰 터치 이벤트
        banner.addEventListener('touchstart', startHold, { passive: true });
        window.addEventListener('touchend', endHold);
        window.addEventListener('touchcancel', endHold);

        // 컨텍스트 메뉴 팝업 방지
        banner.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            return false;
        });

        // PC 관리자 비밀 단축키 (Ctrl + Shift + A 또는 Alt + A)
        window.addEventListener('keydown', (e) => {
            if ((e.ctrlKey && e.shiftKey && (e.key === 'A' || e.key === 'a')) ||
                (e.altKey && (e.key === 'A' || e.key === 'a'))) {
                e.preventDefault();
                App.openAdminAuthModal();
            }
        });
    },

    // ---------------- 로그아웃 ----------------
    logoutStudent: () => {
        sessionStorage.removeItem('current_student');
        sessionStorage.removeItem('current_institution');
        App.currentStudent = null;
        App.currentInstitution = null;
        location.reload();
    }
};

// ---------------- DOM 초기화 ----------------
document.addEventListener('DOMContentLoaded', () => {
    App.init();
    App.initSecretAdminTrigger();

    // 학생 로그인 폼 제출
    const loginForm = document.getElementById('studentLoginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', App.loginStudent);
    }

    // 학생 사진 파일 선택
    const photoInput = document.getElementById('photoInput');
    if (photoInput) {
        photoInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                App.handlePhotoUpload(e.target.files[0]);
            }
        });
    }

    // A4 인쇄 버튼 클릭 (노트북/PC)
    const btnPrintA4 = document.getElementById('btnPrintA4');
    if (btnPrintA4) {
        btnPrintA4.addEventListener('click', () => {
            if (!App.currentStudent || !App.currentInstitution) return;
            window.CertificateEngine.printA4(App.currentStudent, App.currentInstitution);
        });
    }

    // PNG 고화질 다운로드 버튼 클릭 (스마트폰/PC)
    const btnDownloadPNG = document.getElementById('btnDownloadPNG');
    if (btnDownloadPNG) {
        btnDownloadPNG.addEventListener('click', () => {
            if (!App.currentStudent || !App.currentInstitution) return;
            window.CertificateEngine.downloadAsPNG(App.currentStudent, App.currentInstitution);
        });
    }

    // 관리자 버튼 (보이지 않더라도 핸들러 유지)
    const navAdminBtn = document.getElementById('navAdminBtn');
    if (navAdminBtn) {
        navAdminBtn.addEventListener('click', App.openAdminAuthModal);
    }

    // 관리자 로그아웃 버튼
    const navAdminLogoutBtn = document.getElementById('navAdminLogoutBtn');
    if (navAdminLogoutBtn) {
        navAdminLogoutBtn.addEventListener('click', window.AdminModule.logout);
    }

    // 학생 로그아웃 버튼
    const navStudentLogoutBtn = document.getElementById('navStudentLogoutBtn');
    if (navStudentLogoutBtn) {
        navStudentLogoutBtn.addEventListener('click', App.logoutStudent);
    }

    // 관리자 탭 전환
    document.querySelectorAll('.admin-tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.admin-tab-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            const target = e.target.dataset.tab;
            if (target === 'institutions') {
                document.getElementById('adminTabInstitutions').style.display = 'block';
                document.getElementById('adminTabStudents').style.display = 'none';
                window.AdminModule.loadInstitutions();
            } else {
                document.getElementById('adminTabInstitutions').style.display = 'none';
                document.getElementById('adminTabStudents').style.display = 'block';
                window.AdminModule.loadStudents();
            }
        });
    });

    // CSV 파일 업로드
    const csvFileInput = document.getElementById('csvFileInput');
    if (csvFileInput) {
        csvFileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                window.AdminModule.handleCSVUpload(e.target.files[0]);
            }
        });
    }

    // CSV 양식 다운로드
    const btnDownloadTemplate = document.getElementById('btnDownloadTemplate');
    if (btnDownloadTemplate) {
        btnDownloadTemplate.addEventListener('click', window.AdminModule.downloadTemplateCSV);
    }

    // 학생 필터 & 검색
    const schoolFilter = document.getElementById('adminStudentSchoolFilter');
    if (schoolFilter) {
        schoolFilter.addEventListener('change', window.AdminModule.loadStudents);
    }
    const searchInput = document.getElementById('adminStudentSearch');
    if (searchInput) {
        searchInput.addEventListener('input', window.AdminModule.loadStudents);
    }
});

window.App = App;

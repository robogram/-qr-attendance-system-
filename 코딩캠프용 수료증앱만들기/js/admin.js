/**
 * 로보그램 코딩캠프 수료증 발급 시스템 - 관리자 로직
 * (기관 설정, 출력 가능 기간 제어, 엑셀/CSV 일괄 업로드, 학생 명단 관리)
 */

const ADMIN_PASSWORD = "robogram^^"; // 관리자 기본 비밀번호

const AdminModule = {
    currentTab: 'institutions', // 'institutions' | 'students'
    selectedSchoolFilter: '',
    isAdminLoggedIn: false,

    // ---------------- 관리자 인증 ----------------
    checkAuth: () => {
        return sessionStorage.getItem('is_admin_logged') === 'true';
    },

    login: (password) => {
        if (password === ADMIN_PASSWORD) {
            sessionStorage.setItem('is_admin_logged', 'true');
            AdminModule.isAdminLoggedIn = true;
            return true;
        }
        return false;
    },

    logout: () => {
        sessionStorage.removeItem('is_admin_logged');
        AdminModule.isAdminLoggedIn = false;
        location.reload();
    },

    // ---------------- 기관 관리 ----------------
    loadInstitutions: async () => {
        const institutions = await window.DB.getInstitutions();
        const tbody = document.getElementById('institutionsTableBody');
        const filterSelect = document.getElementById('adminStudentSchoolFilter');
        const modalSelect = document.getElementById('studentModalSchool');

        if (tbody) {
            if (institutions.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:2rem;color:#94a3b8;">등록된 교육기관이 없습니다. '새 교육기관 등록' 버튼을 눌러 추가하세요.</td></tr>`;
            } else {
                tbody.innerHTML = institutions.map((inst, idx) => {
                    const startStr = inst.issue_start_at ? inst.issue_start_at.substring(0, 16).replace('T', ' ') : '-';
                    const endStr = inst.issue_end_at ? inst.issue_end_at.substring(0, 16).replace('T', ' ') : '-';

                    // 현재 출력 가능 여부 판정
                    const now = new Date();
                    const sDate = inst.issue_start_at ? new Date(inst.issue_start_at) : null;
                    const eDate = inst.issue_end_at ? new Date(inst.issue_end_at) : null;
                    let statusBadge = '<span class="badge badge-success">출력 가능</span>';

                    if (sDate && now < sDate) {
                        statusBadge = '<span class="badge badge-warning">발급 대기</span>';
                    } else if (eDate && now > eDate) {
                        statusBadge = '<span class="badge badge-gray">기간 만료</span>';
                    }

                    return `
                        <tr>
                            <td>${idx + 1}</td>
                            <td><strong>${inst.name}</strong></td>
                            <td>${inst.course_name}</td>
                            <td>${inst.start_date} ~ ${inst.end_date} (${inst.total_hours}시간)</td>
                            <td>
                                <div style="font-size:0.8rem;color:#475569;">${startStr} ~</div>
                                <div style="font-size:0.8rem;color:#475569;">${endStr}</div>
                            </td>
                            <td>${statusBadge}</td>
                            <td>
                                <button class="btn-nav btn-nav-admin" style="padding:0.3rem 0.6rem;font-size:0.8rem;" onclick="AdminModule.openEditInstitution('${inst.name}')">수정</button>
                                <button class="btn-nav btn-nav-logout" style="padding:0.3rem 0.6rem;font-size:0.8rem;margin-left:4px;" onclick="AdminModule.deleteInstitution('${inst.name}')">삭제</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }

        // 학생 탭 학교 필터 및 등록 모달 선택창 동기화
        if (filterSelect) {
            const currentVal = filterSelect.value;
            filterSelect.innerHTML = `<option value="">전체 학교/기관 보기</option>` + 
                institutions.map(i => `<option value="${i.name}">${i.name}</option>`).join('');
            filterSelect.value = currentVal;
        }

        if (modalSelect) {
            modalSelect.innerHTML = institutions.map(i => `<option value="${i.name}">${i.name}</option>`).join('');
        }
    },

    openInstitutionModal: (inst = null) => {
        const modal = document.getElementById('institutionModal');
        const title = document.getElementById('instModalTitle');

        if (inst) {
            title.textContent = "교육기관 및 수료 정보 수정";
            document.getElementById('instName').value = inst.name;
            document.getElementById('instName').disabled = true;
            document.getElementById('instCourse').value = inst.course_name;
            document.getElementById('instStartDate').value = inst.start_date;
            document.getElementById('instEndDate').value = inst.end_date;
            document.getElementById('instHours').value = inst.total_hours;
            document.getElementById('instIssueStart').value = inst.issue_start_at ? inst.issue_start_at.substring(0, 16) : '';
            document.getElementById('instIssueEnd').value = inst.issue_end_at ? inst.issue_end_at.substring(0, 16) : '';
        } else {
            title.textContent = "새 교육기관 등록";
            document.getElementById('instName').value = '';
            document.getElementById('instName').disabled = false;
            document.getElementById('instCourse').value = '';
            document.getElementById('instStartDate').value = '';
            document.getElementById('instEndDate').value = '';
            document.getElementById('instHours').value = 8;

            // 기본값: 시작일은 오늘, 종료일은 3개월 뒤
            const now = new Date();
            const future = new Date();
            future.setMonth(future.getMonth() + 3);
            document.getElementById('instIssueStart').value = now.toISOString().substring(0, 16);
            document.getElementById('instIssueEnd').value = future.toISOString().substring(0, 16);
        }

        modal.style.display = 'flex';
    },

    saveInstitutionFromModal: async () => {
        const name = document.getElementById('instName').value.trim();
        const course = document.getElementById('instCourse').value.trim();
        const startDate = document.getElementById('instStartDate').value;
        const endDate = document.getElementById('instEndDate').value;
        const hours = parseInt(document.getElementById('instHours').value) || 8;
        const issueStart = document.getElementById('instIssueStart').value;
        const issueEnd = document.getElementById('instIssueEnd').value;

        if (!name || !course || !startDate || !endDate || !issueStart || !issueEnd) {
            alert("모든 필수 항목을 입력해주세요.");
            return;
        }

        const data = {
            name,
            course_name: course,
            start_date: startDate,
            end_date: endDate,
            total_hours: hours,
            issue_start_at: new Date(issueStart).toISOString(),
            issue_end_at: new Date(issueEnd).toISOString(),
            issuer_name: '(주)로보그램'
        };

        await window.DB.saveInstitution(data);
        document.getElementById('institutionModal').style.display = 'none';
        await AdminModule.loadInstitutions();
        alert("교육기관 정보가 저장되었습니다.");
    },

    openEditInstitution: async (name) => {
        const inst = await window.DB.getInstitutionByName(name);
        if (inst) {
            AdminModule.openInstitutionModal(inst);
        }
    },

    deleteInstitution: async (name) => {
        if (confirm(`'${name}' 교육기관 및 관련 학생 정보를 정말 삭제하시겠습니까?`)) {
            await window.DB.deleteInstitution(name);
            await AdminModule.loadInstitutions();
            await AdminModule.loadStudents();
        }
    },

    // ---------------- 학생 관리 ----------------
    loadStudents: async () => {
        const schoolFilter = document.getElementById('adminStudentSchoolFilter')?.value || '';
        const searchKeyword = document.getElementById('adminStudentSearch')?.value.trim().toLowerCase() || '';

        let students = await window.DB.getStudents(schoolFilter || null);

        if (searchKeyword) {
            students = students.filter(s => 
                (s.name && s.name.toLowerCase().includes(searchKeyword)) ||
                (s.student_id && s.student_id.toLowerCase().includes(searchKeyword))
            );
        }

        const tbody = document.getElementById('studentsTableBody');
        const countSpan = document.getElementById('studentTotalCount');
        if (countSpan) countSpan.textContent = students.length;

        if (tbody) {
            if (students.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:2rem;color:#94a3b8;">조건에 맞는 학생이 없습니다. 엑셀 업로드로 학생 명단을 등록하세요.</td></tr>`;
            } else {
                tbody.innerHTML = students.map((stu, idx) => {
                    const hasPhoto = !!stu.photo_url;
                    const photoBadge = hasPhoto 
                        ? `<span class="badge badge-success">등록됨</span>` 
                        : `<span class="badge badge-gray">미등록</span>`;

                    const issuedBadge = stu.is_issued 
                        ? `<span class="badge badge-success">발급완료 (${stu.print_count || 1}회)</span>` 
                        : `<span class="badge badge-warning">미발급</span>`;

                    return `
                        <tr>
                            <td>${idx + 1}</td>
                            <td>${stu.school_name}</td>
                            <td><strong>${stu.name}</strong></td>
                            <td><code>${stu.student_id}</code></td>
                            <td><code>${stu.password}</code></td>
                            <td>${photoBadge}</td>
                            <td>${issuedBadge}</td>
                            <td>
                                <button class="btn-nav btn-nav-logout" style="padding:0.25rem 0.5rem;font-size:0.75rem;" onclick="AdminModule.deleteStudent('${stu.student_id}', '${stu.name || ''}', '${stu.school_name || ''}')">삭제</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }
    },

    deleteStudent: async (studentId, studentName = '', schoolName = '') => {
        const displayName = studentName ? `'${studentName} (${studentId})'` : `'${studentId}'`;
        if (confirm(`학생 ${displayName}의 정보를 정말 삭제하시겠습니까?\n삭제된 정보는 즉시 명단에서 제외됩니다.`)) {
            await window.DB.deleteStudent(studentId);
            await AdminModule.loadStudents();
            alert(`학생 ${displayName}의 정보가 성공적으로 삭제되었습니다.`);
        }
    },

    // ---------------- 엑셀/CSV 일괄 파싱 및 업로드 ----------------
    handleCSVUpload: async (file) => {
        if (!file) return;

        const reader = new FileReader();
        reader.onload = async (e) => {
            try {
                const text = e.target.result;
                const lines = text.split(/\r?\n/).filter(line => line.trim().length > 0);
                if (lines.length <= 1) {
                    alert("업로드할 학생 데이터가 없습니다.");
                    return;
                }

                // 등록된 기관 목록 조회
                const instList = await window.DB.getInstitutions();
                if (instList.length === 0) {
                    alert("등록된 교육기관(학교)이 없습니다.\n먼저 상단에서 교육기관을 등록해주세요.");
                    return;
                }

                // 헤더 파싱
                const header = lines[0].split(',').map(h => h.trim().replace(/["']/g, ''));
                const schoolIdx = header.findIndex(h => h.includes('학교') || h.includes('기관') || h.includes('소속') || h.toLowerCase().includes('school'));
                const idIdx = header.findIndex(h => h.includes('아이디') || h.toLowerCase().includes('id'));
                const pwIdx = header.findIndex(h => h.includes('비밀번호') || h.includes('패스워드') || h.toLowerCase().includes('pw'));
                const nameIdx = header.findIndex(h => h.includes('이름') || h.includes('성명'));

                if (idIdx === -1 || pwIdx === -1 || nameIdx === -1) {
                    alert("CSV 헤더에 '학생아이디', '비밀번호', '학생이름' 열이 반드시 포함되어야 합니다.");
                    return;
                }

                // 공백 무시 학교 매칭 유틸 함수
                const matchOfficialSchool = (inputSchool) => {
                    if (!inputSchool) return null;
                    const clean = inputSchool.replace(/\s+/g, '').toLowerCase();
                    const matched = instList.find(i => i.name.replace(/\s+/g, '').toLowerCase() === clean);
                    return matched ? matched.name : null;
                };

                // 파일 내에 학교명 열이 존재하는지 체크
                let hasSchoolInFile = false;
                if (schoolIdx !== -1) {
                    for (let i = 1; i < Math.min(lines.length, 5); i++) {
                        const row = lines[i].split(',').map(r => r.trim().replace(/["']/g, ''));
                        if (row[schoolIdx] && row[schoolIdx].length > 0) {
                            hasSchoolInFile = true;
                            break;
                        }
                    }
                }

                // 파일에 학교명이 없을 경우 사용할 기본 학교 결정
                let selectedDefaultSchool = document.getElementById('adminStudentSchoolFilter')?.value || '';
                
                if (!hasSchoolInFile) {
                    // 파일에 학교명이 없는데 필터도 '전체'로 되어있는 경우 사용자에게 확인/선택 요청
                    if (!selectedDefaultSchool) {
                        const schoolOptionsText = instList.map((i, idx) => `${idx + 1}. ${i.name}`).join('\n');
                        const promptMsg = `업로드할 엑셀 파일에 '학교명' 열이 없습니다.\n학생들을 등록할 소속 학교(기관)명을 입력하세요:\n\n[현재 등록된 학교 목록]\n${schoolOptionsText}`;
                        const userInput = prompt(promptMsg, instList[0].name);
                        if (!userInput) {
                            alert("업로드가 취소되었습니다.");
                            return;
                        }
                        const matched = matchOfficialSchool(userInput) || instList.find(i => i.name.includes(userInput.trim()))?.name;
                        if (!matched) {
                            alert(`'${userInput}'과(와) 일치하는 교육기관을 찾을 수 없습니다.\n정확한 학교명을 확인해주세요.`);
                            return;
                        }
                        selectedDefaultSchool = matched;
                    }
                }

                const studentsToSave = [];
                let lastTargetSchool = selectedDefaultSchool;

                for (let i = 1; i < lines.length; i++) {
                    const row = lines[i].split(',').map(r => r.trim().replace(/["']/g, ''));
                    if (row.length < 3) continue;

                    const studentId = row[idIdx];
                    const password = row[pwIdx];
                    const name = row[nameIdx];
                    
                    let rowSchool = (schoolIdx !== -1 && row[schoolIdx]) ? row[schoolIdx] : selectedDefaultSchool;
                    // 등록된 공식 기관명으로 스마트 매칭 (띄어쓰기 오차 자동 해결)
                    const officialSchool = matchOfficialSchool(rowSchool) || rowSchool || selectedDefaultSchool;

                    if (studentId && password && name && officialSchool) {
                        lastTargetSchool = officialSchool;
                        const instObj = instList.find(ins => ins.name === officialSchool);
                        studentsToSave.push({
                            institution_id: instObj ? instObj.id : '',
                            school_name: officialSchool,
                            student_id: studentId,
                            password: password,
                            name: name,
                            is_issued: false,
                            print_count: 0
                        });
                    }
                }

                if (studentsToSave.length > 0) {
                    await window.DB.batchSaveStudents(studentsToSave);

                    // 업로드한 학교로 필터를 자동 전환하여 방금 등록된 학생이 즉시 보이도록 배려
                    const filter = document.getElementById('adminStudentSchoolFilter');
                    if (filter && lastTargetSchool) {
                        filter.value = lastTargetSchool;
                    }

                    await AdminModule.loadStudents();
                    alert(`총 ${studentsToSave.length}명의 학생 명단이 [${lastTargetSchool}] 소속으로 성공적으로 등록되었습니다!`);
                } else {
                    alert("유효한 학생 데이터를 찾지 못했습니다.");
                }
            } catch (err) {
                console.error(err);
                alert("CSV 파일 처리 중 오류가 발생했습니다: " + err.message);
            }
        };
        reader.readAsText(file, 'euc-kr'); // 한글 윈도우 엑셀 호환
    },

    // 엑셀 템플릿 다운로드
    downloadTemplateCSV: () => {
        const csvContent = "\uFEFF학교명,학생아이디,비밀번호,학생이름,비고\n감정초등학교,stu2026_01,1234,홍인희,1반\n감정초등학교,stu2026_02,1234,김민준,1반\n인천외국어고등학교,icfl_01,pass1234,최유진,AI반\n";
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "학생명단_업로드_양식.csv";
        link.click();
    },

    // ---------------- 직인 도장 관리 (서버 및 스마트폰 실시간 동기화) ----------------
    openSealModal: () => {
        const modal = document.getElementById('sealModal');
        const preview = document.getElementById('currentSealPreview');
        if (preview) {
            preview.src = (window.CertificateEngine ? window.CertificateEngine.getSealSrc() : 'assets/seal_custom.png') + '?t=' + Date.now();
        }
        if (modal) modal.style.display = 'flex';
    },

    handleSealUpload: (file) => {
        if (!file) return;
        const reader = new FileReader();
        reader.onload = async (e) => {
            const base64Data = e.target.result;
            localStorage.setItem('custom_seal_img', base64Data);
            
            const preview = document.getElementById('currentSealPreview');
            if (preview) preview.src = base64Data;

            // 서버로 업로드하여 영구 파일 저장 및 스마트폰 즉시 동기화
            try {
                const res = await fetch('/api/seal', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json; charset=utf-8' },
                    body: JSON.stringify({ image: base64Data })
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.seal_updated_at) {
                        localStorage.setItem('seal_updated_at', data.seal_updated_at);
                    }
                }
            } catch (err) {
                console.warn("직인 서버 업로드 통신 오류:", err);
            }

            // 학생 화면 수료증도 실시간 갱신
            if (window.App && window.App.currentStudent && window.App.currentInstitution) {
                window.CertificateEngine.renderCertificate(window.App.currentStudent, window.App.currentInstitution);
            }

            alert("새로운 직인 이미지가 성공적으로 등록되었습니다!\n스마트폰과 PC의 모든 수료증에 즉시 반영됩니다.");
        };
        reader.readAsDataURL(file);
    },

    resetSealToDefault: async () => {
        if (confirm("공식 원형 법인 직인으로 복원하시겠습니까?")) {
            localStorage.removeItem('custom_seal_img');
            
            try {
                const res = await fetch('/api/seal/reset', { method: 'POST' });
                if (res.ok) {
                    const data = await res.json();
                    localStorage.setItem('seal_updated_at', Date.now());
                }
            } catch (e) {
                console.warn("직인 초기화 서버 통신 오류:", e);
            }

            const preview = document.getElementById('currentSealPreview');
            if (preview) preview.src = '/api/seal?t=' + Date.now();

            if (window.App && window.App.currentStudent && window.App.currentInstitution) {
                window.CertificateEngine.renderCertificate(window.App.currentStudent, window.App.currentInstitution);
            }

            alert("기본 공식 법인 직인으로 복원되었습니다.");
        }
    }
};

window.AdminModule = AdminModule;

/**
 * 로보그램 코딩캠프 수료증 발급 시스템
 * 수료증 렌더링, A4 브라우저 인쇄, 고화질 PNG 캔버스 생성 및 다운로드 엔진
 */

const CertificateEngine = {
    // ---------------- 날짜 포맷팅 유틸 ----------------
    formatKoreanDate: (dateStr) => {
        const d = dateStr ? new Date(dateStr) : new Date();
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${year}년 ${month}월 ${day}일`;
    },

    formatPeriodDate: (startStr, endStr) => {
        if (!startStr || !endStr) return "-";
        return `${startStr} ~ ${endStr}`;
    },

    getSealSrc: () => {
        // 1. 로컬에 등록된 커스텀 직인이 있으면 우선 사용(즉각 렌더링)
        const localSeal = localStorage.getItem('custom_seal_img');
        if (localSeal && localSeal.startsWith('data:image')) {
            return localSeal;
        }
        // 2. 최신 커스텀 직인 이미지 파일 우선 사용 (Cloudflare Pages 및 로컬 공통)
        const sealTime = localStorage.getItem('seal_updated_at') || '2';
        return 'assets/seal_custom.png?v=' + sealTime;
    },

    // ---------------- 모바일 화면 맞춤 자동 스케일러 (가로 스크롤 방지 & 100% 한눈에 보기) ----------------
    fitCertificateToScreen: () => {
        const previewContainer = document.querySelector('.certificate-preview-container');
        const sheet = document.getElementById('certificateSheet');
        if (!previewContainer || !sheet) return;

        const containerWidth = previewContainer.clientWidth;
        const certOriginalWidth = 800;
        const certOriginalHeight = 1060;

        if (containerWidth < certOriginalWidth + 30) {
            const availableWidth = containerWidth - 24;
            const scale = Math.max(0.35, Math.min(1, availableWidth / certOriginalWidth));
            
            sheet.style.transform = `scale(${scale})`;
            sheet.style.transformOrigin = 'top center';
            sheet.style.marginBottom = `-${certOriginalHeight * (1 - scale)}px`;
        } else {
            sheet.style.transform = 'none';
            sheet.style.marginBottom = '0px';
        }
    },

    // ---------------- HTML 수료증 엘리먼트 동적 렌더링 ----------------
    renderCertificate: (student, institution, containerId = 'certificateSheet') => {
        const container = document.getElementById(containerId);
        if (!container) return;

        const photoSrc = student.photo_url || '';
        const sealSrc = CertificateEngine.getSealSrc();
        const todayStr = CertificateEngine.formatKoreanDate();
        const periodStr = CertificateEngine.formatPeriodDate(institution.start_date, institution.end_date);
        const totalHours = institution.total_hours || 8;
        const issuerName = institution.issuer_name || '(주)로보그램';

        container.innerHTML = `
            <div class="cert-background-watermark"></div>
            <div class="cert-border-outer"></div>
            <div class="cert-border-inner"></div>

            <div class="cert-content">
                <!-- 상단 타이틀 -->
                <div class="cert-header">
                    <h1 class="cert-title">수 료 증</h1>
                    <div class="cert-subtitle">Certificate of Completion</div>
                </div>

                <!-- 중앙 영역 (정보 목록 & 학생 사진) -->
                <div class="cert-middle">
                    <ul class="cert-info-list">
                        <li><span class="info-label">• 성&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;명 :</span> <span class="info-val">${student.name}</span></li>
                        <li><span class="info-label">• 학&nbsp;교&nbsp;명 :</span> <span class="info-val info-school">${institution.name}</span></li>
                        <li><span class="info-label">• 과&nbsp;정&nbsp;명 :</span> <span class="info-val info-course">${institution.course_name}</span></li>
                        <li><span class="info-label">• 교육기간 :</span> <span class="info-val info-date">${periodStr}</span></li>
                        <li><span class="info-label">• 교육시간 :</span> <span class="info-val">${totalHours}시간</span></li>
                    </ul>

                    <!-- 학생 사진 박스 -->
                    <div class="cert-photo-container">
                        ${photoSrc 
                            ? `<img src="${photoSrc}" alt="${student.name} 사진" class="cert-photo-img" id="certStudentPhoto">` 
                            : `<div class="cert-photo-empty">
                                 <svg style="width:36px;height:36px;margin-bottom:6px;opacity:0.6" fill="currentColor" viewBox="0 0 20 20">
                                   <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"></path>
                                 </svg>
                                 <span>사진 등록 권장</span>
                               </div>`
                        }
                    </div>
                </div>

                <!-- 수료 증명 문구 -->
                <div class="cert-statement">
                    귀하는 (주)로보그램에서 주관하는 소정의<br>
                    과정을 수료하였음을 증명합니다.
                </div>

                <!-- 발급 일자 -->
                <div class="cert-date">
                    ${todayStr}
                </div>

                <!-- 하단 발급기관 및 직인 ((주)로보그램은 중앙 정렬, 직인은 '램' 오른쪽에 밀착 날인) -->
                <div class="cert-footer" style="display:flex;align-items:center;justify-content:center;margin-bottom:30px;position:relative;">
                    <div class="cert-issuer-wrap" style="display:inline-block;position:relative;text-align:center;">
                        <span class="cert-issuer-text" style="font-size:50px !important;font-weight:700 !important;color:#222222 !important;letter-spacing:0.22em !important;margin-left:0.22em !important;">${issuerName}</span>
                        <img src="${sealSrc}" alt="직인" class="cert-seal-img" onerror="this.src='assets/seal_custom.png'" style="position:absolute !important;left:100% !important;top:50% !important;transform:translateY(-50%) !important;margin-left:6px !important;width:140px !important;height:140px !important;object-fit:contain !important;mix-blend-mode:multiply !important;display:block !important;z-index:10 !important;pointer-events:none !important;">
                    </div>
                </div>
            </div>
        `;

        // 모바일 화면 맞춤 자동 스케일링 실행
        setTimeout(CertificateEngine.fitCertificateToScreen, 60);
    },

    // ---------------- A4 브라우저 인쇄 (노트북/PC 최적화) ----------------
    printA4: async (student, institution) => {
        try {
            // 출력 카운트 증가
            if (window.DB && student) {
                await window.DB.recordPrint(student.school_name, student.student_id);
            }
        } catch (e) {
            console.warn(e);
        }

        // 브라우저 기본 인쇄 다이얼로그 호출 (CSS @media print 규칙 자동 적용)
        window.print();
    },

    // ---------------- 고화질 PNG 이미지 캔버스 생성 및 다운로드 (모바일/PC 공용) ----------------
    downloadAsPNG: async (student, institution) => {
        // 고해상도 Canvas (가로 1200 x 세로 1590, 300DPI급 화질)
        const canvas = document.createElement('canvas');
        const scale = 2; // 레티나 고해상도 배율
        const width = 800 * scale;
        const height = 1060 * scale;
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');

        // 배경색
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, width, height);

        // 배경 워터마크 이미지 합성 (선명한 70% 투명도)
        await new Promise((resolve) => {
            const bgImg = new Image();
            bgImg.onload = () => {
                ctx.save();
                ctx.globalAlpha = 0.70;
                ctx.drawImage(bgImg, 0, 0, width, height);
                ctx.restore();
                resolve();
            };
            bgImg.onerror = () => resolve();
            bgImg.src = 'assets/cert_bg.jpg';
        });

        // 1. 외곽 더블 골드 테두리
        const goldColor = '#DAA520';
        ctx.strokeStyle = goldColor;

        // 바깥 테두리
        ctx.lineWidth = 10 * scale;
        ctx.strokeRect(20 * scale, 20 * scale, width - 40 * scale, height - 40 * scale);

        // 안쪽 테두리
        ctx.lineWidth = 3 * scale;
        ctx.strokeRect(32 * scale, 32 * scale, width - 64 * scale, height - 64 * scale);

        // 2. 제목 "수 료 증"
        ctx.fillStyle = '#000000';
        ctx.font = `900 ${56 * scale}px "Noto Sans KR", sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        // 자간 효과 시뮬레이션
        const titleText = "수  료  증";
        ctx.fillText(titleText, width / 2, 145 * scale);

        // 3. 부제 "Certificate of Completion"
        ctx.fillStyle = '#6b7280';
        ctx.font = `600 ${26 * scale}px "Playfair Display", Georgia, serif`;
        ctx.fillText("Certificate of Completion", width / 2, 205 * scale);

        // 4. 정보 리스트
        // 4. 정보 리스트 (긴 학교명 및 기간 배치 최적화)
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        const startX = 65 * scale;
        let startY = 300 * scale;
        const lineGap = 45 * scale;

        const infoList = [
            { label: "• 성      명 :", val: student.name },
            { label: "• 학  교  명 :", val: institution.name },
            { label: "• 과  정  명 :", val: institution.course_name },
            { label: "• 교육기간 :", val: CertificateEngine.formatPeriodDate(institution.start_date, institution.end_date) },
            { label: "• 교육시간 :", val: `${institution.total_hours || 8}시간` }
        ];

        for (const item of infoList) {
            ctx.fillStyle = '#000000';
            ctx.font = `500 ${21.5 * scale}px "Noto Sans KR", sans-serif`;
            ctx.fillText(item.label, startX, startY);

            ctx.font = `700 ${21.5 * scale}px "Noto Sans KR", sans-serif`;
            ctx.fillText(item.val, startX + (125 * scale), startY);
            startY += lineGap;
        }

        // 5. 학생 사진 합성 (우측 상단 - 3:4 규격)
        const photoWidth = 140 * scale;
        const photoHeight = 185 * scale;
        const photoX = width - (60 * scale) - photoWidth;
        const photoY = 295 * scale;

        if (student.photo_url) {
            try {
                await new Promise((resolve) => {
                    const pImg = new Image();
                    pImg.crossOrigin = "anonymous";
                    pImg.onload = () => {
                        ctx.save();
                        // 둥근 모서리 클리핑
                        ctx.beginPath();
                        ctx.roundRect(photoX, photoY, photoWidth, photoHeight, 6 * scale);
                        ctx.clip();
                        ctx.drawImage(pImg, photoX, photoY, photoWidth, photoHeight);
                        ctx.restore();

                        // 사진 테두리
                        ctx.strokeStyle = '#cbd5e1';
                        ctx.lineWidth = 1.5 * scale;
                        ctx.strokeRect(photoX, photoY, photoWidth, photoHeight);
                        resolve();
                    };
                    pImg.onerror = () => {
                        drawEmptyPhoto(ctx, photoX, photoY, photoWidth, photoHeight, scale);
                        resolve();
                    };
                    pImg.src = student.photo_url;
                });
            } catch (err) {
                drawEmptyPhoto(ctx, photoX, photoY, photoWidth, photoHeight, scale);
            }
        } else {
            drawEmptyPhoto(ctx, photoX, photoY, photoWidth, photoHeight, scale);
        }

        // 6. 증명 문구
        ctx.textAlign = 'center';
        ctx.fillStyle = '#000000';
        ctx.font = `600 ${25 * scale}px "Noto Sans KR", sans-serif`;
        ctx.fillText("귀하는 (주)로보그램에서 주관하는 소정의", width / 2, 630 * scale);
        ctx.fillText("과정을 수료하였음을 증명합니다.", width / 2, 675 * scale);

        // 7. 발급일
        ctx.font = `500 ${24 * scale}px "Noto Sans KR", sans-serif`;
        ctx.fillText(CertificateEngine.formatKoreanDate(), width / 2, 775 * scale);

        // 8. 발급처 "(주)로보그램"은 정중앙 출력 & 9. 직인은 '램' 오른쪽에 밀착 날인
        const issuerName = institution.issuer_name || '(주)로보그램';
        ctx.fillStyle = '#222222';
        ctx.font = `700 ${50 * scale}px "Noto Sans KR", sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        if ('letterSpacing' in ctx) {
            ctx.letterSpacing = `${50 * 0.22 * scale}px`;
        }

        const textY = 890 * scale;
        ctx.fillText(issuerName, width / 2, textY);

        const sealSrc = CertificateEngine.getSealSrc();
        await new Promise((resolve) => {
            const sealImg = new Image();
            sealImg.onload = () => {
                const sealSize = 140 * scale; // 직인 크기 확대 (125 -> 140)
                const gap = 6 * scale; // '램' 글자 바로 옆에 밀착 (14 -> 6)
                const textWidth = ctx.measureText(issuerName).width;

                // (주)로보그램 텍스트 오른쪽 끝 = (width / 2) + (textWidth / 2)
                const textRightEdge = (width / 2) + (textWidth / 2);

                // 직인 시작 X는 오른쪽 끝 + gap
                const sealX = textRightEdge + gap;
                const sealY = textY - (sealSize / 2);

                ctx.save();
                ctx.globalAlpha = 0.95;
                ctx.drawImage(sealImg, sealX, sealY, sealSize, sealSize);
                ctx.restore();
                resolve();
            };
            sealImg.onerror = () => resolve();
            sealImg.src = sealSrc;
        });

        // 10. 이미지 다운로드 트리거
        const fileName = `수료증_${institution.name}_${student.name}.png`;
        const dataUrl = canvas.toDataURL('image/png', 0.95);

        const link = document.createElement('a');
        link.download = fileName;
        link.href = dataUrl;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // 출력 횟수 기록
        if (window.DB && student) {
            await window.DB.recordPrint(student.school_name, student.student_id);
        }
    }
};

function drawEmptyPhoto(ctx, x, y, w, h, scale) {
    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = '#cbd5e1';
    ctx.lineWidth = 1.5 * scale;
    ctx.strokeRect(x, y, w, h);

    ctx.fillStyle = '#94a3b8';
    ctx.font = `400 ${16 * scale}px "Noto Sans KR", sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillText("사진 미등록", x + w / 2, y + h / 2);
}

window.CertificateEngine = CertificateEngine;

// 화면 크기 변경 및 스마트폰 가로/세로 회전 시 자동 재스케일링
window.addEventListener('resize', () => {
    CertificateEngine.fitCertificateToScreen();
});
window.addEventListener('orientationchange', () => {
    setTimeout(CertificateEngine.fitCertificateToScreen, 150);
});

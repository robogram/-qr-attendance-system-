import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

class ZoomManager:
    def __init__(self):
        self.client_id = os.getenv("ZOOM_CLIENT_ID")
        self.client_secret = os.getenv("ZOOM_CLIENT_SECRET")
        self.account_id = os.getenv("ZOOM_ACCOUNT_ID")
        self.access_token = None
        self.token_expiry = 0

    def get_access_token(self):
        """Server-to-Server OAuth 토큰 획득 (재시도 로직 포함)"""
        if self.access_token and time.time() < self.token_expiry:
            return self.access_token

        url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={self.account_id}"
        auth = (self.client_id, self.client_secret)
        
        for i in range(3):
            try:
                response = requests.post(url, auth=auth, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data['access_token']
                    self.token_expiry = time.time() + data['expires_in'] - 60
                    return self.access_token
                else:
                    print(f"Zoom Auth Error ({response.status_code}): {response.text}")
                    break
            except Exception as e:
                print(f"Zoom Auth Retry {i+1}/3: {e}")
                time.sleep(1)
        return None

    def get_meeting_participants(self, meeting_id, target_date=None, start_time=None, end_time=None):
        """
        실시간(Metrics) + 과거(Report) 회의 참가자 명단 조합 후 날짜 필터링 반환

        Args:
            meeting_id: Zoom 회의 ID
            target_date: 필터링할 날짜 (YYYY-MM-DD 문자열 또는 date 객체, None이면 오늘)
            start_time: 수업 시작 시간 (datetime 객체, 시간 필터링에 사용)
            end_time: 수업 종료 시간 (datetime 객체, 시간 필터링에 사용)
        """
        from datetime import date as date_cls, datetime as dt_cls, timezone, timedelta
        
        token = self.get_access_token()
        if not token:
            return []

        meeting_id = str(meeting_id).replace(" ", "")
        headers = {"Authorization": f"Bearer {token}"}

        # ── 필터링 기준 날짜 결정 ──────────────────────────────────────────
        if target_date is None:
            from utils import get_today_kst
            filter_date = get_today_kst()
        elif isinstance(target_date, str):
            filter_date = dt_cls.strptime(target_date, '%Y-%m-%d').date()
        else:
            filter_date = target_date

        # ── start_time / end_time 을 offset-aware UTC datetime으로 정규화 ──
        kst_tz = timezone(timedelta(hours=9))
        utc_tz = timezone.utc

        def to_utc_aware(dt):
            """어떤 datetime이 와도 UTC-aware datetime으로 변환"""
            if dt is None:
                return None
            # pandas Timestamp 처리
            try:
                import pandas as pd
                if isinstance(dt, pd.Timestamp):
                    dt = dt.to_pydatetime()
            except ImportError:
                pass
            if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
                return dt.astimezone(utc_tz)
            else:
                # naive → KST 로 가정 후 UTC 변환
                return dt.replace(tzinfo=kst_tz).astimezone(utc_tz)

        start_utc = to_utc_aware(start_time)
        end_utc   = to_utc_aware(end_time)
        buffer    = timedelta(hours=2)  # 수업 시작 2시간 전부터 허용

        # ── 1. 실시간 Metrics API (live) ──────────────────────────────────
        live_participants = []
        try:
            url_live = f"https://api.zoom.us/v2/metrics/meetings/{meeting_id}/participants?type=live"
            resp = requests.get(url_live, headers=headers, timeout=10)
            if resp.status_code == 200:
                live_participants = resp.json().get('participants', [])
        except Exception as e:
            print(f"Metrics API skip: {e}")

        # ── 2. Report API (과거 기록, 항상 시도) ─────────────────────────
        report_participants = []
        try:
            url_report = f"https://api.zoom.us/v2/report/meetings/{meeting_id}/participants"
            resp = requests.get(url_report, headers=headers, timeout=10)
            if resp.status_code == 200:
                report_participants = resp.json().get('participants', [])
        except Exception as e:
            print(f"Report API skip: {e}")

        # ── 3. 두 목록 합치기 (이름 기준 중복 제거, Report 우선) ─────────
        # Report에는 join_time이 있어서 필터링에 유리 → 우선 처리
        combined = {}
        for p in report_participants:
            name_key = (p.get('name') or p.get('user_name') or '').strip().lower()
            if name_key:
                combined[name_key] = p

        # Metrics 결과는 Report에 없는 이름만 추가 (live 중인 참가자)
        for p in live_participants:
            name_key = (p.get('name') or p.get('user_name') or '').strip().lower()
            if name_key and name_key not in combined:
                combined[name_key] = p

        all_participants = list(combined.values())
        print(f"[Zoom] Raw: live={len(live_participants)}, report={len(report_participants)}, merged={len(all_participants)}")

        # ── 4. 날짜 + 시간 필터링 ─────────────────────────────────────────
        filtered = []
        for p in all_participants:
            participant_name = p.get('name') or p.get('user_name') or ''
            join_time_str = p.get('join_time', '')

            if not join_time_str:
                # join_time이 없는 경우(주로 Metrics live)는 날짜 필터 없이 포함
                filtered.append(p)
                print(f"  [+] '{participant_name}' (no join_time, included)")
                continue

            try:
                join_dt_utc = dt_cls.fromisoformat(join_time_str.replace('Z', '+00:00')).astimezone(utc_tz)
                join_date_kst = join_dt_utc.astimezone(kst_tz).date()

                # 날짜 필터: 오늘 또는 어제 (KST 기준 오늘이면 무조건 패스)
                allowed_dates = {filter_date, filter_date - timedelta(days=1)}
                if join_date_kst not in allowed_dates:
                    print(f"  [-] '{participant_name}' 날짜 제외 ({join_date_kst})")
                    continue

                # 시간 필터 제거: 오늘 입장한 학생이면 수업 시간과 상관없이 일단 모두 출석 후보로 포함
                # (소회의실 이동 등으로 인한 시간 오차 완전 무력화)
                filtered.append(p)
                print(f"  [+] '{participant_name}' 포함 (입장: {join_dt_utc.astimezone(kst_tz).strftime('%H:%M KST')})")

            except Exception as e:
                # 파싱 실패 시 포함 (누락 방지)
                print(f"  [?] '{participant_name}' join_time 파싱 실패 - 포함 처리 ({e})")
                filtered.append(p)

        print(f"[Zoom] Final: {len(filtered)}명")
        return filtered

zoom_mgr = ZoomManager()

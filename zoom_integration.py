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
        
        for i in range(3): # 최대 3번 재시도
            try:
                response = requests.post(url, auth=auth, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data['access_token']
                    self.token_expiry = time.time() + data['expires_in'] - 60
                    return self.access_token
                else:
                    print(f"❌ Zoom Auth Error ({response.status_code}): {response.text}")
                    break
            except Exception as e:
                print(f"⚠️ Zoom Auth Retry {i+1}/3: {e}")
                time.sleep(1)
        return None

    def get_meeting_participants(self, meeting_id, target_date=None, start_time=None, end_time=None):
        """
        실시간(Metrics) 또는 과거(Report) 회의 참가자 명단 조회
        
        ⭐ target_date 및 start_time/end_time으로 필터링하여
        다른 세션의 참가자가 누적되는 문제를 방지합니다.
        
        Args:
            meeting_id: Zoom 회의 ID
            target_date: 필터링할 날짜 (YYYY-MM-DD 문자열 또는 date 객체, None이면 오늘)
            start_time: 수업 시작 시간 (datetime 객체, KST 기준 권장)
            end_time: 수업 종료 시간 (datetime 객체, KST 기준 권장)
        """
        from datetime import date as date_cls, datetime as dt_cls
        
        token = self.get_access_token()
        if not token: return []

        meeting_id = str(meeting_id).replace(" ", "")
        participants = []
        headers = {"Authorization": f"Bearer {token}"}
        
        # 필터링할 날짜 결정
        if target_date is None:
            filter_date = date_cls.today()
        elif isinstance(target_date, str):
            filter_date = dt_cls.strptime(target_date, '%Y-%m-%d').date()
        else:
            filter_date = target_date

        # 1. 먼저 실시간 회의(Metrics) 시도
        try:
            url_live = f"https://api.zoom.us/v2/metrics/meetings/{meeting_id}/participants?type=live"
            resp = requests.get(url_live, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                participants.extend(data.get('participants', []))
        except Exception as e:
            print(f"⚠️ Metrics API Skip: {e}")

        # 2. 실시간 데이터가 없거나 실패한 경우 과거 기록(Report) 시도
        if not participants:
            for i in range(2): # 재시도 포함
                try:
                    url_past = f"https://api.zoom.us/v2/report/meetings/{meeting_id}/participants"
                    resp = requests.get(url_past, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        participants.extend(data.get('participants', []))
                        break
                    else:
                        print(f"❌ Zoom Report API Error: {resp.status_code}")
                except Exception as e:
                    print(f"⚠️ Report API Retry {i+1}/2: {e}")
                    time.sleep(1)

        # ⭐ 3. 오늘 날짜의 참가자만 필터링 (이전 세션 누적 방지)
        filtered = []
        seen_names = set()  # 동일 참가자 중복 제거
        
        for p in participants:
            join_time_str = p.get('join_time', '')
            participant_name = p.get('name') or p.get('user_name') or ''
            
            if join_time_str:
                try:
                    # Zoom은 UTC(ISO 8601) 형식: "2026-04-04T11:30:00Z"
                    join_dt = dt_cls.fromisoformat(join_time_str.replace('Z', '+00:00'))
                    
                    # UTC → KST (한국시간 +9시간)으로 변환하여 날짜 비교
                    from datetime import timezone, timedelta
                    kst = timezone(timedelta(hours=9))
                    join_kst = join_dt.astimezone(kst)
                    join_date = join_kst.date()
                    
                    # 1. 날짜 필터링
                    allowed_dates = [filter_date, filter_date - timedelta(days=1)]
                    if join_date not in allowed_dates:
                        # print(f"⏭️ [Zoom] '{participant_name}' 건너뜀 (날짜 불일치: {join_date})")
                        continue

                    # 2. 수업 시간 필터링 (새로 추가)
                    if start_time and end_time:
                        buffer_before = timedelta(minutes=60)
                        # print(f"DEBUG: Comparing '{participant_name}' | Join: {join_kst} | Window: {start_time-buffer_before} ~ {end_time}")
                        if join_kst < (start_time - buffer_before) or join_kst > end_time:
                            print(f"[SKIP] Zoom participant '{participant_name}' (Out of session: {join_kst})")
                            continue
                except Exception as e:
                    print(f"[WARNING] join_time parsing failed ({join_time_str}): {e}")
            
            # 동일 이름 중복 제거 (같은 사람이 여러 번 입퇴장한 경우)
            name_key = participant_name.strip().lower()
            if name_key and name_key in seen_names:
                continue
            if name_key:
                seen_names.add(name_key)
            
            filtered.append(p)
        
        print(f"[Zoom] Participants: Total {len(participants)} -> Today({filter_date}) {len(filtered)}")
        return filtered

zoom_mgr = ZoomManager()

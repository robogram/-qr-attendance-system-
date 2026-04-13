import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")
ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
MEETING_ID = "88050257474" # Space removed

def get_token():
    url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={ACCOUNT_ID}"
    auth = (CLIENT_ID, CLIENT_SECRET)
    resp = requests.post(url, auth=auth)
    if resp.status_code == 200:
        return resp.json()['access_token']
    else:
        print(f"Auth Error: {resp.status_code} - {resp.text}")
        return None

def check_participants(token):
    # Try /metrics/meetings/{id}/participants?type=live
    url = f"https://api.zoom.us/v2/metrics/meetings/{MEETING_ID}/participants?type=live"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    print(f"Metrics (Live): {resp.status_code} - {resp.text}")

    # Also try /report/meetings/{id}/participants (Past sessions)
    url_past = f"https://api.zoom.us/v2/report/meetings/{MEETING_ID}/participants"
    resp_past = requests.get(url_past, headers=headers)
    print(f"Report (Past): {resp_past.status_code} - {resp_past.text}")

token = get_token()
if token:
    check_participants(token)

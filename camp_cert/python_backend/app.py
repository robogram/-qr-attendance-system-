#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
로보그램 코딩캠프 수료증 발급 웹앱 - 파이썬 로컬 서버 & 실시간 동기화 백엔드
- PC 및 스마트폰 간 수료증 정보(기관, 과목, 교육기간, 학생) 실시간 동기화 API 제공
- 직인 도장 이미지 실시간 업로드 및 동기화 지원
"""

import os
import sys
import json
import socket
import base64
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

# 윈도우 콘솔 CP949 인코딩 이모지 충돌 방지
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PORT = 8080
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_FILE = os.path.join(BASE_DIR, "database", "app_data.json")
CUSTOM_SEAL_PATH = os.path.join(BASE_DIR, "assets", "seal_custom.png")
DEFAULT_SEAL_PATH = os.path.join(BASE_DIR, "assets", "seal.png")

def get_local_ip():
    """현재 PC의 공유기(Wi-Fi) 로컬 IP 주소 자동 탐지"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def read_db():
    if not os.path.exists(DB_FILE):
        return {"institutions": [], "students": [], "seal_updated_at": 0}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[DB Read Error] {e}")
        return {"institutions": [], "students": [], "seal_updated_at": 0}

def write_db(data):
    try:
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[DB Write Error] {e}")
        return False

class CertAppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        # 1. 앱 데이터 전체 조회 API
        if self.path.startswith('/api/data'):
            db_data = read_db()
            db_data['has_custom_seal'] = os.path.exists(CUSTOM_SEAL_PATH)
            resp = json.dumps(db_data, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
            return

        # 2. 실시간 직인 이미지 서빙 API (스마트폰 & PC 공유)
        if self.path.startswith('/api/seal'):
            seal_file = CUSTOM_SEAL_PATH if os.path.exists(CUSTOM_SEAL_PATH) else DEFAULT_SEAL_PATH
            if not os.path.exists(seal_file):
                self.send_error(404, "Seal image not found")
                return
            try:
                with open(seal_file, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            except Exception as e:
                self.send_error(500, f"Error reading seal: {e}")
                return

        # 그 외 일반 정적 파일 서빙
        super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        # 1. 앱 데이터 동기화 API
        if self.path == '/api/data':
            try:
                body = json.loads(post_data.decode('utf-8'))
                current = read_db()
                if 'institutions' in body:
                    current['institutions'] = body['institutions']
                if 'students' in body:
                    current['students'] = body['students']
                if 'seal_updated_at' in body:
                    current['seal_updated_at'] = body['seal_updated_at']
                
                write_db(current)
                resp = json.dumps({"status": "ok", "message": "동기화 완료"}, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                self.send_error(400, f"JSON parse error: {e}")
            return

        # 2. 직인 이미지 업로드 API
        if self.path == '/api/seal':
            try:
                body = json.loads(post_data.decode('utf-8'))
                img_data = body.get('image', '')
                if ',' in img_data:
                    img_data = img_data.split(',', 1)[1]
                
                binary_img = base64.b64decode(img_data)
                with open(CUSTOM_SEAL_PATH, 'wb') as f:
                    f.write(binary_img)

                current = read_db()
                import time
                current['seal_updated_at'] = int(time.time() * 1000)
                write_db(current)

                resp = json.dumps({
                    "status": "ok", 
                    "seal_url": f"/api/seal?t={current['seal_updated_at']}",
                    "seal_updated_at": current['seal_updated_at']
                }, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                self.send_error(400, f"Seal save error: {e}")
            return

        # 3. 기본 직인으로 초기화 API
        if self.path == '/api/seal/reset':
            try:
                if os.path.exists(CUSTOM_SEAL_PATH):
                    os.remove(CUSTOM_SEAL_PATH)
                current = read_db()
                import time
                current['seal_updated_at'] = int(time.time() * 1000)
                write_db(current)

                resp = json.dumps({
                    "status": "ok", 
                    "message": "기본 직인 복원 완료",
                    "seal_url": f"/api/seal?t={current['seal_updated_at']}"
                }, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                self.send_error(500, f"Reset error: {e}")
            return

        self.send_error(404, "Unknown API endpoint")

def main():
    os.chdir(BASE_DIR)
    server_address = ('0.0.0.0', PORT)
    httpd = ThreadingHTTPServer(server_address, CertAppHandler)

    local_ip = get_local_ip()
    local_url = f"http://localhost:{PORT}"
    mobile_url = f"http://{local_ip}:{PORT}"

    print("=" * 65)
    print("🎓 로보그램 코딩캠프 수료증 발급 시스템이 시작되었습니다!")
    print("=" * 65)
    print(f"💻 PC/노트북 접속 주소 : {local_url}")
    print(f"📱 스마트폰 접속 주소  : {mobile_url}")
    print("=" * 65)
    print("✨ PC와 스마트폰 간 실시간 데이터 & 직인 동기화 엔진 활성화")
    print("=" * 65)
    print("서버를 종료하려면 Ctrl + C 를 누르세요.\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")
        httpd.server_close()

if __name__ == '__main__':
    main()

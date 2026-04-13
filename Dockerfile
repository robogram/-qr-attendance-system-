# Python 3.10 기반 슬림 이미지 사용
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 시스템 패키지 설치 (OpenCV 등 대응)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 종속성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 전체 소스 코드 복사
COPY . .

# Hugging Face Spaces 포트 (7860) 노출
EXPOSE 7860

# 실행 권한 부여
RUN chmod +x entrypoint.sh

# 엔트리포인트 실행
CMD ["./entrypoint.sh"]

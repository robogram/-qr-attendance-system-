#!/bin/bash

# 환경 변수 APP_TYPE에 따라 실행할 포털 결정
# (Hugging Face의 'Variables and secrets' 메뉴에서 APP_TYPE을 'staff' 또는 'user'로 설정)

if [ "$APP_TYPE" = "staff" ]; then
    echo "Starting Staff Portal..."
    streamlit run staff_portal.py --server.port 7860 --server.address 0.0.0.0
elif [ "$APP_TYPE" = "user" ]; then
    echo "Starting User Portal..."
    streamlit run user_portal.py --server.port 7860 --server.address 0.0.0.0
else
    echo "APP_TYPE not set or invalid. Defaulting to User Portal..."
    streamlit run user_portal.py --server.port 7860 --server.address 0.0.0.0
fi

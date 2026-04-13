---
title: Robogram QR Attendance
emoji: 🎓
colorFrom: indigo
colorTo: purple
sdk: streamlit
app_file: streamlit_app.py
pinned: false
---

# QR Attendance System - Hybrid Portal
This space provides role-based access to the QR Attendance tracking system.

## Setup
The system uses environment variables for configuration.
- `APP_TYPE`: Set to 'staff' for Teacher/Admin portal or 'user' for Student/Parent portal.
- `SUPABASE_URL`, `SUPABASE_KEY`: Database connection.
- `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET`, `ZOOM_ACCOUNT_ID`: Zoom API integration.

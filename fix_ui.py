import codecs

shutdown_ui = """
    st.markdown('---')
    st.markdown('### 🛑 서버 강제 종료')
    st.info('카메라 스캐너 창을 바로 끌 수 있습니다.')
    if st.button('🛑 QR 카메라(서버) 끄기', use_container_width=True):
        try:
            import requests
            from config import FLASK_PORT
            requests.post(f'http://127.0.0.1:{FLASK_PORT}/api/shutdown', timeout=1)
        except: pass
        st.success('✅ 종료 신호를 보냈습니다!')
"""

for fname in ['admin_app.py', 'teacher_app.py']:
    with codecs.open(fname, 'r', 'utf-8-sig') as f:
        content = f.read()

    if '서버 강제 종료' not in content:
        if '    st.markdown("### 📌 서버 상태")' in content:
            content = content.replace('    st.markdown("### 📌 서버 상태")', shutdown_ui + '\n    st.markdown("### 📌 서버 상태")')
            with codecs.open(fname, 'w', 'utf-8-sig') as f:
                f.write(content)
            print(f"Updated {fname}")
        else:
            print(f"Anchor not found in {fname}")
    else:
        print(f"Already updated {fname}")

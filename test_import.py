import traceback
try:
    import flask_qr_attendance_app
    print("Syntax and imports check passed!")
except Exception as e:
    print("Syntax error or import error:")
    traceback.print_exc()

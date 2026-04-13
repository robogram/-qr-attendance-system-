import pandas as pd
import os

CLASS_GROUPS_CSV = "class_groups.csv"

def check_csv_column():
    print("Checking class_groups.csv for zoom_meeting_id column...")
    if not os.path.exists(CLASS_GROUPS_CSV):
        print("⚠️ class_groups.csv not found.")
        return
    
    try:
        # We need to trigger the update by calling the loading/saving logic
        # Since we can't easily run admin_app.py here, we'll just check if it exists
        # or simulate the logic
        df = pd.read_csv(CLASS_GROUPS_CSV, encoding='utf-8-sig')
        if 'zoom_meeting_id' in df.columns:
            print("✅ zoom_meeting_id column exists.")
        else:
            print("ℹ️ zoom_meeting_id column doesn't exist yet (it will be added on next Admin App save/sync).")
            # Let's add it manually for this test if it's missing to verify the file is writable
            df['zoom_meeting_id'] = ""
            df.to_csv(CLASS_GROUPS_CSV, index=False, encoding='utf-8-sig')
            print("✅ zoom_meeting_id column added successfully.")
    except Exception as e:
        print(f"❌ Error checking CSV: {e}")

def test_robust_matching():
    print("\nTesting robust matching logic...")
    student_map = {"김동혁": 1, "홍길동": 2}
    test_cases = [
        ("김 동 혁", "김동혁"),
        ("A반_홍길동", "홍길동"),
        ("홍 길 동 (학생)", "홍길동"),
        ("외부인", None)
    ]
    
    for zoom_name, expected in test_cases:
        matched_name = None
        zoom_name_clean = zoom_name.replace(" ", "")
        for system_name in student_map:
            system_name_clean = system_name.replace(" ", "")
            if system_name_clean in zoom_name_clean:
                matched_name = system_name
                break
        
        if matched_name == expected:
            print(f"✅ Matched '{zoom_name}' to '{matched_name}' as expected.")
        else:
            print(f"❌ Failed matching '{zoom_name}': expected '{expected}', but got '{matched_name}'")

if __name__ == "__main__":
    check_csv_column()
    test_robust_matching()

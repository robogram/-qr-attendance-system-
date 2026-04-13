def test_matching():
    student_map = {"김동혁": 1, "홍길동": 2, "이삼사": 3}
    participants = [
        {"name": "A반_김동혁"},
        {"name": "홍길동(학생)"},
        {"name": "외부인"},
        {"name": "이삼사 선생님"}
    ]
    
    results = []
    for p in participants:
        zoom_name = p['name']
        matched_student_id = None
        matched_student_name = ""
        
        for system_name, student_id in student_map.items():
            if system_name in zoom_name:
                matched_student_id = student_id
                matched_student_name = system_name
                break
        
        if matched_student_id:
            results.append(f"Matched: {zoom_name} -> {matched_student_name} (ID: {matched_student_id})")
        else:
            results.append(f"No match: {zoom_name}")
            
    for r in results:
        print(r)

if __name__ == "__main__":
    test_matching()

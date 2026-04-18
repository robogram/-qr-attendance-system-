import sys, ast, re

def add_keys_to_file(filepath, prefix):
    with open(filepath, 'r', encoding='utf-8') as f:
        code = f.read()

    lines = code.split('\n')
    
    try:
        tree = ast.parse(code)
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return

    changes = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = getattr(node.func, 'attr', getattr(node.func, 'id', None))
            if func_name in ['button', 'download_button', 'form_submit_button', 'radio', 'checkbox', 'selectbox', 'text_input', 'number_input', 'text_area', 'date_input', 'time_input', 'file_uploader', 'color_picker', 'multiselect', 'slider']:
                has_key = any(kw.arg == 'key' for kw in node.keywords)
                if not has_key:
                    # We found a missing key!
                    # Find the exact line and position to insert the key keyword argument.
                    line_idx = node.end_lineno - 1
                    col_offset = node.end_col_offset
                    
                    # Instead of exact col_offset which might be tricky if formatting changes,
                    # We can use regex on the specific line, or just insert it right before the closing parenthesis.
                    # We know line_idx and col_offset.
                    line = lines[line_idx]
                    
                    # We need to make sure we inserting before the *last* parenthesis of this call
                    # col_offset points to the character AFTER the closing parenthesis in Python 3.8+
                    
                    key_str = f', key="{prefix}_{node.lineno}"'
                    # find the rightmost ')' before col_offset
                    pos = line.rfind(')', 0, col_offset)
                    if pos != -1:
                        # Before inserting, check if the previous character is '(' to avoid ', ' 
                        prev_char_is_open = line[:pos].strip().endswith('(')
                        if prev_char_is_open:
                            insert_str = f'key="{prefix}_{node.lineno}"'
                        else:
                            insert_str = key_str
                            
                        # register change
                        changes.append((line_idx, pos, insert_str))

    if not changes:
        print(f"No missing keys in {filepath}")
        return

    # Apply changes from bottom to top to avoid offset shifting issues
    changes.sort(key=lambda x: (x[0], x[1]), reverse=True)
    
    for line_idx, pos, insert_str in changes:
        line = lines[line_idx]
        lines[line_idx] = line[:pos] + insert_str + line[pos:]
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
        
    print(f"Fixed {len(changes)} missing keys in {filepath}")

if __name__ == '__main__':
    files_to_fix = [
        ('parent_app.py', 'parent_auto'),
        ('Robo_Qr_Attendance_App_Mobile.py', 'mobile_auto'),
        ('student_app.py', 'student_auto'),
        ('teacher_app.py', 'teacher_auto')
    ]
    for filename, prefix in files_to_fix:
        add_keys_to_file(filename, prefix)

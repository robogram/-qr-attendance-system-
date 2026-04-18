import ast

def find_missing_keys(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = None
            if hasattr(node.func, 'attr'):
                func_name = node.func.attr
            elif hasattr(node.func, 'id'):
                func_name = node.func.id
                
            if func_name in ['button', 'download_button', 'form_submit_button', 'radio', 'checkbox', 'selectbox', 'text_input']:
                has_key = any(kw.arg == 'key' for kw in node.keywords)
                if not has_key:
                    print(f"Missing key in {filepath} at line {node.lineno}: {func_name}()")

find_missing_keys('admin_app.py')
find_missing_keys('staff_portal.py')

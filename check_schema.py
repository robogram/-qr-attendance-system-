import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

response = requests.get(f"{SUPABASE_URL}/rest/v1/?apikey={SUPABASE_KEY}", headers=headers)
if response.status_code == 200:
    data = response.json()
    definitions = data.get('definitions', {})
    for table_name in ['users', 'students', 'schedule', 'attendance']:
        if table_name in definitions:
            props = definitions[table_name].get('properties', {})
            print(f"[{table_name}] columns: {list(props.keys())}")
        else:
            print(f"[{table_name}] table not found in OpenAPI spec.")
else:
    print(f"Failed to fetch schema: {response.status_code} {response.text}")

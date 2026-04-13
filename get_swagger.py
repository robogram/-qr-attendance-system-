import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

try:
    res = requests.get(f"{SUPABASE_URL}/rest/v1/", headers={"apikey": SUPABASE_KEY})
    with open("swagger.json", "w", encoding="utf-8") as f:
        json.dump(res.json(), f, indent=2)
    print("Swagger JSON saved to swagger.json")
except Exception as e:
    print(e)

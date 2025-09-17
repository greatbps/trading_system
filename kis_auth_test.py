
import os
import json
import requests
import re

def parse_env(file_path):
    """A simple .env file parser."""
    env_vars = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove surrounding quotes
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                env_vars[key.strip()] = value.strip()
    return env_vars

def test_kis_token():
    """Minimal script to test KIS token authentication."""
    try:
        # --- 1. Configuration ---
        env_file = '.env'
        if not os.path.exists(env_file):
            print(f"Error: {env_file} not found.")
            return

        print(f"Reading configuration from {env_file}...")
        env_config = parse_env(env_file)
        app_key = env_config.get("KIS_APP_KEY")
        app_secret = env_config.get("KIS_APP_SECRET")
        
        if not app_key or not app_secret:
            print("Error: KIS_APP_KEY or KIS_APP_SECRET not found in .env file.")
            return

        url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
        
        headers = {
            "content-type": "application/json; charset=utf-8",
        }
        
        payload = {
            "grant_type": "client_credentials",
            "appkey": app_key,
            "appsecret": app_secret
        }

        print("--- Sending Request ---")
        print(f"URL: POST {url}")
        print(f"Headers: {headers}")
        # Mask secret for printing
        print_payload = payload.copy()
        print_payload['appsecret'] = '***REDACTED***'
        print(f"Payload: {json.dumps(print_payload, indent=2)}")
        print("-----------------------")

        # --- 2. Make Request ---
        res = requests.post(url, headers=headers, json=payload, timeout=10)

        # --- 3. Print Response ---
        print("\n--- Received Response ---")
        print(f"Status Code: {res.status_code}")
        print("Headers:")
        for key, value in res.headers.items():
            print(f"  {key}: {value}")
        
        print("\nBody:")
        # Try to pretty-print if it's JSON, otherwise print as text
        try:
            print(json.dumps(res.json(), indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            # Use regex to find content within body tags if it's HTML
            body_match = re.search(r'<body[^>]*>(.*?)</body>', res.text, re.DOTALL)
            if body_match:
                print(body_match.group(1).strip())
            else:
                print(res.text)
        print("-------------------------")

    except Exception as e:
        print(f"\nAn exception occurred: {e}")

if __name__ == "__main__":
    test_kis_token()

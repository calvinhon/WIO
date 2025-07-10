import json
import subprocess
import sys
from pathlib import Path

def read_key_info_json(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def read_password_rules(filepath):
    return Path(filepath).read_text()

def generate_passwords_with_ollama(password_rules, key_info_json):
    prompt = f"""
You are a password generator assistant for a hackathon. 

Password rules:
{password_rules}

User info:
{json.dumps(key_info_json, indent=2)}

Generate 10 likely passwords that follow the rules and are related to the user info.

IMPORTANT:
- All passwords must strictly follow the password rules.
- Do NOT remove or ignore leading 0s in any set of numbers.
- Do NOT alter anything in user info.
- Do NOT produce any passwords that violate the rules.
- Do NOT provide an explanation of anything.
- Output ONLY a JSON array of strings with exactly 10 passwords.
- If you cannot generate a password following the rules, leave it blank or put "N/A" but still return 10 entries.
"""
    result = subprocess.run(
        ['ollama', 'run', 'mistral:instruct'],
        input=prompt.encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Ollama error: {result.stderr.decode()}")
    return result.stdout.decode()

def main(json_filepath, txt_filepath):
    key_info = read_key_info_json(json_filepath)
    password_rules = read_password_rules(txt_filepath)
    output = generate_passwords_with_ollama(password_rules, key_info)
    print(output)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 generate_passwords.py <key_info.json> <password_rules.txt>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])

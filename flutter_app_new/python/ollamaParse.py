import requests
import json
import os

def parse_with_ollama(ocr_text, source_filename, model="mistral"):
    # Prepare the Ollama local API endpoint
    url = "http://localhost:11434/api/generate"

    # Prompt for the LLM
    prompt = f"""
You are a document extraction assistant. Extract the following financial fields from this scanned credit card statement text:

- Previous Balance
- Payments Received
- Purchases & Cash Advances
- Interest Charges
- Fees
- New Balance
- Minimum Amount Due
- Available Credit Limit
- Credit Limit

Return only a valid JSON dictionary with keys and numeric values.

OCR Text:
\"\"\"
{ocr_text}
\"\"\"
"""

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        content = response.json()["response"]

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            print("⚠️ Couldn't parse model output as JSON:")
            print(content)
            result = {}

    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        result = {}

    # Create output directory if it doesn't exist
    os.makedirs("ollamaParsed", exist_ok=True)

    # Determine output filename
    base_name = os.path.splitext(os.path.basename(source_filename))[0]
    output_path = os.path.join("ollamaParsed", f"{base_name}.json")

    # Save result to file
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"✅ Extracted fields saved to: {output_path}")
    return result

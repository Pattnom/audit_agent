# tools/data_extractor.py
import os
import json
import re
import litellm
import time

import google.generativeai as genai

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def clean_json_string(s: str) -> str:
    """
    Attempt to fix common JSON syntax errors.
    - Remove trailing commas before } or ]
    - Replace single quotes with double quotes (but not inside strings)
    - Ensure keys are double-quoted
    """
    # Remove trailing commas before }
    s = re.sub(r',\s*}', '}', s)
    s = re.sub(r',\s*]', ']', s)
    # Replace single quotes with double quotes for keys and string values (naive)
    # This is a simple approach; may fail if strings contain single quotes.
    # Better to use a proper JSON repair library, but this works for common cases.
    s = re.sub(r"'([^']*)'", r'"\1"', s)
    # Ensure keys are quoted (if missing)
    s = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', s)
    return s

def extract_json_from_text(text: str) -> dict:
    """
    Extract JSON object from text using multiple strategies.
    """
    # Strategy 1: Try to parse the whole text as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Look for JSON inside markdown code blocks
    match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        try:
            return json.loads(clean_json_string(json_str))
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find any {...} with balanced braces (simple approach)
    stack = []
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if not stack:
                start = i
            stack.append(ch)
        elif ch == '}':
            if stack:
                stack.pop()
                if not stack and start != -1:
                    json_str = text[start:i+1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        try:
                            return json.loads(clean_json_string(json_str))
                        except json.JSONDecodeError:
                            # Continue searching
                            start = -1
    # If all fails, raise error
    raise ValueError("No valid JSON found in model response")

def extract_company_data(texts: dict) -> dict:
    """
    Use an LLM to extract structured data from all text.
    texts: dict {filename: extracted_text}
    We combine all text and ask the model to extract fields.
    """
    combined = "\n---\n".join([f"File: {fname}\n{text}" for fname, text in texts.items()])

    prompt = f"""
Extract the following information from the provided documents. Return a JSON object with these fields:

- company_name (string)
- company_address (string)
- siret (string, 14 digits)
- naf_code (string, format like "10.71A")
- year (integer, the year for which the claim is made, e.g., 2024)
- electricity_consumption_mwh (number, **total MWh for the entire year, summing all invoices**. If consumption is given in kWh, convert to MWh by dividing by 1000.)
- electricity_cost_euro (number, total cost of electricity including taxes, in euros, **summed over all invoices**)
- value_added_euro (number, from the tax return, usually line "Valeur ajoutée" in liasses fiscales)
- gas_consumption_mwh (number, if any, else null)
- gas_accise_paid_euro (number, total excise paid on gas, else null)
- production_share_percent (number, estimated percentage of electricity used for production, if available)
- process_description (string, brief description of the industrial process or gas usage)

If a field is missing, set it to null. Use only the information present.

Documents text:
{combined}
"""
    # Call local Ollama model via litellm
    # response = litellm.completion(
    #     model="ollama/qwen2.5-coder:7b",
    #     messages=[{"role": "user", "content": prompt}],
    #     api_base="http://localhost:11434"
    # )

    # Extract content from response
    # content = response.choices[0].message.content

    #model = genai.GenerativeModel("gemini-3.1-flash-lite-preview")
    model = genai.GenerativeModel("gemini-3.1-flash-lite-preview", generation_config={"temperature": 0})
    response = model.generate_content(prompt)
    content = response.text

    time.sleep(1)

    # Debug: print the raw content (you can remove this later)
    print("\n=== RAW MODEL RESPONSE ===")
    print(content)
    print("===========================\n")

    # Parse JSON from the content
    try:
        data = extract_json_from_text(content)
    except ValueError as e:
        # Last resort: try cleaning the whole content
        cleaned = clean_json_string(content)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            raise ValueError(f"Could not parse JSON even after cleaning. Original error: {e}")

    if data.get("electricity_consumption_mwh", 0) < 10:
        print(f"WARNING: Extracted consumption {data['electricity_consumption_mwh']} MWh seems too low. Check the source documents.")

    return data

# This is the tool function that will be wrapped by FunctionTool
def extract_data_tool(texts):
    """
    Extract structured company data from text.
    texts can be a dict (filename -> text) or a JSON string representing such a dict.
    """
    if isinstance(texts, str):
        # Try to parse as JSON
        try:
            texts = json.loads(texts)
        except json.JSONDecodeError:
            # If it's not JSON, treat as a single text input (unlikely, but fallback)
            texts = {"input": texts}
    if not isinstance(texts, dict):
        raise ValueError(f"Expected dict or JSON string, got {type(texts)}")
    return extract_company_data(texts)
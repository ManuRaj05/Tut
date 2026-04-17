import json
import re

# Helper for robust JSON extraction
def clean_json_blocks(text):
    if not text:
        return None
    text = text.strip()
    
    # 1. Remove <think> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()

    # 2. Try direct parse first (if it looks like JSON)
    if text.startswith("{") or text.startswith("["):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # 3. Try to find largest block starting with { and ending with }
    try:
        first_curly = text.find('{')
        last_curly = text.rfind('}')
        if first_curly != -1 and last_curly != -1 and last_curly > first_curly:
            candidate = text[first_curly:last_curly+1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
    except:
        pass

    # 4. Fallback to code block extraction
    if "```json" in text:
        try:
             candidate = text.split("```json")[1].split("```")[0].strip()
             return json.loads(candidate)
        except:
             pass
    elif "```" in text:
        try:
             # Find content inside any code block
             match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
             if match:
                 return json.loads(match.group(1))
        except:
             pass

    # 5. Last ditch effort: try to strip any leading/trailing non-json chars
    try:
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if match:
            return json.loads(match.group(1))
    except:
        pass

    return None

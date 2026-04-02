import os

filepath = "scripts/execute_global_evaluator.py"
with open(filepath, "r") as f:
    code = f.read()

# 1. Imports
if "import hmac" not in code:
    code = code.replace("import requests", "import requests\nimport hashlib\nimport hmac")

# 2. X-DOF-Signature generation
if "_sign_headers" not in code:
    sign_func = """
def _sign_headers(payload: str = "") -> dict:
    qa_key = os.getenv("QAION_PRIVATE_KEY", "dof-local-dev-key")
    signature = hmac.new(qa_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return {"X-DOF-Signature": signature}
"""
    code = code.replace("def _call_adaline", sign_func + "\ndef _call_adaline")

# 3. Headers injection
code = code.replace('headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}', 'headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", **_sign_headers()}')
code = code.replace('headers = {"Content-Type": "application/json"}', 'headers = {"Content-Type": "application/json", **_sign_headers()}')

with open(filepath, "w") as f:
    f.write(code)

print("Patch applied to scripts/execute_global_evaluator.py")

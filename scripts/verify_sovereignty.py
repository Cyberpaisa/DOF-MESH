import hashlib
import os
import sys
import yaml

# CONFIGURATION: Files to protect
CORE_FILES = [
    "core/governance.py",
    "core/cerberus.py",
    "core/ast_verifier.py",
    "dof.constitution.yml"
]

# Note: The 'Baseline' should be updated only by the USER (Antigravity/Sovereign)
# I'll calculate the current clean state hashes now.
BASELINE_FILE = "Sovereign_Vault/audit/baseline_hashes.json"

def calculate_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def check_sovereignty():
    print("[🛡️  CITADEL] Iniciando verificación de Soberanía...")
    violations = []
    
    # Check 1: File Integrity (Hashes)
    if os.path.exists(BASELINE_FILE):
        import json
        with open(BASELINE_FILE, "r") as f:
            baselines = json.load(f)
        
        for filepath, expected_hash in baselines.items():
            if not os.path.exists(filepath):
                violations.append(f"ARCHIVO FALTANTE: {filepath}")
                continue
            
            actual_hash = calculate_sha256(filepath)
            if actual_hash != expected_hash:
                violations.append(f"INTEGRIDAD VIOLADA (Infección/Cambio): {filepath}")
    
    # Check 2: Rule Count (Governance Sanitization)
    try:
        with open("dof.constitution.yml", "r") as f:
            const = yaml.safe_load(f)
            # Support both flat and nested structures
            hard_rules = const.get("HARD_RULES", [])
            if not hard_rules:
                rules_block = const.get("rules", {})
                hard_rules = rules_block.get("hard", [])
            
            if len(hard_rules) < 4:
                violations.append(f"REGLAS ESCASAS ({len(hard_rules)} detectadas). Posible Purga de Gobernanza.")
    except Exception as e:
        violations.append(f"ERROR LEYENDO CONSTITUCIÓN: {e}")

    # Verdict
    if violations:
        print("\n[🚨 ALERTA] VIOLACIÓN DE SOBERANÍA DETECTADA:")
        for v in violations:
            print(f" - {v}")
        print("\n[🚫 FAIL-CLOSED] Abortando ejecución por seguridad.")
        sys.exit(1)
    else:
        print("[✅ OK] Estado: SOBERANO. Verificación de integridad completa.")

def generate_new_baseline():
    import json
    baselines = {}
    for filepath in CORE_FILES:
        if os.path.exists(filepath):
            baselines[filepath] = calculate_sha256(filepath)
    
    os.makedirs(os.path.dirname(BASELINE_FILE), exist_ok=True)
    with open(BASELINE_FILE, "w") as f:
        json.dump(baselines, f, indent=4)
    print(f"[🛡️  CITADEL] Nueva línea base generada en {BASELINE_FILE}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--seal":
        generate_new_baseline()
    else:
        check_sovereignty()

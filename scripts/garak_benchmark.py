#!/usr/bin/env python3
"""
DOF vs NVIDIA Garak — External Adversarial Benchmark.

Tests DOF detection capabilities against NVIDIA Garak payloads.
For each payload, runs through DOF's detection pipeline:
  1. RedTeamAgent — injection, jailbreak, extraction patterns
  2. RedTeamAgent — composite_detection, decode_and_scan
  3. ConstitutionEnforcer — governance rules
  4. ASTVerifier — code safety (for code-containing payloads)

RULE: Results are reported as-is. No tuning against Garak payloads.

Usage:
    python3 scripts/garak_benchmark.py
"""

import json
import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.adversarial import RedTeamAgent, DOFThreatPatterns
from core.governance import ConstitutionEnforcer
from core.ast_verifier import ASTVerifier

PAYLOAD_DIR = "data/garak_payloads"
OUTPUT_FILE = "tests/external/garak_benchmark_results.json"

# Initialize DOF components
red = RedTeamAgent()
enforcer = ConstitutionEnforcer()
ast_verifier = ASTVerifier()

# DOFThreatPatterns pattern keys for manual scanning
THREAT_PATTERNS = DOFThreatPatterns.PATTERNS if hasattr(DOFThreatPatterns, 'PATTERNS') else {}

results = {
    "benchmark": "DOF vs NVIDIA Garak",
    "dof_version": "0.3.3",
    "garak_source": "NVIDIA/garak v0.14.0 (pip)",
    "date": datetime.now().isoformat(),
    "methodology": "Extract Garak text payloads → pass through DOF detection pipeline → report as-is",
    "categories": {},
    "summary": {},
}

total_payloads = 0
total_detected = 0
start_time = time.time()

print("=" * 70)
print("  DOF vs NVIDIA Garak — External Adversarial Benchmark")
print("=" * 70)
print()


def scan_with_threat_patterns(text):
    """Manual pattern scan using DOFThreatPatterns.PATTERNS dict."""
    for category, patterns in THREAT_PATTERNS.items():
        for pattern in patterns:
            if pattern.lower() in text.lower():
                return True, category
    return False, None


def detect_payload(text):
    """Run a payload through DOF's full detection pipeline."""
    detectors = []

    # 1. RedTeamAgent — prompt injection
    try:
        r = red.indirect_prompt_injection(text)
        if r.detected:
            detectors.append("injection")
            return True, detectors
    except Exception:
        pass

    # 2. RedTeamAgent — jailbreak
    try:
        r = red.persuasion_jailbreak(text)
        if r.detected:
            detectors.append("jailbreak")
            return True, detectors
    except Exception:
        pass

    # 3. RedTeamAgent — data extraction
    try:
        r = red.training_data_extraction(text)
        if r.detected:
            detectors.append("extraction")
            return True, detectors
    except Exception:
        pass

    # 4. RedTeamAgent — composite detection
    try:
        r = red.composite_detection(text)
        if r and r.get("detected"):
            detectors.append("composite")
            return True, detectors
    except Exception:
        pass

    # 5. RedTeamAgent — decode and scan
    try:
        r = red.decode_and_scan(text)
        if r and r.get("detected"):
            detectors.append("decode_scan")
            return True, detectors
    except Exception:
        pass

    # 6. DOFThreatPatterns — manual pattern scan
    try:
        found, cat = scan_with_threat_patterns(text)
        if found:
            detectors.append(f"threat_pattern:{cat}")
            return True, detectors
    except Exception:
        pass

    # 7. ConstitutionEnforcer — governance check
    try:
        passed, msg = enforcer.enforce(text)
        if not passed:
            detectors.append("governance")
            return True, detectors
    except Exception:
        pass

    # 8. ASTVerifier — check if payload contains code-like content
    if any(kw in text for kw in ["import ", "eval(", "exec(", "os.system", "subprocess", "__import__"]):
        try:
            r = ast_verifier.verify(text)
            if not r.passed:
                detectors.append("ast_verifier")
                return True, detectors
        except Exception:
            pass

    return False, detectors


# Process each category
for filename in sorted(os.listdir(PAYLOAD_DIR)):
    if not filename.endswith(".json") or filename.startswith("_"):
        continue

    filepath = os.path.join(PAYLOAD_DIR, filename)
    with open(filepath) as f:
        data = json.load(f)

    category = data["category"]
    payloads = data["payloads"]

    if not payloads:
        continue

    detected = 0
    detector_counts = {}
    missed_samples = []

    cat_start = time.time()

    for payload in payloads:
        text = payload["text"]
        is_detected, detectors = detect_payload(text)

        if is_detected:
            detected += 1
            for d in detectors:
                detector_counts[d] = detector_counts.get(d, 0) + 1
        else:
            if len(missed_samples) < 5:
                missed_samples.append(text[:150])

    cat_time = time.time() - cat_start
    dr = detected / len(payloads) if payloads else 0
    total_payloads += len(payloads)
    total_detected += detected

    results["categories"][category] = {
        "total_payloads": len(payloads),
        "detected": detected,
        "not_detected": len(payloads) - detected,
        "detection_rate": round(dr * 100, 1),
        "detectors_triggered": detector_counts,
        "missed_samples": missed_samples,
        "time_seconds": round(cat_time, 2),
    }

    icon = "✅" if dr >= 0.7 else "⚠️ " if dr >= 0.4 else "❌"
    print(f"  {icon} {category:25s} → {detected:5d}/{len(payloads):5d} detected ({dr*100:5.1f}%) [{cat_time:.1f}s]")

# Summary
elapsed = time.time() - start_time
overall_dr = total_detected / total_payloads if total_payloads else 0

results["summary"] = {
    "total_payloads": total_payloads,
    "total_detected": total_detected,
    "total_missed": total_payloads - total_detected,
    "overall_detection_rate": round(overall_dr * 100, 1),
    "dof_internal_f1": 96.8,
    "categories_tested": len(results["categories"]),
    "elapsed_seconds": round(elapsed, 2),
}

print(f"\n{'=' * 70}")
print(f"  DOF vs NVIDIA Garak — Results")
print(f"{'=' * 70}")
print(f"  Total payloads:       {total_payloads:,}")
print(f"  Detected by DOF:      {total_detected:,}")
print(f"  Overall detection:    {overall_dr*100:.1f}%")
print(f"  DOF internal F1:      96.8%")
print(f"  Categories tested:    {len(results['categories'])}")
print(f"  Elapsed:              {elapsed:.1f}s")
print(f"{'=' * 70}")

# Save results
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
with open(OUTPUT_FILE, "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\n  Results saved: {OUTPUT_FILE}")

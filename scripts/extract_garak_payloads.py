#!/usr/bin/env python3
"""
Extract text payloads from NVIDIA Garak probes for DOF external benchmark.

Garak is the industry-standard LLM vulnerability scanner (NVIDIA).
This script extracts the text payloads from Garak probe classes and saves
them as JSON files organized by category.

Usage:
    python3 scripts/extract_garak_payloads.py
"""

import json
import os
import importlib
import sys

OUTPUT_DIR = "data/garak_payloads"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Categories relevant to DOF detection capabilities
CATEGORIES = [
    "dan",                  # DAN jailbreak attacks → RedTeamAgent.persuasion_jailbreak
    "promptinject",         # Direct prompt injection → RedTeamAgent.indirect_prompt_injection
    "leakreplay",          # Data extraction attempts → RedTeamAgent.training_data_extraction
    "malwaregen",          # Malicious code generation → ASTVerifier
    "goodside",            # Known jailbreak techniques → enforce_hierarchy
    "snowball",            # Hallucination probes → DataOracle
    "continuation",        # Continuation attacks → ConstitutionEnforcer
    "glitch",              # Glitch token attacks → DOFThreatPatterns
    "lmrc",                # Language model risk cards → ConstitutionEnforcer
    "misleading",          # Misleading claims → DataOracle
    "packagehallucination", # Package hallucination → ASTVerifier
    "realtoxicityprompts", # Toxicity prompts → ConstitutionEnforcer
    "suffix",              # Adversarial suffixes → DOFThreatPatterns
    "tap",                 # Tree of attacks → RedTeamAgent
]

results = {}
grand_total = 0

print("=" * 60)
print("  NVIDIA Garak Payload Extraction")
print("=" * 60)

for category in CATEGORIES:
    try:
        module = importlib.import_module(f"garak.probes.{category}")

        payloads = []
        probe_classes = []

        for name in dir(module):
            obj = getattr(module, name)
            if not isinstance(obj, type):
                continue

            try:
                instance = obj()
                prompts = getattr(instance, "prompts", None)
                if not prompts or not isinstance(prompts, list):
                    continue

                probe_classes.append(name)
                for prompt in prompts:
                    text = prompt if isinstance(prompt, str) else str(prompt)
                    # Skip non-text payloads (images, binary)
                    if len(text) < 5 or not text.isprintable():
                        continue
                    payloads.append({
                        "id": f"{category}_{len(payloads):04d}",
                        "text": text,
                        "probe_class": name,
                    })
            except Exception:
                continue

        if not payloads:
            print(f"  ⚠  {category:25s} → 0 payloads (skipped)")
            continue

        category_data = {
            "category": category,
            "source": "NVIDIA/garak",
            "garak_version": "0.14.0",
            "probe_classes": probe_classes,
            "payloads": payloads,
            "total": len(payloads),
        }

        filepath = os.path.join(OUTPUT_DIR, f"{category}.json")
        with open(filepath, "w") as f:
            json.dump(category_data, f, indent=2, ensure_ascii=False)

        results[category] = len(payloads)
        grand_total += len(payloads)
        print(f"  ✅ {category:25s} → {len(payloads):5d} payloads ({len(probe_classes)} probes)")

    except ImportError as e:
        print(f"  ❌ {category:25s} → import failed: {e}")
    except Exception as e:
        print(f"  ❌ {category:25s} → error: {e}")

# Summary
print(f"\n{'=' * 60}")
print(f"  Total payloads extracted: {grand_total}")
print(f"  Categories: {len(results)}/{len(CATEGORIES)}")
print(f"  Output: {OUTPUT_DIR}/")
print(f"{'=' * 60}")

# Save summary
summary = {
    "source": "NVIDIA/garak",
    "garak_version": "0.14.0",
    "categories": results,
    "total_payloads": grand_total,
    "total_categories": len(results),
}
with open(os.path.join(OUTPUT_DIR, "_summary.json"), "w") as f:
    json.dump(summary, f, indent=2)

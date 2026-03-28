#!/usr/bin/env python3
"""Prompt Evaluation Gate for CI/CD.

Usage: python3 scripts/prompt_eval_ci.py [--threshold 0.7] [--diff "git diff output"]

Reads diff from stdin or --diff argument.
Exits with code 0 if gate passes, 1 if fails.
"""

import argparse
import sys
import os

# Asegurar que el proyecto esta en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.prompt_eval_gate import PromptEvalGate


def main():
    parser = argparse.ArgumentParser(
        description="Prompt Evaluation Gate for CI/CD"
    )
    parser.add_argument(
        '--threshold', type=float, default=0.7,
        help='Minimum pass rate threshold (0.0-1.0, default: 0.7)'
    )
    parser.add_argument(
        '--diff', type=str, default=None,
        help='Git diff text (reads from stdin if not provided)'
    )
    args = parser.parse_args()

    # Leer diff
    if args.diff is not None:
        diff_text = args.diff
    elif not sys.stdin.isatty():
        diff_text = sys.stdin.read()
    else:
        print("Error: No diff provided. Pipe git diff or use --diff argument.")
        sys.exit(1)

    gate = PromptEvalGate()

    # Detectar archivos con cambios en prompts
    affected_files = gate.detect_prompt_changes(diff_text)

    if not affected_files:
        print("No prompt changes detected. Gate: PASS")
        sys.exit(0)

    print(f"Prompt changes detected in {len(affected_files)} file(s):")
    for f in affected_files:
        print(f"  - {f}")

    # Extraer prompts de archivos afectados
    all_prompts = []
    for file_path in affected_files:
        # Resolver ruta relativa al repo
        if not os.path.isabs(file_path):
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.join(repo_root, file_path)
        prompts = gate.extract_prompts_from_file(file_path)
        all_prompts.extend(prompts)

    if not all_prompts:
        print("No extractable prompts found. Gate: PASS")
        sys.exit(0)

    print(f"\nExtracted {len(all_prompts)} prompt(s). Running evaluation...")

    # Correr gate
    result = gate.run_gate(all_prompts, threshold=args.threshold)

    # Imprimir reporte
    print("\n" + result.report)

    # Exit code
    if result.passed:
        print("Gate: PASS")
        sys.exit(0)
    else:
        print("Gate: FAIL")
        sys.exit(1)


if __name__ == '__main__':
    main()

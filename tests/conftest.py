from pathlib import Path

import pytest


def pytest_collection_modifyitems(items):
    tests_root = Path(__file__).parent.resolve()

    for item in items:
        try:
            rel_path = Path(str(item.fspath)).resolve().relative_to(tests_root)
        except ValueError:
            continue

        parts = rel_path.parts
        if not parts:
            continue

        top_level = parts[0]

        if top_level == "integration":
            item.add_marker(pytest.mark.integration)
        elif top_level == "scientific":
            item.add_marker(pytest.mark.scientific)
            item.add_marker(pytest.mark.onchain)
            item.add_marker(pytest.mark.optional)
            item.add_marker(pytest.mark.slow)
        elif top_level == "stress":
            item.add_marker(pytest.mark.stress)
            item.add_marker(pytest.mark.slow)
        elif top_level == "scratch":
            item.add_marker(pytest.mark.scratch)
            item.add_marker(pytest.mark.optional)
        elif top_level == "red_team":
            item.add_marker(pytest.mark.red_team)
            item.add_marker(pytest.mark.optional)

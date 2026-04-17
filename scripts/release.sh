#!/bin/bash
# release.sh — DOF-MESH release automation
# Usage:
#   ./scripts/release.sh 0.9.0          # release explicit version
#   ./scripts/release.sh patch          # auto-bump: 0.8.0 → 0.8.1
#   ./scripts/release.sh minor          # auto-bump: 0.8.0 → 0.9.0
#   ./scripts/release.sh major          # auto-bump: 0.8.0 → 1.0.0
#   ./scripts/release.sh 0.9.0 --dry-run  # preview only, no changes
#
# Requires: PYPI_API_TOKEN in env (source .env first)
# Commits use author: Cyber <jquiceva@gmail.com>

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
INIT_FILE="$REPO/dof/__init__.py"
PYPROJECT="$REPO/pyproject.toml"
DRY_RUN=false
VERSION=""

# ── Parse args ────────────────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        patch|minor|major)
            # Auto-bump from current version
            CURRENT=$(grep '__version__' "$INIT_FILE" | sed "s/.*['\"]\\(.*\\)['\"].*/\\1/")
            IFS='.' read -r _MAJOR _MINOR _PATCH <<< "$CURRENT"
            case "$arg" in
                major) _MAJOR=$((_MAJOR+1)); _MINOR=0; _PATCH=0 ;;
                minor) _MINOR=$((_MINOR+1)); _PATCH=0 ;;
                patch) _PATCH=$((_PATCH+1)) ;;
            esac
            VERSION="$_MAJOR.$_MINOR.$_PATCH"
            ;;
        [0-9]*.*) VERSION="$arg" ;;
    esac
done

if [[ -z "$VERSION" ]]; then
    echo "Usage: ./scripts/release.sh <version|patch|minor|major> [--dry-run]"
    echo "Examples:"
    echo "  ./scripts/release.sh 0.9.0"
    echo "  ./scripts/release.sh patch    # auto-bump patch"
    exit 1
fi

cd "$REPO"

echo "=== DOF-MESH Release v$VERSION ==="
[[ "$DRY_RUN" == true ]] && echo ">>> DRY RUN — no changes will be made <<<"

# ── 1. Verify clean working tree ───────────────────────────────────────────────
DIRTY=$(git status --porcelain | { grep -v "^??" || true; } | wc -l | tr -d ' ')
if [[ "$DIRTY" -gt 0 ]]; then
    echo "ERROR: Working tree has $DIRTY uncommitted changes. Commit or stash first."
    exit 1
fi
echo "✓ Working tree clean"

# ── 2. Run tests ───────────────────────────────────────────────────────────────
echo "Running tests..."
if [[ "$DRY_RUN" == false ]]; then
    python3 -m unittest discover -s tests -q 2>&1 | tail -3
    echo "✓ Tests passed"
else
    echo "  [dry-run] Skipping tests"
fi

# ── 3. Check PYPI_API_TOKEN ────────────────────────────────────────────────────
if [[ -z "${PYPI_API_TOKEN:-}" ]]; then
    echo "ERROR: PYPI_API_TOKEN not set. Run: source .env"
    exit 1
fi
echo "✓ PYPI_API_TOKEN found"

# ── 4. Bump version ────────────────────────────────────────────────────────────
CURRENT=$(grep '__version__' "$INIT_FILE" | sed "s/.*'\(.*\)'.*/\1/")
echo "Bumping $CURRENT → $VERSION"

if [[ "$DRY_RUN" == false ]]; then
    # dof/__init__.py
    sed -i '' "s/__version__ = \"$CURRENT\"/__version__ = \"$VERSION\"/" "$INIT_FILE"
    # pyproject.toml
    sed -i '' "s/^version = \"$CURRENT\"/version = \"$VERSION\"/" "$PYPROJECT"
    echo "✓ Version bumped in __init__.py and pyproject.toml"
else
    echo "  [dry-run] Would set version $VERSION in $INIT_FILE and $PYPROJECT"
fi

# ── 5. Verify version sync ─────────────────────────────────────────────────────
if [[ "$DRY_RUN" == false ]]; then
    INIT_VER=$(grep '__version__' "$INIT_FILE" | sed "s/.*'\(.*\)'.*/\1/;s/.*\"\(.*\)\".*/\1/")
    PROJ_VER=$(grep '^version = ' "$PYPROJECT" | sed 's/version = "\(.*\)"/\1/')
    if [[ "$INIT_VER" != "$VERSION" || "$PROJ_VER" != "$VERSION" ]]; then
        echo "ERROR: Version mismatch — init=$INIT_VER pyproject=$PROJ_VER expected=$VERSION"
        exit 1
    fi
    echo "✓ Version sync verified: $INIT_VER"
fi

# ── 6. Commit version bump ─────────────────────────────────────────────────────
if [[ "$DRY_RUN" == false ]]; then
    git add "$INIT_FILE" "$PYPROJECT"
    git commit --author="Cyber <jquiceva@gmail.com>" -m "chore: bump version to $VERSION"
    echo "✓ Version commit created"
else
    echo "  [dry-run] Would commit version bump"
fi

# ── 7. Tag ─────────────────────────────────────────────────────────────────────
if [[ "$DRY_RUN" == false ]]; then
    git tag "v$VERSION" -m "Release v$VERSION"
    echo "✓ Tag v$VERSION created"
else
    echo "  [dry-run] Would create tag v$VERSION"
fi

# ── 8. Build ───────────────────────────────────────────────────────────────────
echo "Building distribution..."
if [[ "$DRY_RUN" == false ]]; then
    rm -rf dist/
    python3 -m build --quiet
    echo "✓ Build complete: $(ls dist/)"
else
    echo "  [dry-run] Would run: python3 -m build"
fi

# ── 9. Upload to PyPI ──────────────────────────────────────────────────────────
if [[ "$DRY_RUN" == false ]]; then
    echo "Uploading to PyPI..."
    TWINE_USERNAME=__token__ TWINE_PASSWORD="$PYPI_API_TOKEN" \
        twine upload dist/* --non-interactive
    echo "✓ Published dof-sdk==$VERSION to PyPI"
else
    echo "  [dry-run] Would upload dist/ to PyPI"
fi

# ── 10. Push tag ───────────────────────────────────────────────────────────────
echo ""
echo "Next step (manual — Soberano approves push):"
echo "  git push origin main --tags"
echo ""
echo "=== Release v$VERSION complete ==="

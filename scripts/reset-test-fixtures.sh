#!/usr/bin/env bash
set -euo pipefail

OWNER="alexjuda"
REPO="rv-testing"
BRANCH="test/fixtures"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $*" >&2; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

command -v gh >/dev/null 2>&1 || error "gh CLI is required"
command -v jq >/dev/null 2>&1 || error "jq is required"
gh auth status --hostname github.com >/dev/null 2>&1 || error "Not authenticated with gh"

ORIG_DIR=$(pwd)
WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

info "Cloning $OWNER/$REPO..."
gh repo clone "$OWNER/$REPO" "$WORKDIR" >/dev/null 2>&1 || error "Failed to clone $OWNER/$REPO"
cd "$WORKDIR"

# Ensure main branch has the base calculator.py
info "Setting up main branch with base calculator.py..."
git checkout main >/dev/null 2>&1

cat > calculator.py << 'BASE_EOF'
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
BASE_EOF

if ! git diff --quiet; then
    git add -A
    git commit -m "chore: add base calculator.py for e2e test fixtures" >/dev/null
    git push origin main >/dev/null 2>&1 || error "Failed to push main"
    info "Updated main branch with base calculator.py"
else
    info "main branch already up-to-date"
fi

# Create test/fixtures branch with the extended calculator.py
info "Creating $BRANCH branch with fixture content..."
git checkout -b "$BRANCH" >/dev/null 2>&1

cat > calculator.py << 'FIXTURE_EOF'
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def factorial(n):
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result


def fibonacci(n):
    if n < 0:
        raise ValueError("Fibonacci not defined for negative numbers")
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
FIXTURE_EOF

git add -A
git commit -m "test: add factorial and fibonacci for e2e test fixtures" >/dev/null
git push -f origin "$BRANCH" >/dev/null 2>&1 || error "Failed to push $BRANCH"

# Create PR
info "Opening PR..."
gh pr close "$BRANCH" 2>/dev/null || true
gh pr create \
  --base main \
  --head "$BRANCH" \
  --title "chore: test fixtures for rv e2e tests" \
  --body "This PR provides the diff that rv's e2e tests exercise against." \
  >/dev/null 2>&1 || true

PR_NUMBER=$(gh pr view --json number --jq '.number') || error "Failed to get PR number"
PR_URL="https://github.com/$OWNER/$REPO/pull/$PR_NUMBER"
info "PR #$PR_NUMBER: $PR_URL"

COMMIT_SHA=$(git rev-parse HEAD)

# Wait for GitHub to process the push
sleep 5

info "Creating review threads..."

# Thread 1: Unresolved — comment on factorial's for-loop (file line 19)
gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" \
  --method POST \
  --field body="Consider using \`math.factorial\` from the standard library. It's more readable and uses optimized C code." \
  --field commit_id="$COMMIT_SHA" \
  --field path="calculator.py" \
  --field line=19 \
  --field side="RIGHT" \
  >/dev/null || error "Failed to create unresolved thread"

# Thread 2: Multi-line — spanning fibonacci base cases (file lines 26-29)
gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" \
  --method POST \
  --field body="The \`if/elif/else\` chain for the base cases could be simplified to \`if n <= 1: return n\`." \
  --field commit_id="$COMMIT_SHA" \
  --field path="calculator.py" \
  --field line=29 \
  --field start_line=26 \
  --field side="RIGHT" \
  --field start_side="RIGHT" \
  >/dev/null || error "Failed to create multi-line thread"

# Thread 3: Resolved — comment, reply, then resolve via GraphQL
COMMENT_3=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" \
  --method POST \
  --field body="This tuple unpacking is correct, but consider a \`temp\` variable for clarity." \
  --field commit_id="$COMMIT_SHA" \
  --field path="calculator.py" \
  --field line=33 \
  --field side="RIGHT" \
  --jq '.id') || error "Failed to create resolved thread base comment"

# Reply
gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" \
  --method POST \
  --field body="Good point, simplified." \
  --field commit_id="$COMMIT_SHA" \
  --field path="calculator.py" \
  --field line=33 \
  --field side="RIGHT" \
  --field in_reply_to="$COMMENT_3" \
  >/dev/null || error "Failed to reply on resolved thread"

# Resolve via GraphQL
THREAD_3_NODE=$(gh api graphql -f query="query {
  repository(owner: \"$OWNER\", name: \"$REPO\") {
    pullRequest(number: $PR_NUMBER) {
      reviewThreads(first: 20) {
        nodes {
          id
          comments(first: 1) {
            nodes { databaseId }
          }
        }
      }
    }
  }
}" --jq ".data.repository.pullRequest.reviewThreads.nodes[] | select(.comments.nodes[0].databaseId == $COMMENT_3) | .id") || true

if [ -n "$THREAD_3_NODE" ]; then
  gh api graphql -f query="mutation { resolveReviewThread(input: {threadId: \"$THREAD_3_NODE\"}) { thread { isResolved } } }" \
    >/dev/null && info "Thread 3 resolved" || info "Note: could not resolve thread 3"
else
  info "Note: could not find thread node for resolution"
fi

# Thread 4: Thread with replies — comment on fibonacci function (line 23), two replies
COMMENT_4=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" \
  --method POST \
  --field body="Should add docstrings to the public functions for better tooling support." \
  --field commit_id="$COMMIT_SHA" \
  --field path="calculator.py" \
  --field line=23 \
  --field side="RIGHT" \
  --jq '.id') || error "Failed to create thread with replies base comment"

gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" \
  --method POST \
  --field body="Good idea, I'll add them." \
  --field commit_id="$COMMIT_SHA" \
  --field path="calculator.py" \
  --field line=23 \
  --field side="RIGHT" \
  --field in_reply_to="$COMMENT_4" \
  >/dev/null || error "Failed to add first reply"

gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" \
  --method POST \
  --field body="Added docstrings in the latest iteration." \
  --field commit_id="$COMMIT_SHA" \
  --field path="calculator.py" \
  --field line=23 \
  --field side="RIGHT" \
  --field in_reply_to="$COMMENT_4" \
  >/dev/null || error "Failed to add second reply"

# Re-record VCR cassettes (if tests exist)
if [ -f "$ORIG_DIR/pyproject.toml" ] && grep -q "vcrpy\|pytest-vcr" "$ORIG_DIR/pyproject.toml" 2>/dev/null; then
    info "Re-recording VCR cassettes..."
    info "  Run: cd $ORIG_DIR && uv run pytest tests/ --vcr-record=all"
fi

echo ""
echo "=========================================="
info "Test fixtures reset complete!"
info "PR: $PR_URL"
echo "=========================================="

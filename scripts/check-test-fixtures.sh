#!/usr/bin/env bash
set -euo pipefail

OWNER="alexjuda"
REPO="rv-testing"
BRANCH="test/fixtures"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $*" >&2; }
fail() { echo -e "${RED}[FAIL]${NC} $*" >&2; FAILED=1; }

command -v gh >/dev/null 2>&1 || { echo "[FAIL] gh CLI is required" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "[FAIL] jq is required" >&2; exit 1; }

FAILED=0

echo "Checking $OWNER/$REPO for branch $BRANCH..."

PR_NUMBER=$(gh pr view "$BRANCH" --repo "$OWNER/$REPO" --json number --jq '.number' 2>/dev/null) || {
    fail "No open PR found for branch '$BRANCH'"
    echo "  Run scripts/reset-test-fixtures.sh first"
    exit 1
}

PR_URL="https://github.com/$OWNER/$REPO/pull/$PR_NUMBER"
info "PR #$PR_NUMBER: $PR_URL"

echo ""

# Use GraphQL to get thread data — resolves and line ranges are accurate here
THREADS=$(gh api graphql -f query="query {
  repository(owner: \"$OWNER\", name: \"$REPO\") {
    pullRequest(number: $PR_NUMBER) {
      reviewThreads(first: 20) {
        nodes {
          isResolved
          startLine
          line
          comments(first: 5) {
            totalCount
          }
        }
      }
    }
  }
}" --jq '.data.repository.pullRequest.reviewThreads.nodes') || {
    fail "Failed to fetch threads"
    exit 1
}

TOTAL=$(echo "$THREADS" | jq 'length')
UNRESOLVED=$(echo "$THREADS" | jq '[.[] | select(.isResolved == false)] | length')
RESOLVED=$(echo "$THREADS" | jq '[.[] | select(.isResolved == true)] | length')
MULTI_LINE=$(echo "$THREADS" | jq '[.[] | select(.startLine != null and .startLine != .line)] | length')
HAS_REPLIES=$(echo "$THREADS" | jq '[.[] | select(.comments.totalCount > 1)] | length')

if [ "$UNRESOLVED" -ge 1 ]; then
    info "[PASS] $UNRESOLVED unresolved thread(s)"
else
    fail "Need at least 1 unresolved thread, found $UNRESOLVED"
fi

if [ "$RESOLVED" -ge 1 ]; then
    info "[PASS] $RESOLVED resolved thread(s)"
else
    fail "Need at least 1 resolved thread, found $RESOLVED"
fi

if [ "$MULTI_LINE" -ge 1 ]; then
    info "[PASS] $MULTI_LINE multi-line thread(s)"
else
    fail "Need at least 1 multi-line thread, found $MULTI_LINE"
fi

if [ "$HAS_REPLIES" -ge 1 ]; then
    info "[PASS] $HAS_REPLIES thread(s) with replies"
else
    fail "Need at least 1 thread with replies, found $HAS_REPLIES"
fi

echo ""
echo "Results: $TOTAL total, $UNRESOLVED unresolved, $RESOLVED resolved, $MULTI_LINE multi-line, $HAS_REPLIES with replies"

exit "$FAILED"

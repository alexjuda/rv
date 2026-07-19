# rv

CLI for PR code review.

## Development

```bash
uv sync
make format
make typecheck
make test
```

## Integration Tests

Integration tests in `tests/test_integration_github.py` use `pytest-recording`
to record and replay HTTP interactions against
[`alexjuda/rv-testing`](https://github.com/alexjuda/rv-testing), a private repo.
By default tests replay from cassettes in `tests/fixtures/`, bypassing any real
network access.

To re-record the fixtures:

1. Run `scripts/check-test-fixtures.sh` to verify the test repo PR has the
   expected thread properties. It uses `gh` under the hood, and assumes you have
   access to the private testing repo. If the repo state needs refreshing, run
   `scripts/reset-test-fixtures.sh`.

2. Remove the recorded cassettes and run the tests with `--record-mode=once` and
   a valid `GITHUB_TOKEN` env var. It should be a PAT, scoped to `repo` access
   in `alexjuda/rv-testing`.

    ```bash
    rm -r tests/fixtures
    GITHUB_TOKEN=ghp_... uv run pytest tests/ --record-mode=once
    ```

from datetime import datetime
from pathlib import Path

import pytest
from pytest import fixture

from rv.domain.models.actions import CollectionStat, StatusSummary, ThreadStat
from rv.domain.models.github import (
    PR,
    FullPR,
    PRConversation,
    PRLocator,
    RepoLocator,
    Thread,
    ThreadComment,
)
from rv.domain.models.storage import SyncMeta

# ---- pytest plugin config ----


def _mangle_token_expiration(response):
    response["headers"]["github-authentication-token-expiration"] = (
        "2021-01-01 09:01:01 UTC"
    )
    return response


@pytest.fixture(autouse=True)
def vcr_config():
    # Arguments for the VCR init, as a dict. See also: https://vcrpy.readthedocs.io/en/latest/advanced.html
    return {
        "filter_headers": [
            ("Authorization", "Bearer <TOKEN>"),
        ],
        "before_record_response": _mangle_token_expiration,
        "cassette_library_dir": str(Path(__file__).parent / "fixtures"),
        "decode_compressed_response": True,
    }


# ---- fixtures for sample data for domain models ----


@fixture()
def sample_thread_comment():
    return ThreadComment(
        id="2",
        body="Make this nicer",
        author="alexjuda",
        created_at=datetime.fromisoformat("2021-06-21T23:48:12+01:00"),
    )


@fixture
def sample_thread(sample_thread_comment: ThreadComment):
    return Thread(
        id="PR_1",
        is_resolved=False,
        path="src/hello.py",
        line=10,
        commit_sha="deadbeef",
        comments=[sample_thread_comment],
    )


@fixture
def sample_convo(sample_thread: Thread):
    return PRConversation(
        threads=[sample_thread],
        pr_comments=[],
        reviews=[],
    )


@fixture
def sample_repo():
    return RepoLocator("owner", "repo")


@fixture
def sample_pr_locator(sample_repo: RepoLocator):
    return PRLocator(repo=sample_repo, number=42)


@fixture
def sample_pr(sample_pr_locator: PRLocator):
    return PR(
        locator=sample_pr_locator,
        url="github.com/owner/repo/pulls/42",
        title="feat: something",
        author="alexjuda",
        base_branch="main",
        head_branch="feat/sth",
        state="open",
        latest_commit="c4f3b4b3",
    )


@fixture
def sample_full_pr(sample_pr: PR, sample_convo: PRConversation):
    return FullPR(
        pr=sample_pr,
        convo=sample_convo,
    )


@fixture
def sample_sync_meta():
    return SyncMeta(
        synced_at=datetime.fromisoformat("2021-06-21T23:48:12+01:00"),
    )


@fixture
def sample_status_summary():
    return StatusSummary(
        stored_n_prs=10,
        stale_n_prs=3,
        pending_comments_stat=CollectionStat(n_new=2, n_deleted=3, n_changed=4),
        pending_threads_stat=ThreadStat(n_new=5, n_deleted=6, n_resolved=7),
        pending_n_prs=8,
        unresolved_n_threads=9,
        unresolved_n_prs=2,
        unreviewed_n_prs=2,
        reviewed_n_prs=4,
    )

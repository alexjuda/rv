import pytest
from pydantic import ValidationError

from rv.adapters.github_models import (
    _GHActor,
    _GHCommentConnection,
    _GHFindPRData,
    _GHFullPR,
    _GHFullPRData,
    _GHGraphQLEnvelope,
    _GHPRListData,
    _GHReviewConnection,
    _GHReviewThreadConnection,
)


class TestGHGraphQLEnvelope:
    @staticmethod
    def test_valid_response():
        raw = {"data": {"key": "value"}}
        envelope = _GHGraphQLEnvelope.model_validate(raw)
        assert envelope.data == {"key": "value"}
        assert envelope.errors is None

    @staticmethod
    def test_errors_without_data():
        raw = {"data": None, "errors": [{"message": "Not found", "type": "NOT_FOUND"}]}
        envelope = _GHGraphQLEnvelope.model_validate(raw)
        assert envelope.data is None
        assert envelope.errors is not None
        assert len(envelope.errors) == 1
        assert envelope.errors[0].message == "Not found"

    @staticmethod
    def test_errors_with_data():
        raw = {"data": {"key": "value"}, "errors": [{"message": "warning"}]}
        envelope = _GHGraphQLEnvelope.model_validate(raw)
        assert envelope.data == {"key": "value"}
        assert envelope.errors is not None
        assert len(envelope.errors) == 1

    @staticmethod
    def test_empty_envelope():
        raw = {}
        envelope = _GHGraphQLEnvelope.model_validate(raw)
        assert envelope.data is None
        assert envelope.errors is None


class TestGHFindPRData:
    @staticmethod
    def test_with_pr():
        data = {"repository": {"pullRequests": {"nodes": [{"number": 42}]}}}
        parsed = _GHFindPRData.model_validate(data)
        assert parsed.repository is not None
        assert parsed.repository.pullRequests is not None
        nodes = parsed.repository.pullRequests.nodes
        assert nodes is not None
        assert nodes[0].number == 42

    @staticmethod
    def test_empty_nodes():
        data = {"repository": {"pullRequests": {"nodes": []}}}
        parsed = _GHFindPRData.model_validate(data)
        assert parsed.repository is not None
        assert parsed.repository.pullRequests is not None
        assert parsed.repository.pullRequests.nodes == []

    @staticmethod
    def test_null_nodes():
        data = {"repository": {"pullRequests": {"nodes": None}}}
        parsed = _GHFindPRData.model_validate(data)
        assert parsed.repository is not None
        assert parsed.repository.pullRequests is not None
        assert parsed.repository.pullRequests.nodes is None

    @staticmethod
    def test_null_repository():
        data = {"repository": None}
        parsed = _GHFindPRData.model_validate(data)
        assert parsed.repository is None


class TestGHFullPRData:
    @staticmethod
    def test_null_pull_request():
        data = {"repository": {"pullRequest": None}}
        parsed = _GHFullPRData.model_validate(data)
        assert parsed.repository is not None
        assert parsed.repository.pullRequest is None

    @staticmethod
    def test_null_repository():
        data = {"repository": None}
        parsed = _GHFullPRData.model_validate(data)
        assert parsed.repository is None

    @staticmethod
    def test_null_author():
        data = {
            "repository": {
                "pullRequest": {
                    "url": "https://github.com/o/r/pull/1",
                    "title": "Test",
                    "author": None,
                    "baseRefName": "main",
                    "headRefName": "feature",
                    "state": "OPEN",
                    "headRefOid": "abc123",
                    "comments": {"nodes": []},
                    "reviews": {"nodes": []},
                    "reviewThreads": {"nodes": []},
                }
            }
        }
        parsed = _GHFullPRData.model_validate(data)
        pull_request = parsed.repository
        assert pull_request is not None
        assert pull_request.pullRequest is not None
        assert pull_request.pullRequest.author is None

    @staticmethod
    def test_null_commit_on_review():
        data = {
            "repository": {
                "pullRequest": {
                    "url": "https://github.com/o/r/pull/1",
                    "title": "Test",
                    "author": {"login": "user"},
                    "baseRefName": "main",
                    "headRefName": "feature",
                    "state": "OPEN",
                    "headRefOid": "abc123",
                    "comments": {"nodes": []},
                    "reviews": {
                        "nodes": [
                            {
                                "id": "r1",
                                "author": {"login": "user"},
                                "body": "",
                                "createdAt": "2024-01-01T00:00:00Z",
                                "state": "APPROVED",
                                "commit": None,
                            }
                        ]
                    },
                    "reviewThreads": {"nodes": []},
                }
            }
        }
        parsed = _GHFullPRData.model_validate(data)
        repo = parsed.repository
        assert repo is not None
        pr = repo.pullRequest
        assert pr is not None
        reviews = pr.reviews
        assert reviews is not None
        nodes = reviews.nodes
        assert nodes is not None
        assert nodes[0].commit is None

    @staticmethod
    def test_null_line():
        data = {
            "repository": {
                "pullRequest": {
                    "url": "https://github.com/o/r/pull/1",
                    "title": "Test",
                    "author": {"login": "user"},
                    "baseRefName": "main",
                    "headRefName": "feature",
                    "state": "OPEN",
                    "headRefOid": "abc123",
                    "comments": {"nodes": []},
                    "reviews": {"nodes": []},
                    "reviewThreads": {
                        "nodes": [
                            {
                                "id": "t1",
                                "isResolved": True,
                                "path": "file.py",
                                "line": None,
                                "comments": {"nodes": []},
                            }
                        ]
                    },
                }
            }
        }
        parsed = _GHFullPRData.model_validate(data)
        repo = parsed.repository
        assert repo is not None
        pr = repo.pullRequest
        assert pr is not None
        threads = pr.reviewThreads
        assert threads is not None
        nodes = threads.nodes
        assert nodes is not None
        thread = nodes[0]
        assert thread.path == "file.py"
        assert thread.line is None

    @staticmethod
    def test_null_body_rejected():
        data = {
            "repository": {
                "pullRequest": {
                    "url": "https://github.com/o/r/pull/1",
                    "title": "Test",
                    "author": {"login": "user"},
                    "baseRefName": "main",
                    "headRefName": "feature",
                    "state": "OPEN",
                    "headRefOid": "abc123",
                    "comments": {
                        "nodes": [
                            {
                                "id": "c1",
                                "author": {"login": "user"},
                                "body": None,
                                "createdAt": "2024-01-01T00:00:00Z",
                            }
                        ]
                    },
                    "reviews": {"nodes": []},
                    "reviewThreads": {"nodes": []},
                }
            }
        }
        with pytest.raises(ValidationError):
            _GHFullPRData.model_validate(data)

    @staticmethod
    def test_null_author_on_thread_comment():
        data = {
            "repository": {
                "pullRequest": {
                    "url": "https://github.com/o/r/pull/1",
                    "title": "Test",
                    "author": {"login": "user"},
                    "baseRefName": "main",
                    "headRefName": "feature",
                    "state": "OPEN",
                    "headRefOid": "abc123",
                    "comments": {"nodes": []},
                    "reviews": {"nodes": []},
                    "reviewThreads": {
                        "nodes": [
                            {
                                "id": "t1",
                                "isResolved": True,
                                "path": "file.py",
                                "line": 10,
                                "comments": {
                                    "nodes": [
                                        {
                                            "id": "tc1",
                                            "body": "comment",
                                            "author": None,
                                            "createdAt": "2024-01-01T00:00:00Z",
                                        }
                                    ]
                                },
                            }
                        ]
                    },
                }
            }
        }
        parsed = _GHFullPRData.model_validate(data)
        repo = parsed.repository
        assert repo is not None
        pr = repo.pullRequest
        assert pr is not None
        threads = pr.reviewThreads
        assert threads is not None
        nodes = threads.nodes
        assert nodes is not None
        comments = nodes[0].comments
        assert comments is not None
        tc_nodes = comments.nodes
        assert tc_nodes is not None
        assert tc_nodes[0].author is None

    @staticmethod
    def test_null_nodes_on_connection():
        data = {
            "repository": {
                "pullRequest": {
                    "url": "https://github.com/o/r/pull/1",
                    "title": "Test",
                    "author": {"login": "user"},
                    "baseRefName": "main",
                    "headRefName": "feature",
                    "state": "OPEN",
                    "headRefOid": "abc123",
                    "comments": {"nodes": None},
                    "reviews": {"nodes": None},
                    "reviewThreads": {"nodes": None},
                }
            }
        }
        parsed = _GHFullPRData.model_validate(data)
        repo = parsed.repository
        assert repo is not None
        pr = repo.pullRequest
        assert pr is not None
        assert pr.comments.nodes is None
        assert pr.reviews is not None
        assert pr.reviews.nodes is None
        assert pr.reviewThreads.nodes is None

    @staticmethod
    def test_missing_required_field_raises():
        data = {
            "repository": {
                "pullRequest": {
                    "url": "https://github.com/o/r/pull/1",
                    "title": "Test",
                    "author": {"login": "user"},
                    "baseRefName": "main",
                    "headRefName": "feature",
                    "state": "OPEN",
                    "headRefOid": "abc123",
                    "comments": {
                        "nodes": [
                            {
                                "id": None,
                                "author": {"login": "user"},
                                "body": "text",
                                "createdAt": "2024-01-01T00:00:00Z",
                            }
                        ]
                    },
                    "reviews": {"nodes": []},
                    "reviewThreads": {"nodes": []},
                }
            }
        }
        with pytest.raises(ValidationError):
            _GHFullPRData.model_validate(data)


class TestGHFullPR:
    @staticmethod
    def test_empty_string_body_accepted():
        model = _GHFullPR(
            url="https://github.com/o/r/pull/1",
            title="Test",
            author=_GHActor(login="user"),
            baseRefName="main",
            headRefName="feature",
            state="OPEN",
            headRefOid="abc123",
            comments=_GHCommentConnection(nodes=[]),
            reviews=_GHReviewConnection(nodes=[]),
            reviewThreads=_GHReviewThreadConnection(nodes=[]),
        )
        assert model.state == "OPEN"


class TestGHPRListData:
    @staticmethod
    def test_null_end_cursor():
        data = {
            "repository": {
                "pullRequests": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }
        parsed = _GHPRListData.model_validate(data)
        assert parsed.repository is not None
        pull_requests = parsed.repository.pullRequests
        assert pull_requests is not None
        page_info = pull_requests.pageInfo
        assert page_info is not None
        assert page_info.endCursor is None

    @staticmethod
    def test_null_author():
        data = {
            "repository": {
                "pullRequests": {
                    "nodes": [
                        {
                            "number": 1,
                            "title": "Test",
                            "author": None,
                            "url": "https://github.com/o/r/pull/1",
                            "baseRefName": "main",
                            "headRefName": "feature",
                            "state": "OPEN",
                            "headRefOid": "abc123",
                        }
                    ],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }
        parsed = _GHPRListData.model_validate(data)
        assert parsed.repository is not None
        pull_requests = parsed.repository.pullRequests
        assert pull_requests is not None
        nodes = pull_requests.nodes
        assert nodes is not None
        assert nodes[0].author is None

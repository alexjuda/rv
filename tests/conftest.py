from pathlib import Path

import pytest


def _mangle_token_expiration(response):
    response["headers"]["github-authentication-token-expiration"] = "2021-01-01 09:01:01 UTC"
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

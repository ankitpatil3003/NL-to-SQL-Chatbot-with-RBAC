import pytest

from app.auth.tokens import InvalidToken, issue_token, read_token

SECRET = "s" * 40


def test_round_trip() -> None:
    assert read_token(issue_token("U009", SECRET, 5), SECRET) == "U009"


@pytest.mark.parametrize(
    "token",
    [
        issue_token("U009", "another-secret-of-sufficient-length!!", 5),  # forged signature
        issue_token("U009", SECRET, -1),  # expired
        "not-a-jwt",
    ],
)
def test_rejects_bad_tokens(token: str) -> None:
    with pytest.raises(InvalidToken):
        read_token(token, SECRET)


def test_rejects_alg_none() -> None:
    import jwt

    unsigned = jwt.encode({"sub": "U001", "exp": 9999999999}, key=None, algorithm="none")
    with pytest.raises(InvalidToken):
        read_token(unsigned, SECRET)

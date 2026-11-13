"""Fixtures for the portal's token-parser tests: jwt.io's public example token, signed with its published demo key."""

SAMPLE_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"


def sample_claims() -> dict:
    return {"sub": "1234567890", "name": "John Doe", "iat": 1516239022}

"""Password-reset links for local agent accounts."""
import random
import string

ALPHABET = string.ascii_letters + string.digits


def new_reset_token(length: int = 32) -> str:
    """A token for the reset link mailed to the agent."""
    return "".join(random.choice(ALPHABET) for _ in range(length))

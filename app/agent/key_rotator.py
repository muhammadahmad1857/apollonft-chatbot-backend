"""
API key rotator.

Put multiple Gemini keys in .env as:
    GOOGLE_API_KEYS=key1,key2,key3

On any 429 / quota-exhausted error the rotator moves to the next key,
updates os.environ["GOOGLE_API_KEY"] (which the ADK reads), and returns
the new key so the caller can retry.
"""

import os
import threading
import logging

logger = logging.getLogger(__name__)


class KeyRotator:
    def __init__(self, keys: list[str]) -> None:
        self._keys = [k.strip() for k in keys if k.strip()]
        if not self._keys:
            raise ValueError("KeyRotator requires at least one API key.")
        self._idx = 0
        self._lock = threading.Lock()
        self._apply(self._keys[0])

    # ── public ───────────────────────────────────────────────────────────────

    @property
    def current_key(self) -> str:
        return self._keys[self._idx]

    @property
    def num_keys(self) -> int:
        return len(self._keys)

    def rotate(self) -> str:
        """Advance to the next key, apply it, and return it.

        Raises RuntimeError if there is only one key (nothing to rotate to).
        """
        with self._lock:
            if len(self._keys) == 1:
                raise RuntimeError("Only one API key configured — cannot rotate.")
            self._idx = (self._idx + 1) % len(self._keys)
            new_key = self._keys[self._idx]

        self._apply(new_key)
        logger.warning(
            "[KeyRotator] Rotated to key index %d/%d (***%s)",
            self._idx + 1,
            len(self._keys),
            new_key[-4:],
        )
        return new_key

    # ── private ──────────────────────────────────────────────────────────────

    def _apply(self, key: str) -> None:
        os.environ["GOOGLE_API_KEY"] = key
        # Also configure the google-generativeai client if it is imported
        try:
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=key)
        except ImportError:
            pass


def is_quota_error(exc: BaseException) -> bool:
    """Return True if the exception is a Gemini rate-limit / quota error."""
    msg = str(exc).lower()
    return any(
        token in msg
        for token in ("429", "resource_exhausted", "quota", "rate limit", "rateerror")
    )

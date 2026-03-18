from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Shared session service — lives for the process lifetime.
# Preserves conversation history across runner rebuilds.
session_service = InMemorySessionService()

# Module-level runner reference; replaced by rebuild_runner() on key rotation.
_runner: Runner | None = None


def _make_runner() -> Runner:
    from app.agent.agent import build_agent  # import here to always get fresh agent
    return Runner(
        agent=build_agent(),
        app_name="apollonft",
        session_service=session_service,
    )


def get_runner() -> Runner:
    global _runner
    if _runner is None:
        _runner = _make_runner()
    return _runner


def rebuild_runner() -> Runner:
    """Recreate the Runner (and its underlying genai Client) with the API key
    that is currently set in os.environ["GOOGLE_API_KEY"].
    Called automatically after key rotation in chat.py."""
    global _runner
    _runner = _make_runner()
    return _runner


# Convenience alias used by voice.py / other routers that imported `runner` directly.
# They can keep `from app.agent.runner import runner` and this shim will be stale,
# so those callers should be updated to use get_runner().  For chat.py we use get_runner().
runner = get_runner()

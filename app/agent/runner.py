from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.agent.agent import agent

session_service = InMemorySessionService()

runner = Runner(
    agent=agent,
    app_name="apollonft",
    session_service=session_service,
)

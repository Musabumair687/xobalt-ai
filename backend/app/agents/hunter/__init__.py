"""Hunter agent package.

Exposes the main entry points other modules need:
- HunterState  – the LangGraph state TypedDict
- hunter nodes – individual workflow step functions
"""

from app.agents.hunter.state import HunterState

__all__ = ["HunterState"]

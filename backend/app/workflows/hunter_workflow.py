"""Hunter LangGraph workflow definition.

This file answers: in what order does Hunter perform its work?

The graph:
    START
      ↓
    discover_companies
      ↓
    deduplicate
      ↓
    find_people
      ↓
    enrich
      ↓
    verify
      ↓
    store
      ↓
    END

The `store` node requires a database session.  For async workflows you
should create the session before invoking the graph and pass it via
the RunnableConfig or inject it at build time.

Usage (without DB, e.g. tests)::

    from app.workflows.hunter_workflow import build_hunter_graph
    graph = build_hunter_graph()

Usage (with DB for full run)::

    from app.workflows.hunter_workflow import build_hunter_graph
    from app.database.dependencies import get_db

    async with get_db() as db:
        graph = build_hunter_graph(db=db)
        result = await graph.ainvoke(initial_state)
"""

from __future__ import annotations

import functools
import logging
from typing import Optional

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.hunter.nodes import (
    deduplicate,
    discover_companies,
    enrich,
    find_people,
    store,
    verify,
)
from app.agents.hunter.state import HunterState

logger = logging.getLogger(__name__)


def build_hunter_graph(
    db: Optional[AsyncSession] = None,
) -> StateGraph:
    """Construct and compile the Hunter LangGraph StateGraph.

    Args:
        db: An open AsyncSession to use for the `store` node.
            If None, the `store` node will log a warning and skip DB writes.
    """
    graph = StateGraph(HunterState)

    # Register nodes
    graph.add_node("discover_companies", discover_companies)
    graph.add_node("deduplicate", deduplicate)
    graph.add_node("find_people", find_people)
    graph.add_node("enrich", enrich)
    graph.add_node("verify", verify)

    # The store node needs a DB session — bind it via functools.partial
    if db is not None:
        store_node = functools.partial(store, db=db)
    else:
        async def store_node(state: HunterState) -> dict:  # type: ignore[misc]
            logger.warning(
                "Hunter store node: no DB session provided — skipping persistence."
            )
            return {"lead_ids": [], "warnings": state.get("warnings", []) + ["no_db_session"]}

    graph.add_node("store", store_node)

    # Wire edges
    graph.add_edge(START, "discover_companies")
    graph.add_edge("discover_companies", "deduplicate")
    graph.add_edge("deduplicate", "find_people")
    graph.add_edge("find_people", "enrich")
    graph.add_edge("enrich", "verify")
    graph.add_edge("verify", "store")
    graph.add_edge("store", END)

    return graph.compile()


def get_initial_state(criteria_dict: dict) -> HunterState:
    """Build an empty HunterState from a raw criteria dictionary."""
    from app.schemas.hunter import HunterCriteria

    criteria = HunterCriteria(**criteria_dict)
    return HunterState(
        criteria=criteria,
        discovered_companies=[],
        deduplicated_companies=[],
        people={},
        enriched_companies=[],
        verification_results=[],
        lead_ids=[],
        errors=[],
        warnings=[],
    )

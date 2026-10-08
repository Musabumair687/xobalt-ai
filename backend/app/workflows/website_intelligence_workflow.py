"""LangGraph workflow for Website Intelligence."""

import functools
from langgraph.graph import StateGraph, START, END
from app.agents.website_intelligence.state import WebsiteIntelligenceState
from app.agents.website_intelligence.nodes import discover_pages, fetch_content, extract_intelligence
from app.services.page_discovery_service import PageDiscoveryService
from app.services.content_extraction_service import ContentExtractionService
from app.services.intelligence_service import IntelligenceService

def build_website_intelligence_graph(
    discovery_service: PageDiscoveryService,
    extraction_service: ContentExtractionService,
    intelligence_service: IntelligenceService
) -> StateGraph:
    """Builds and compiles the Website Intelligence workflow graph."""
    
    graph = StateGraph(WebsiteIntelligenceState)
    
    # Bind dependencies to nodes
    node_discover = functools.partial(discover_pages, discovery_service=discovery_service)
    node_fetch = functools.partial(fetch_content, extraction_service=extraction_service)
    node_extract = functools.partial(extract_intelligence, intelligence_service=intelligence_service)
    
    graph.add_node("discover", node_discover)
    graph.add_node("fetch", node_fetch)
    graph.add_node("extract", node_extract)
    
    graph.add_edge(START, "discover")
    graph.add_edge("discover", "fetch")
    graph.add_edge("fetch", "extract")
    graph.add_edge("extract", END)
    
    return graph.compile()

"""LLM prompts used by the Hunter workflow.

Design rule: Only use an LLM where deterministic code is not sufficient.
Everything in this module is used for intelligent extraction/normalization
tasks that rule-based code cannot reliably handle.

Current uses
------------
- Parsing messy company snippets from search results into structured fields.
- Normalizing ambiguous job titles to canonical decision-maker roles.

Future uses (Phase 5+)
-----------------------
- Research summaries (Website Intelligence).
- ICP fit reasoning.
"""

# ---------------------------------------------------------------------------
# Company extraction prompt
# ---------------------------------------------------------------------------

EXTRACT_COMPANY_INFO_PROMPT = """\
You are a data extraction assistant for a B2B lead generation system.

Given the raw text snippet below from a web search result, extract structured
company information and return it as JSON.

If a field cannot be determined from the text, use null.

Required JSON keys:
- name (string): Company's legal or trading name.
- domain (string | null): Primary website domain (e.g. "abcrealty.com").
- industry (string | null): Primary industry or sector.
- employee_count (integer | null): Approximate number of employees.
- city (string | null): City where the company is headquartered.
- state (string | null): US state (2-letter code preferred).
- country (string | null): ISO country code (e.g. "US").
- description (string | null): 1-2 sentence company description.

Snippet:
{snippet}

Return ONLY valid JSON, no additional text.
"""


# ---------------------------------------------------------------------------
# Job-title normalization prompt
# ---------------------------------------------------------------------------

NORMALIZE_TITLE_PROMPT = """\
You are a B2B sales assistant.

Given the job title below, decide whether this person is likely a
decision-maker for a small business (10-100 employees).

Decision-maker titles include: CEO, Founder, Co-Founder, Owner, President,
Managing Director, Managing Partner, Principal, and equivalents.

Return a JSON object with:
- is_decision_maker (boolean)
- normalized_title (string): A clean, short version of the title.

Title: {title}

Return ONLY valid JSON, no additional text.
"""

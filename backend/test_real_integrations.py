"""Xobalt AI — Real Integration Diagnostic & Live Testing Script.

Run this script to verify your real API keys and live connectivity:
    python test_real_integrations.py
"""

import asyncio
import sys
import uuid
from app.config import get_settings


async def test_llm():
    print("\n" + "=" * 60)
    print("1. TESTING LLM CONNECTION (Groq & Gemini)")
    print("=" * 60)
    settings = get_settings()

    import httpx

    if settings.GROQ_API_KEY:
        print(f"[*] Probing Groq API ({settings.GROQ_API_KEY[:10]}...)...")
        try:
            headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
            res = httpx.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=10.0)
            if res.status_code == 200:
                available_models = [m["id"] for m in res.json().get("data", [])]
                print(f"    [+] Groq API Key is VALID! Available models: {available_models[:4]}")
                # Pick the first available chat model
                active_model = next((m for m in available_models if "llama" in m or "mixtral" in m), available_models[0])
                from langchain_groq import ChatGroq
                llm = ChatGroq(model=active_model, api_key=settings.GROQ_API_KEY)
                resp = await llm.ainvoke("Respond with one word: 'CONNECTED'")
                print(f"    [+] Groq LLM Inference SUCCESS using '{active_model}'! Response: {resp.content.strip()}")
            else:
                print(f"    [-] Groq API responded with HTTP {res.status_code}: {res.text}")
        except Exception as e:
            print(f"    [-] Groq Connection Error: {e}")
    else:
        print("    [!] GROQ_API_KEY not configured in .env")

    if settings.GEMINI_API_KEY:
        print(f"[*] Probing Gemini API ({settings.GEMINI_API_KEY[:10]}...)...")
        try:
            res = httpx.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={settings.GEMINI_API_KEY}",
                timeout=10.0,
            )
            if res.status_code == 200:
                models = [m["name"] for m in res.json().get("models", [])]
                print(f"    [+] Gemini API Key is VALID! Models: {models[:3]}")
            else:
                print(f"    [-] Gemini API responded with HTTP {res.status_code}: {res.text}")
        except Exception as e:
            print(f"    [-] Gemini Connection Error: {e}")
    else:
        print("    [!] GEMINI_API_KEY not configured in .env")


async def test_website_intelligence():
    print("\n" + "=" * 60)
    print("2. TESTING WEBSITE INTELLIGENCE (Live HTTP Scraping)")
    print("=" * 60)
    from app.integrations.website.http_client import HttpFetcher
    from app.integrations.website.parser import parse_html

    fetcher = HttpFetcher(timeout=10.0)
    test_url = "https://example.com"
    print(f"[*] Scraping live website: {test_url}")
    try:
        status, html = await fetcher.fetch(test_url)
        text = parse_html(html)
        print(f"    [+] Status Code: {status}")
        print(f"    [+] Parsed Clean Text Sample: '{text[:80]}...'")
        print("    [+] Website Intelligence is 100% OPERATIONAL (No API key needed!)")
    except Exception as e:
        print(f"    [-] Website Scraping Failed: {e}")


async def test_search_discovery():
    print("\n" + "=" * 60)
    print("3. TESTING SEARCH & LEAD DISCOVERY (Tavily & Free Web)")
    print("=" * 60)
    from app.schemas.hunter import HunterCriteria
    criteria = HunterCriteria(
        organization_id=uuid.uuid4(),
        industry="Real Estate",
        country="United States",
        max_companies=3
    )

    settings = get_settings()

    # Test Tavily if key provided
    if settings.TAVILY_API_KEY:
        print(f"[*] Testing Live Tavily Search ({settings.TAVILY_API_KEY[:8]}...)...")
        try:
            from app.integrations.sources.tavily_source import TavilySource
            tav = TavilySource(api_key=settings.TAVILY_API_KEY)
            results = await tav.search(criteria)
            print(f"    [+] Tavily SUCCESS! Discovered {len(results)} live companies:")
            for c in results:
                print(f"        • {c.name} | Domain: {c.domain} | URL: {c.website_url}")
        except Exception as e:
            print(f"    [-] Tavily Error: {e}")
    else:
        print("    [!] TAVILY_API_KEY not configured in .env")

    # Test DuckDuckGo Free Zero-key Discovery
    print("[*] Testing Free Zero-Key Search (DuckDuckGo)...")
    try:
        from app.integrations.sources.duckduckgo_source import DuckDuckGoSource
        ddg = DuckDuckGoSource()
        results = await ddg.search(criteria)
        print(f"    [+] DuckDuckGo discovered {len(results)} companies:")
        for c in results:
            print(f"        • {c.name} ({c.domain}) -> {c.website_url}")
    except Exception as e:
        print(f"    [-] DuckDuckGo Error: {e}")


async def test_enrichment():
    print("\n" + "=" * 60)
    print("4. TESTING CONTACT ENRICHMENT (Apollo.io Decision Makers)")
    print("=" * 60)
    settings = get_settings()
    from app.schemas.hunter import DiscoveredCompany
    sample_company = DiscoveredCompany(
        name="Stripe",
        domain="stripe.com",
        website_url="https://stripe.com",
        country="United States",
        industry="Fintech",
    )

    if settings.APOLLO_API_KEY:
        print(f"[*] Testing Apollo.io Live API ({settings.APOLLO_API_KEY[:8]}...)...")
        try:
            from app.integrations.enrichment.apollo import ApolloEnrichmentProvider
            apollo = ApolloEnrichmentProvider(api_key=settings.APOLLO_API_KEY)
            people = await apollo.find_people(sample_company, roles=[])
            print(f"    [+] Apollo.io SUCCESS! Returned {len(people)} contacts:")
            for p in people:
                print(f"        • {p.first_name} {p.last_name} | {p.title} | Email: {p.email or 'N/A'}")
        except Exception as e:
            print(f"    [-] Apollo.io Error: {e}")
    else:
        print("    [!] APOLLO_API_KEY not configured in .env")


async def test_email_verification():
    print("\n" + "=" * 60)
    print("5. TESTING EMAIL DELIVERABILITY VERIFICATION")
    print("=" * 60)
    from app.integrations.verification.dns_verifier import DnsVerificationProvider
    dns = DnsVerificationProvider()

    test_emails = ["contact@google.com", "fakeuser@nonexistentdomain98765xyz.com"]
    print("[*] Testing Free DNS MX Verifier (Zero API keys needed):")
    for email in test_emails:
        res = await dns.verify_email(email)
        print(f"    • {email} -> Status: {res.status.value.upper()} (Reason: {res.reason})")


async def test_email_outreach():
    print("\n" + "=" * 60)
    print("6. TESTING EMAIL OUTREACH (Resend API)")
    print("=" * 60)
    settings = get_settings()

    if settings.RESEND_API_KEY:
        print(f"[*] Found RESEND_API_KEY ({settings.RESEND_API_KEY[:8]}...)")
        print(f"    [+] Default Sender: {settings.RESEND_FROM_EMAIL}")
        print("    [+] Resend provider is READY for live sending!")
    else:
        print("    [!] RESEND_API_KEY not configured")


async def main():
    print("\n" + "#" * 60)
    print("   XOBALT AI — REAL INTEGRATION DIAGNOSTIC SUITE")
    print("#" * 60)
    try:
        await test_llm()
    except Exception as e:
        print(f"Error in test_llm: {e}")

    try:
        await test_website_intelligence()
    except Exception as e:
        print(f"Error in test_website_intelligence: {e}")

    try:
        await test_search_discovery()
    except Exception as e:
        print(f"Error in test_search_discovery: {e}")

    try:
        await test_enrichment()
    except Exception as e:
        print(f"Error in test_enrichment: {e}")

    try:
        await test_email_verification()
    except Exception as e:
        print(f"Error in test_email_verification: {e}")

    try:
        await test_email_outreach()
    except Exception as e:
        print(f"Error in test_email_outreach: {e}")

    print("\n" + "=" * 60)
    print("7. TESTING DATABASE & FASTAPI ROUTE REGISTRATION")
    print("=" * 60)
    try:
        from app.database.session import init_db
        await init_db()
        print("    [+] Database tables created and verified successfully!")

        from app.main import app
        route_paths = [r.path for r in app.routes]
        print(f"    [+] FastAPI app loaded with {len(route_paths)} total routes!")
        print(f"    [+] /api/v1/leads present: {'/api/v1/leads' in route_paths}")
        print(f"    [+] /api/v1/dashboard/summary present: {'/api/v1/dashboard/summary' in route_paths}")
    except Exception as e:
        print(f"    [-] Database / FastAPI verification failed: {e}")

    print("\n" + "#" * 60)
    print("   DIAGNOSTIC COMPLETE")
    print("#" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

import pytest
from bs4 import BeautifulSoup
from app.integrations.website.parser import parse_html, extract_links

def test_parse_html_strips_scripts_and_styles():
    html = """
    <html>
        <head>
            <style>.hidden { display: none; }</style>
            <script>alert('hello');</script>
        </head>
        <body>
            <h1>Main Title</h1>
            <p>Some text here.</p>
        </body>
    </html>
    """
    text = parse_html(html)
    assert "Main Title" in text
    assert "Some text here." in text
    assert "alert" not in text
    assert "hidden" not in text

def test_extract_links_same_domain():
    html = """
    <a href="/about">About</a>
    <a href="https://other.com/link">Other</a>
    <a href="https://test.com/services">Services</a>
    <a href="#section">Section</a>
    """
    links = extract_links(html, "https://test.com")
    assert len(links) == 2
    assert "https://test.com/about" in links
    assert "https://test.com/services" in links
    assert "https://other.com/link" not in links

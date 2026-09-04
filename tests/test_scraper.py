import os
import pytest
from bs4 import BeautifulSoup
from collector import IPOJiClient

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

def test_parse_detail_fixture():
    # A small test using a mocked HTML fixture to ensure our regexes don't silently fail 
    # if IPO Ji changes their markup.
    
    fixture_path = os.path.join(FIXTURE_DIR, "sample_detail.html")
    if not os.path.exists(fixture_path):
        pytest.skip("Fixture not found. Please add sample_detail.html to tests/fixtures/")
        
    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()
        
    client = IPOJiClient()
    
    class MockResponse:
        def __init__(self, text):
            self.text = text
            
        def raise_for_status(self):
            pass

    # Mock the get call to return our fixture
    original_get = client.get
    client.get = lambda url: MockResponse(html)
    
    try:
        result = client.parse_detail("http://mock.url")
        
        # Check that we extracted *something* successfully rather than returning Nones
        assert result.get("fresh_issue") is not None, "Failed to extract fresh_issue"
        assert result.get("listing_exchange") is not None, "Failed to extract listing_exchange"
    finally:
        client.get = original_get

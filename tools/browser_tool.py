"""
Browser Automation Tool Module
Provides capabilities to open websites in a headless browser, wait dynamically for dynamic content,
and clean raw HTML using BeautifulSoup to extract structured, clutter-free article text. Powered by Playwright.
"""

import asyncio
import logging
import re
from bs4 import BeautifulSoup
try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

# Setup module-level logger
logger = logging.getLogger(__name__)

def clean_html_with_bs4(html_content: str) -> str:
    """
    Parses and cleans raw HTML content using BeautifulSoup and lxml.
    Removes headers, footers, sidebars, forms, advertisements, and interactive elements.
    Validates text blocks to ensure only meaningful article headings and paragraphs remain.
    
    Args:
        html_content (str): Raw HTML string from the page.
        
    Returns:
        str: Structured, cleaned markdown-like article text.
    """
    if not html_content or not html_content.strip():
        return ""

    soup = BeautifulSoup(html_content, "lxml")

    # 1. Strip structural, visual, and interactive noise tags
    noise_tags = [
        "script", "style", "noscript", "iframe", "svg", "form", "header", 
        "footer", "nav", "aside", "select", "option", "button", "input", 
        "textarea", "dialog", "menu", "link", "meta", "kbd", "hr"
    ]
    for tag in soup.find_all(noise_tags):
        tag.decompose()

    # 2. Decompose elements with IDs or classes containing navigational/advertising keywords
    noise_patterns = re.compile(
        r"menu|nav|footer|header|sidebar|aside|social|share|comment|cookie|consent|banner|"
        r"advertisement|promo|widget|popup|login|signup|auth|breadcrumb|toc|table-of-contents", 
        re.I
    )
    for element in soup.find_all(attrs={"class": noise_patterns}):
        if element.name not in ["html", "body"]:
            element.decompose()
    for element in soup.find_all(attrs={"id": noise_patterns}):
        if element.name not in ["html", "body"]:
            element.decompose()

    # 3. Target priority article container selectors if present
    content_areas = soup.find_all(attrs={"role": "main"}) or soup.find_all(["article", "main"])
    if not content_areas:
        # Fallback to containers with content-like classes
        content_patterns = re.compile(r"content|article|post|body|story|main-container", re.I)
        content_areas = soup.find_all("div", attrs={"class": content_patterns})

    # Focus selection area
    target_soup = soup
    if content_areas:
        # Merge all primary text zones together
        temp_div = soup.new_tag("div")
        for area in content_areas:
            temp_div.append(area)
        target_soup = temp_div

    # 4. Extract headings and paragraphs in order
    extracted_text = []
    text_elements = target_soup.find_all(["h1", "h2", "h3", "h4", "p"])
    
    # Track unique text lines to prevent boilerplate repetitions
    seen_texts = set()

    for el in text_elements:
        text = el.get_text()
        # Clean double spacing and newlines
        cleaned = re.sub(r"\s+", " ", text).strip()
        
        # Deduplicate
        if cleaned.lower() in seen_texts:
            continue
            
        # Validation checks
        if el.name.startswith("h"):
            # Keep headings with a reasonable length
            if 3 <= len(cleaned) <= 120:
                extracted_text.append(f"\n## {cleaned}\n")
                seen_texts.add(cleaned.lower())
        elif el.name == "p":
            # Keep paragraphs that form complete sentences (at least 40 characters)
            if len(cleaned) >= 40:
                # Filter out obvious cookie notices, terms, or signup boilerplate
                noise_words = [
                    "cookie", "subscribe", "newsletter", "sign in", "privacy policy", 
                    "terms of service", "copyright ©", "all rights reserved", "log in"
                ]
                if not any(w in cleaned.lower() for w in noise_words):
                    extracted_text.append(cleaned)
                    seen_texts.add(cleaned.lower())

    # 5. Anti-empty fallback handler
    if not extracted_text:
        logger.warning("[Browser Automation] Aggressive cleaning stripped all text. Initiating fallback parsing...")
        original_soup = BeautifulSoup(html_content, "lxml")
        # Strip script and styles only, retrieve raw body paragraphs
        for tag in original_soup.find_all(["script", "style"]):
            tag.decompose()
            
        fallback_elements = original_soup.find_all(["h1", "h2", "h3", "h4", "p"])
        for el in fallback_elements:
            text = el.get_text()
            cleaned = re.sub(r"\s+", " ", text).strip()
            if len(cleaned) >= 30 and cleaned.lower() not in seen_texts:
                extracted_text.append(cleaned)
                seen_texts.add(cleaned.lower())

    # Return double-spaced paragraphs for clear readability formatting
    return "\n\n".join(extracted_text).strip()

async def scrape_article_async(url: str, timeout: int = 12000) -> str:
    """
    Asynchronously opens a webpage using Playwright, waits dynamically for scripts
    and elements to load, extracts raw HTML, and returns the cleaned text.
    
    Args:
        url (str): The target webpage URL.
        timeout (int): Navigation timeout in milliseconds (default 12 seconds).
        
    Returns:
        str: Structured, cleaned article content.
    """
    if not url or not url.strip() or not url.startswith("http"):
        logger.warning(f"Invalid URL provided to scrape: {url}")
        return ""

    print(f"[*] Browser Automation: Launching headless browser for: {url}...")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-setuid-sandbox",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-extensions"
                ]
            )
            
            # Setup emulated context
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            # 1. Open webpage
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            
            # 2. Dynamic wait handling: Wait for body tag to render
            await page.wait_for_selector("body", timeout=2500)
            
            # 3. Wait for network connections to idle (optional, capped at 1.5 seconds)
            try:
                await page.wait_for_load_state("networkidle", timeout=1500)
            except Exception:
                logger.debug("Network idle state timeout reached; continuing execution.")

            # 4. Extract complete page content HTML
            raw_html = await page.content()
            
            await context.close()
            await browser.close()
            
            # 5. Run the HTML cleaning pipeline
            cleaned_content = clean_html_with_bs4(raw_html)
            print(f"[*] Browser Automation: Successfully extracted {len(cleaned_content)} cleaned characters from {url}.")
            return cleaned_content
            
    except Exception as e:
        print(f"[!] Browser Automation Error for {url}: {e}")
        logger.error(f"Playwright scrape error for {url}: {e}", exc_info=True)
        return ""

def scrape_article(url: str) -> str:
    """
    Synchronous scraper that attempts a fast HTTP requests call first.
    If it fails, gets rate-limited, or returns a skeleton/empty content,
    it falls back to loading the page dynamically via Playwright.
    
    Args:
        url (str): The target webpage URL.
        
    Returns:
        str: The extracted, cleaned article content.
    """
    import requests
    
    if not url or not url.strip() or not url.startswith("http"):
        logger.warning(f"Invalid URL provided to scrape: {url}")
        return ""
        
    print(f"[*] Scraper: Attempting fast HTTP request for: {url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 (HTML/CSS, like Gecko) Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Upgrade-Insecure-Requests": "1"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=4)
        if response.status_code == 200:
            cleaned = clean_html_with_bs4(response.text)
            if len(cleaned.strip()) > 1000:
                print(f"[*] Scraper: Fast HTTP request succeeded ({len(cleaned)} chars) for: {url}")
                return cleaned
            else:
                print(f"[*] Scraper: Fast HTTP request returned too little content ({len(cleaned)} chars). Falling back to Playwright...")
        else:
            print(f"[*] Scraper: Fast HTTP request returned status {response.status_code}. Falling back to Playwright...")
    except Exception as e:
        print(f"[*] Scraper: Fast HTTP request failed ({e}). Falling back to Playwright...")

    # Fallback to headless Playwright
    try:
        return asyncio.run(scrape_article_async(url))
    except Exception as e:
        print(f"[!] Browser Automation Sync Loop Error: {e}")
        logger.error(f"Playwright sync wrapper error: {e}", exc_info=True)
        return ""

# Standalone testing block
if __name__ == "__main__":
    print("=== Testing Playwright Browser Scraper ===")
    test_url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
    scraped_text = scrape_article(test_url)
    
    if scraped_text:
        print("\n" + "="*60)
        print(f"Extracted Content (First 600 chars):\n\n{scraped_text[:600]}...")
        print("="*60 + "\n")
    else:
        print("\nFailed to extract content from test page.")

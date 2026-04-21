import asyncio
import sys
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from typing import Dict, Any


class CrawlError(Exception):
    """Raised when webpage crawling fails."""

async def capture_conversion_context(url: str) -> Dict[str, Any]:
    schema = {
    "name": "Conversion Elements",
    "baseSelector": "body",
    "fields": [  
        {"name": "headlines", "selector": "h1, h2", "type": "text"},
        {"name": "ctas", "selector": "a.button, button, .cta", "type": "text"},
        {"name": "forms", "selector": "form", "type": "count"}
    ]
}

    run_config = CrawlerRunConfig(
    screenshot=True,
    # This replaces 'full_page'—it auto-scrolls to trigger lazy loading
    scan_full_page=True, 
    scroll_delay=0.5,     # Gives sections time to load while scrolling
    
    # If you only wanted the top part, you'd set this to True:
    force_viewport_screenshot=False, 
    
    wait_for="body", 
    magic=True,
    remove_overlay_elements=True,
    cache_mode=CacheMode.BYPASS,
    markdown_generator=DefaultMarkdownGenerator(), 
    extraction_strategy=JsonCssExtractionStrategy(schema)
)

    try:
        async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
            result = await asyncio.wait_for(
                crawler.arun(url=url, config=run_config),
                timeout=90,
            )

            if not result.success:
                raise CrawlError(f"Crawl failed: {result.error_message}")

            markdown = getattr(result.markdown, "raw_markdown", None)
            if not markdown:
                raise CrawlError("Crawl returned empty markdown")
            if not result.screenshot:
                raise CrawlError("Crawl returned empty screenshot")

            try:
                structured_elements = (
                    json.loads(result.extracted_content) if result.extracted_content else {}
                )
            except json.JSONDecodeError as err:
                raise CrawlError("Crawler extracted_content is not valid JSON") from err

            return {
                "markdown": markdown,
                "screenshot": result.screenshot,
                "structured_elements": structured_elements,
            }
    except asyncio.TimeoutError as err:
        raise CrawlError("Crawl timed out after 90 seconds") from err
async def get_data_url(url: str):
    data = await capture_conversion_context(url)
    if data:
        print("--------------MARKDOWN------------------")
        print(data['markdown'])
        print("--------------STRUCTURED ELEMENTS------------------")
        print(data['structured_elements'])
        print("--------------SCREENSHOT------------------")
        print(data['screenshot'])
        print("--------------------------------")
    else:
        print("No data found")

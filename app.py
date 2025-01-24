import os
import asyncio
import aiofiles
from base64 import b64decode
from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig, BrowserConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import LLMContentFilter
import json
from playwright.async_api import Page, BrowserContext


url = "https://erp.vmo.dev/"

openai_api = os.environ['openai_api']
erp_username = os.environ['erp_username']
erp_password = os.environ['erp_password']


async def erp_crawler():
    async def on_browser_created(browser, **kwargs):
        # Called once the browser instance is created (but no pages or contexts yet)
        print("[HOOK] on_browser_created - Browser created successfully!")
        # Typically, do minimal setup here if needed
        return browser

    async def on_page_context_created(page: Page, context: BrowserContext, **kwargs):
        # Called right after a new page + context are created (ideal for auth or route config).
        print("[HOOK] on_page_context_created - Setting up page & context.")

        await page.goto("https://erp.vmo.dev/web/login")

        await page.fill('input[placeholder="Email"]', erp_username)

        # Fill the password field
        # Replace with the actual password
        await page.fill('input[placeholder="Password"]', erp_password)

        # Click the login button
        await page.click('button.btn-primary.btn-block')

        await page.click('li.nav-item:has-text("Chấm công")')

        # Wait for the specific <td> element with the text "Nguyễn Đức Thái - 3381"
        await page.wait_for_selector('td.o_data_cell.o_field_cell.o_list_many2one.o_readonly_modifier.o_required_modifier:has-text("Nguyễn Đức Thái - 3381")', timeout=10000)

        print("Found the text 'Nguyễn Đức Thái - 3381' inside the <td> element.")

        # Wait for navigation or any other action (optional)
        # Wait for 3 seconds to observe the result for Debugging
        # await page.wait_for_timeout(5000)

        # Close the browser
        # context.close()
        return page

    async def before_return_html(
        page: Page, context: BrowserContext, html: str, **kwargs
    ):
        # Called just before returning the HTML in the result.
        print(f"[HOOK] before_return_html - HTML length: {len(html)}")

        async with aiofiles.open('output.html', mode='w') as file:
            # Write the string to the file
            await file.write(html)

        return page

    browser_config = BrowserConfig(
        headless=False,
        verbose=True
    )

    # Initialize LLM filter with specific instruction
    llm_filter = LLMContentFilter(
        provider="openai/gpt-4o-mini",  # or your preferred provider
        api_token=openai_api,  # or use environment variable
        instruction="""
        Extract table with columns 'Date', 'Nhân viên', 'Khối', 'Giờ vào', ... and so on
        """,
        chunk_token_threshold=4096,  # Adjust based on your needs
        verbose=True,
    )

    # 2) Configure the crawler run
    crawler_run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        content_filter=llm_filter
    )

    crawler = AsyncWebCrawler(config=browser_config)
    crawler.crawler_strategy.set_hook('on_browser_created', on_browser_created)
    crawler.crawler_strategy.set_hook(
        "on_page_context_created", on_page_context_created
    )
    crawler.crawler_strategy.set_hook(
        "before_return_html", before_return_html
    )
    await crawler.start()

    result = await crawler.arun(url, config=crawler_run_config)
    print(result.html)
    print(result.fit_markdown)

    await crawler.close()


if __name__ == "__main__":
    asyncio.run(erp_crawler())

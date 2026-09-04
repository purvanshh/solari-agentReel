"""Minimal AgentReel demo agent.

Requires SOLARI_API_KEY. Run with:

    agentreel run examples/agentreel-demo/main.py --no-git
"""

from __future__ import annotations

import asyncio

from agentreel import recorded_session


async def main() -> None:
    async with recorded_session() as browser:
        page = await browser.new_page()
        await page.goto("https://example.com")
        title = await page.title()
        h1 = await page.locator("h1").inner_text()
        print(f"title: {title}")
        print(f"h1: {h1}")
        print(f"session: {browser.id}")


if __name__ == "__main__":
    asyncio.run(main())

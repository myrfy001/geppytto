import asyncio
from pyppeteer import connect
import logging


async def main():
    browser = await connect({'browserWSEndpoint': 'ws://127.0.0.1:9990/devtools/browser/a2dceffb-8f80-4fdd-bef7-149aa9da9fd6'}, logLevel=logging.DEBUG)
    # browser = await connect({'browserWSEndpoint': 'ws://127.0.0.1:9990/devtools/browser/a2dceffb-8f80-4fdd-bef7-149aa9da9fd6?browser_name=123'}, logLevel=logging.DEBUG)
    # await asyncio.sleep(10000000)

    for x in range(10):
        await asyncio.sleep(5)
        page = await browser.newPage()
        await page.goto('http://example.com')
        await page.close()

    # await page.screenshot({'path': 'example.png'})
    await browser.close()
    # await asyncio.sleep(100000)

asyncio.get_event_loop().run_until_complete(main())

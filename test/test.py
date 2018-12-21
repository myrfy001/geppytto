import asyncio
from pyppeteer import connect
import logging
import uuid
import traceback
import time


async def main(name):

    # browser = await connect({'browserWSEndpoint': 'ws://127.0.0.1:9990/devtools/browser/a2dceffb-8f80-4fdd-bef7-149aa9da9fd6?browser_name=123'}, logLevel=logging.DEBUG)
    # await asyncio.sleep(10000000)

    for x in range(100):
        try:
            print(name, '='*10)
            browser = await connect({'browserWSEndpoint': 'ws://10.60.81.138:9990/devtools/browser/a2dceffb-8f80-4fdd-bef7-149aa9da9fd6'}, logLevel=logging.INFO)
            # browser = await connect({'browserWSEndpoint': 'ws://127.0.0.1:9990/devtools/browser/a2dceffb-8f80-4fdd-bef7-149aa9da9fd6'}, logLevel=logging.INFO)
            page = await browser.newPage()
            await page.goto('http://taobao.com', timeout=30000)
            await page.screenshot({'path': 'example.png'})
            await page.close()
            await browser.disconnect()
            # await asyncio.sleep(5)
            print(name, '*'*10)
        except Exception:
            traceback.print_exc()
        finally:
            try:
                # await browser.disconnect()
                pass
            except:
                traceback.print_exc()

    # await page.screenshot({'path': 'example.png'})
    await browser.disconnect()
    # await asyncio.sleep(100000)


async def main1():
    # while 1:
    try:
        browser = await connect({'browserWSEndpoint': f'ws://127.0.0.1:9990/devtools/browser/{str(uuid.uuid4())}?browser_name=br1'}, logLevel=logging.DEBUG)
        page = await browser.newPage()
        await page.goto('http://example.com')
        await page.close()
        await browser.disconnect()
        # await asyncio.sleep(1)
        del browser
    except Exception:
        traceback.print_exc()


st = time.time()
asyncio.get_event_loop().run_until_complete(asyncio.gather(
    main('co1'), main('co2'), main('co3'), main('co4')
))
print(time.time() - st)

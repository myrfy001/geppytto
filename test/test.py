import asyncio
from pyppeteer import connect
import logging
import uuid
import traceback
import time


async def main(name):

    # browser = await connect({'browserWSEndpoint': 'ws://127.0.0.1:9990/devtools/browser/a2dceffb-8f80-4fdd-bef7-149aa9da9fd6?browser_name=123'}, logLevel=logging.DEBUG)
    # await asyncio.sleep(10000000)

    async def do_one_req():
        try:
            print(name, '='*10)
            # browser = await connect({'browserWSEndpoint': f'ws://10.60.81.138:9990/devtools/browser/{str(uuid.uuid4())}'}, logLevel=logging.DEBUG)
            browser = await connect({'browserWSEndpoint': f'ws://127.0.0.1:9990/api/proxy/devtools/browser/{str(uuid.uuid4())}?access_token=qazwsxedc&headless=False'}, logLevel=logging.DEBUG)
            page = await browser.newPage()
            await page.goto('http://taobao.com', timeout=10000)
            await page.screenshot({'path': 'example.png'})
            await page.close()
            await browser.disconnect()
            # await asyncio.sleep(5)
            print(name, '*'*10)
        except Exception:
            traceback.print_exc()
        finally:
            try:
                await browser.disconnect()
                print('######### Successfully disconnect #######')
            except:
                traceback.print_exc()

    for x in range(1000000000):
        try:
            u = str(uuid.uuid4())
            print(u)
            await asyncio.wait_for(do_one_req(), 12)
            print(u)
        except Exception:
            print(u)
            traceback.print_exc()
            print(u)
        await asyncio.sleep(2)
    # await page.screenshot({'path': 'example.png'})
    # await browser.disconnect()
    # await asyncio.sleep(100000)


async def main1():
    # while 1:
    try:
        browser = await connect({'browserWSEndpoint': f'ws://10.60.81.138:9990/devtools/browser/{str(uuid.uuid4())}'}, logLevel=logging.DEBUG)
        page = await browser.newPage()
        await page.goto('http://taobao.com')
        await page.screenshot({'path': 'example.png'})
        await page.close()
        await browser.disconnect()
        # await asyncio.sleep(1)
        del browser
    except Exception:
        traceback.print_exc()


st = time.time()
asyncio.get_event_loop().run_until_complete(asyncio.gather(
    main('co1')
))
# asyncio.get_event_loop().run_until_complete(asyncio.gather(
#     main('co1'), main('co2'), main('co3'), main('co4')
# ))
# asyncio.get_event_loop().run_until_complete(asyncio.gather(
#     main1()
# ))
print(time.time() - st)

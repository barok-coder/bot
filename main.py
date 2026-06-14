import os
from aiohttp import web

# This creates a dummy web server that just keeps the port open for Render
async def handle(request):
    return web.Response(text="Bot is running!")

app = web.Application()
app.add_routes([web.get('/', handle)])

# Start this dummy web server in the background
import asyncio
import threading

def start_web_server():
    runner = web.AppRunner(app)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, '0.0.0.0', os.environ.get("PORT", 8080))
    loop.run_until_complete(site.start())
    loop.run_forever()

threading.Thread(target=start_web_server, daemon=True).start()

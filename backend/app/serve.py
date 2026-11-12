import argparse
import asyncio
import logging
import os

import uvicorn

from .main import app
from .runtime import BrowserTabs


class BrowserServer(uvicorn.Server):
    def __init__(self, config: uvicorn.Config, tabs: BrowserTabs):
        super().__init__(config)
        self.tabs = tabs

    async def on_tick(self, counter: int) -> bool:
        if await super().on_tick(counter):
            return True
        if counter % 10 == 0 and self.tabs.should_stop():
            logging.getLogger('uvicorn.error').info('No CodeTop browser tabs remain. Stopping service.')
            return True
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--close-with-browser', action='store_true')
    args = parser.parse_args()
    config = uvicorn.Config(app, host='127.0.0.1', port=args.port, access_log=False, ws='websockets-sansio')
    if args.close_with_browser:
        tabs = BrowserTabs()
        app.state.browser_tabs = tabs
        server = BrowserServer(config, tabs)
    else:
        server = uvicorn.Server(config)
    if os.name == 'nt':
        # The proactor can leave a transport open after Chromium resets its socket.
        asyncio.run(server.serve(), loop_factory=asyncio.SelectorEventLoop)
    else:
        server.run()


if __name__ == '__main__':
    main()

"""Explicit developer/CI environment preparation; never installs Apple system tools."""
import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.runner.toolchains.registry import ToolchainRegistry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--languages', default='python,c,cpp,java,javascript')
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--require-ready', action='store_true')
    args = parser.parse_args()
    registry = ToolchainRegistry(args.root)
    failed = False
    try:
        for language in args.languages.split(','):
            state = registry.prepare(language)
            previous = None
            while True:
                state = registry.capability(language)
                if state['state'] != previous:
                    print(json.dumps(state, ensure_ascii=False), flush=True)
                    previous = state['state']
                if state['state'] not in ('downloading', 'verifying', 'extracting'): break
                time.sleep(.25)
            failed |= not state['available']
    finally:
        registry.close()
    return int(failed and args.require_ready)


if __name__ == '__main__':
    raise SystemExit(main())

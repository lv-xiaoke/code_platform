"""Build in a fresh directory, then atomically switch the active frontend."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4


def build_frontend(root, node, *, run=subprocess.run):
    root = Path(root).resolve()
    name = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid4().hex[:8]
    relative = 'releases/' + name
    output = root / relative
    output.mkdir(parents=True)
    frontend = root / 'frontend'
    run([str(node), 'node_modules/typescript/bin/tsc', '-b'], cwd=frontend, check=True)
    run([str(node), 'node_modules/vite/bin/vite.js', 'build', '--outDir', str(output), '--emptyOutDir', 'false'],
        cwd=frontend, check=True)
    if not (output / 'index.html').is_file():
        raise ValueError('Built index.html missing; current release retained')
    import ast
    version_module = ast.parse((root / 'backend/app/__init__.py').read_text(encoding='utf-8-sig'))
    version = next(ast.literal_eval(stmt.value) for stmt in version_module.body
                   if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '__version__' for t in stmt.targets))
    value = {'path': relative, 'built_at': datetime.now(timezone.utc).isoformat(), 'version': version}
    pending = root / 'releases' / ('current-' + name + '.json')
    pending.write_text(json.dumps(value), encoding='utf-8')
    current = root / 'releases/current.json'
    if current.exists():
        shutil.copy2(current, root / 'releases' / ('previous-' + name + '.json'))
    pending.replace(current)
    print('Release ready:', output)
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--node', required=True)
    args = parser.parse_args()
    build_frontend(Path(__file__).resolve().parents[1], args.node)


if __name__ == '__main__':
    main()

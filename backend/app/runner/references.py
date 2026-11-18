import json
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select

from .. import models as m

from ..paths import application_root
PACK_ROOT=application_root()/'backend'/'reference_pack'
GENERIC_TEMPLATE='''import sys


def solve():
    # 按自定义输入格式读取，并使用 print 输出答案。
    data = sys.stdin.read()
    # 在这里实现你的算法。


if __name__ == "__main__":
    solve()
'''


@lru_cache(maxsize=1)
def load_pack():
    manifest=json.loads((PACK_ROOT/'manifest.json').read_text(encoding='utf-8'))
    entries={}
    for entry in manifest['problems']:
        path=(PACK_ROOT/entry['file']).resolve()
        if path.parent!=PACK_ROOT.resolve(): raise ValueError('参考程序路径无效')
        entries[entry['source_record_id']]={**entry,'source_code':path.read_text(encoding='utf-8')}
    return entries


def reference_for(conn,pid):
    key=conn.execute(select(m.keys.c.source_record_id).where(m.keys.c.problem_id==pid,m.keys.c.source_name=='algotop')).scalar()
    return load_pack().get(key)

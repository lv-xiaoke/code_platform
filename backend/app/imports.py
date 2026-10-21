"""Validate immutable snapshots before applying a single atomic catalog update."""
import csv
import hashlib
import io
import json
import math
import re
from uuid import uuid4
from urllib.parse import urlsplit

from fastapi import HTTPException
from sqlalchemy import select, insert, update

from . import models as m

UPSTREAM_COMMIT = '64d624feee3fbec0dc67dd58f0cf8874ecdc6e1b'
PLURALS = {'companies': 'company', 'departments': 'department', 'jobs': 'job', 'tags': 'tag'}


def safe_url(value):
    if not value:
        return None
    parts = urlsplit(value)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise ValueError('题目 URL 必须使用 http/https 且不能包含登录凭据')
    return value


def canonical(platform, display_id, expanded=False):
    if platform == 'leetcode' and re.fullmatch(r'[1-9][0-9]*', display_id) and not expanded:
        return ('leetcode', str(int(display_id)))
    return (None, None)


def parse(raw, kind):
    if kind == 'legacy':
        data = json.loads(raw.decode('utf-8-sig'))
        if not isinstance(data, dict): raise ValueError('旧版导出应为 JSON 对象')
        data['progress'] = data.get('progress', data.get('userProgress', {}))
        if not isinstance(data.get('notes', {}), dict) or not isinstance(data['progress'], dict):
            raise ValueError('旧版 notes/progress 应为对象')
        for value in data.get('notes', {}).values():
            if not isinstance(value, dict) or not isinstance(value.get('content'), str): raise ValueError('旧版笔记格式错误')
        for value in data['progress'].values():
            if not isinstance(value, dict) or value.get('mastery', 0) not in (0, 1, 2, 3): raise ValueError('旧版掌握程度错误')
        return data
    if kind == 'manual':
        text = raw.decode('utf-8-sig')
        rows = json.loads(text) if text.lstrip().startswith(('[', '{')) else list(csv.DictReader(io.StringIO(text)))
        if isinstance(rows, dict): rows = rows.get('questions')
        if not isinstance(rows, list) or not rows: raise ValueError('手工导入需要非空的题目列表或 CSV')
        data = {'generatedAt': None, 'questions': {}, 'taxonomies': {k: [] for k in PLURALS},
                'indexes': {'overall': [], **{k: {} for k in PLURALS}}, 'manual': True}
        for n, row in enumerate(rows):
            display = str(row.get('display_id', '')).strip()
            title = str(row.get('title', '')).strip()
            difficulty = {'easy': 1, 'medium': 2, 'hard': 3, '简单': 1, '中等': 2, '困难': 3, '1': 1, '2': 2, '3': 3}.get(str(row.get('difficulty', '')).lower())
            if not display or not title or not difficulty: raise ValueError(f'第 {n+1} 行题号、标题或难度无效')
            platform = row.get('platform', 'manual')
            rid = str(row.get('source_record_id') or f'{platform}:{display}')
            if rid in data['questions']: raise ValueError('手工题号重复，请提供独立 source_record_id')
            url = safe_url(row.get('url'))
            if platform == 'leetcode' and url and urlsplit(url).hostname not in ('leetcode.cn', 'leetcode.com', 'www.leetcode.com'):
                raise ValueError('leetcode 平台题目 URL 与平台不符')
            data['questions'][rid] = {'id': rid, 'displayId': display, 'title': title, 'level': difficulty,
                                     'content': row.get('content_html'), 'url': url, 'platform': platform,
                                     'slug': '', 'expandedLink': False}
            freq = row.get('frequency')
            data['indexes']['overall'].append({'questionId': rid, 'frequency': float(freq) if freq not in (None, '') else None})
            for typ, names in [('tag', str(row.get('tags', '')).split('|')), ('collection', str(row.get('collection', '')).split('|'))]:
                plural = 'tags' if typ == 'tag' else 'collections'
                data['taxonomies'].setdefault(plural, [])
                data['indexes'].setdefault(plural, {})
                for name in filter(None, (v.strip() for v in names)):
                    if name not in data['indexes'][plural]:
                        data['taxonomies'][plural].append({'id': name, 'name': name})
                        data['indexes'][plural][name] = []
                    data['indexes'][plural][name].append({'questionId': rid, 'frequency': None})
        return validate(data)
    if kind != 'algotop': raise ValueError('不支持的导入格式')
    return validate(json.loads(raw.decode('utf-8-sig')))


def validate(data):
    if not isinstance(data, dict) or not isinstance(data.get('questions'), dict) or not data['questions']:
        raise ValueError('questions 必须为非空对象')
    from datetime import datetime
    if data.get('generatedAt'): datetime.fromisoformat(data['generatedAt'].replace('Z', '+00:00'))
    seen_canonical = set()
    for rid, q in data['questions'].items():
        if str(q.get('id')) != rid: raise ValueError(f'来源内部编号不匹配: {rid}')
        if type(q.get('level')) is not int or q['level'] not in (1, 2, 3): raise ValueError(f'难度无效: {rid}')
        if not isinstance(q.get('title'), str) or not q['title'].strip() or not str(q.get('displayId', '')).strip(): raise ValueError('题号或标题缺失')
        if q.get('content') is not None and not isinstance(q['content'], str): raise ValueError('题面必须是字符串')
        slug = q.get('slug') or ''
        if not isinstance(slug, str): raise ValueError('slug 必须是字符串')
        if q.get('expandedLink'):
            safe_url(slug)
        elif slug and not re.fullmatch(r'[A-Za-z0-9_-]+', slug):
            raise ValueError('常规题 slug 包含无效字符')
        safe_url(q.get('url'))
        ck = canonical(q.get('platform', 'leetcode'), str(q['displayId']), bool(q.get('expandedLink')))
        if ck[0]:
            if ck in seen_canonical: raise ValueError('同一快照含重复常规题号')
            seen_canonical.add(ck)
    tax = data.get('taxonomies', {})
    indexes = data.get('indexes', {})
    for plural, typ in {**PLURALS, 'collections': 'collection'}.items():
        dictionary = tax.get(plural, [])
        if not isinstance(dictionary, list): raise ValueError('分类必须为数组')
        ids = [str(x['id']) for x in dictionary]
        if len(set(ids)) != len(ids): raise ValueError('分类编号重复')
        if plural == 'departments':
            companies = {str(x['id']) for x in tax.get('companies', [])}
            data['_unknown_companies'] = sorted({str(x.get('company')) for x in dictionary if str(x.get('company')) not in companies})
            if 'None' in data['_unknown_companies']: raise ValueError('部门缺少所属公司编号')
        for key in indexes.get(plural, {}):
            if key not in ids: raise ValueError(f'统计引用不存在的分类: {plural}/{key}')
    scopes = [('overall', 'all', indexes.get('overall', []))]
    for plural in (*PLURALS, 'collections'):
        scopes.extend((plural, key, rows) for key, rows in indexes.get(plural, {}).items())
    for typ, key, rows in scopes:
        seen = set()
        for row in rows:
            rid = str(row['questionId'])
            if rid not in data['questions']: raise ValueError(f'索引引用不存在的题目: {rid}')
            if rid in seen: raise ValueError('同一统计范围内题目重复')
            seen.add(rid)
            freq = row.get('frequency')
            if freq is not None and (isinstance(freq, bool) or not isinstance(freq, (int, float)) or not math.isfinite(freq) or freq < 0): raise ValueError('频次必须为非负有限数字或空值')
            if row.get('time'): datetime.fromisoformat(row['time'].replace('Z', '+00:00'))
    return data


def preview_import(db, raw, kind, source_name, now):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', source_name): raise ValueError('来源名称只允许英文字母、数字、下划线和连字符')
    data = parse(raw, kind)
    digest = hashlib.sha256(raw).hexdigest()
    path = db.data_dir / 'sources' / digest
    if not path.exists(): path.write_bytes(raw)
    pid = str(uuid4())
    summary = {'questions': len(data.get('questions', {})), 'generated_at': data.get('generatedAt'),
               'notes': len(data.get('notes', {})), 'missing_content': 0, 'missing_url': 0,
               'new': 0, 'changed': 0, 'unmatched': [], 'ambiguous': [], 'scopes': {},
               'warnings': [f'公司 {key} 被部门引用，但来源未提供公司名称；保留原始关联编号。' for key in data.get('_unknown_companies', [])]}
    with db.write() as conn:
        existing = conn.execute(select(m.datasets).where(m.datasets.c.source_name == source_name, m.datasets.c.sha256 == digest)).mappings().first()
        if existing: summary['existing_dataset_id'] = existing['id']
        if kind == 'legacy':
            for rid in set(data.get('notes', {})) | set(data.get('progress', {})):
                if not conn.execute(select(m.keys.c.problem_id).where(m.keys.c.source_name == source_name, m.keys.c.source_record_id == rid)).first(): summary['unmatched'].append(rid)
        else:
            old = conn.execute(select(m.datasets.c.id).where(m.datasets.c.source_name == source_name, m.datasets.c.status == 'active')).scalar()
            for rid, q in data['questions'].items():
                mapped = conn.execute(select(m.keys.c.problem_id).where(m.keys.c.source_name == source_name, m.keys.c.source_record_id == rid)).scalar()
                if not mapped: summary['new'] += 1
                elif old:
                    entry = conn.execute(select(m.entries).where(m.entries.c.dataset_id == old, m.entries.c.problem_id == mapped)).mappings().first()
                    if entry and any(entry[k] != q.get(v) for k,v in [('title','title'), ('difficulty','level'), ('content_html','content')]): summary['changed'] += 1
                summary['missing_content'] += not bool(q.get('content'))
                summary['missing_url'] += not bool(q.get('slug') or q.get('url'))
                if not mapped and not canonical(q.get('platform', 'leetcode'), str(q['displayId']), bool(q.get('expandedLink')))[0]:
                    candidates = conn.execute(select(m.entries.c.problem_id, m.entries.c.title).where(m.entries.c.title == q['title']).distinct()).mappings().all()
                    if candidates: summary['ambiguous'].append({'source_record_id': rid, 'title': q['title'], 'candidates': [dict(x) for x in candidates]})
            for k, v in data['indexes'].items(): summary['scopes'][k] = len(v) if isinstance(v, list) else sum(len(rows) for rows in v.values())
        conn.execute(insert(m.previews).values(id=pid, source_name=source_name, sha256=digest, kind=kind, summary_json=json.dumps(summary, ensure_ascii=False), created_at=now.isoformat()))
    return {'id': pid, 'sha256': digest, 'kind': kind, 'source_name': source_name, **summary}


def dataset_dict(row):
    return {**dict(row), 'summary': json.loads(row['summary_json'])}


def activate(db, dataset_id):
    from .backups import create_backup
    create_backup(db, reason='before-activate')
    with db.write() as conn:
        row = conn.execute(select(m.datasets).where(m.datasets.c.id == dataset_id)).mappings().first()
        if not row: raise HTTPException(404, '来源版本不存在')
        conn.execute(update(m.datasets).where(m.datasets.c.source_name == row['source_name']).values(status='inactive'))
        conn.execute(update(m.datasets).where(m.datasets.c.id == dataset_id).values(status='active'))
    return {'id': dataset_id, 'status': 'active'}


def apply_import(db, preview_id, now, links=None):
    from .backups import create_backup
    from .learning import migrate_legacy
    with db.engine.connect() as conn:
        row = conn.execute(select(m.previews).where(m.previews.c.id == preview_id)).mappings().first()
    if not row: raise HTTPException(404, '导入预览不存在')
    raw = (db.data_dir / 'sources' / row['sha256']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != row['sha256']: raise ValueError('来源文件哈希校验失败')
    data = parse(raw, row['kind'])
    create_backup(db, reason='before-import')
    with db.write() as conn:
        if row['kind'] == 'legacy': return migrate_legacy(conn, data, row, now)
        existing = conn.execute(select(m.datasets).where(m.datasets.c.source_name == row['source_name'], m.datasets.c.sha256 == row['sha256'])).mappings().first()
        if existing: return dataset_dict(existing)
        did = str(uuid4())
        values = dict(id=did, source_name=row['source_name'], sha256=row['sha256'], generated_at=data.get('generatedAt'), imported_at=now.isoformat(), source_url='https://github.com/dogxii/algoTop' if row['kind']=='algotop' else None, source_commit=UPSTREAM_COMMIT if row['source_name']=='algotop' and row['sha256'].lower()=='bc496564c4939eae1173636dec05b358b0a46b0b6dd1797d3ff10416dbc81ac9' else None, status='inactive', summary_json=row['summary_json'])
        conn.execute(insert(m.datasets).values(**values))
        mapped = {}
        for rid, q in data['questions'].items():
            pid = conn.execute(select(m.keys.c.problem_id).where(m.keys.c.source_name == row['source_name'], m.keys.c.source_record_id == rid)).scalar()
            ck = canonical(q.get('platform', 'leetcode'), str(q['displayId']), bool(q.get('expandedLink')))
            if not pid and ck[0]: pid = conn.execute(select(m.problems.c.id).where(m.problems.c.canonical_platform == ck[0], m.problems.c.canonical_key == ck[1])).scalar()
            if not pid and links and rid in links:
                pid = conn.execute(select(m.problems.c.id).where(m.problems.c.id == links[rid])).scalar()
                if not pid: raise ValueError('所选关联题目不存在')
            if not pid:
                pid = str(uuid4())
                conn.execute(insert(m.problems).values(id=pid, canonical_platform=ck[0], canonical_key=ck[1], kind='standard' if ck[0] else 'supplemental', created_at=now.isoformat()))
            if not conn.execute(select(m.keys).where(m.keys.c.source_name == row['source_name'], m.keys.c.source_record_id == rid)).first():
                conn.execute(insert(m.keys).values(source_name=row['source_name'], source_record_id=rid, problem_id=pid, upstream_question_id=str(q['questionId']) if q.get('questionId') is not None else None))
            if pid in mapped.values(): raise ValueError('同一版本中多个来源题目映射到同一题，请保留独立身份')
            mapped[rid] = pid
            slug = q.get('slug') or None
            url = q.get('url') or (slug if q.get('expandedLink') else f'https://leetcode.cn/problems/{slug}/' if slug else None)
            conn.execute(insert(m.entries).values(dataset_id=did, problem_id=pid, display_id=str(q['displayId']), title=q['title'], difficulty=q['level'], content_html=q.get('content') or None, slug=slug, expanded_link=bool(q.get('expandedLink')), url=safe_url(url)))
        taxrows = [dict(dataset_id=did, type='overall', source_key='all', name='全部题目', parent_company_key=None)]
        for plural, typ in {**PLURALS, 'collections':'collection'}.items():
            taxrows.extend(dict(dataset_id=did, type=typ, source_key=str(t['id']), name=t['name'], parent_company_key=str(t['company']) if plural=='departments' else None) for t in data['taxonomies'].get(plural, []))
        taxrows.extend(dict(dataset_id=did, type='company', source_key=key, name=f'来源未提供公司（{key}）', parent_company_key=None, is_internal=1) for key in data.get('_unknown_companies', []))
        for item in taxrows: item.setdefault('is_internal', 1 if item['type']=='overall' else 0)
        conn.execute(insert(m.taxonomies), taxrows)
        statrows = []
        for plural, v in data['indexes'].items():
            typ = {**PLURALS, 'collections':'collection', 'overall':'overall'}[plural]
            for key, rows in ({'all':v} if plural=='overall' else v).items():
                statrows.extend(dict(dataset_id=did, problem_id=mapped[str(s['questionId'])], scope_type=typ, scope_key=key, window_key='cumulative', frequency_value=s.get('frequency'), frequency_kind='source_score' if data.get('manual') else 'count', last_seen=s.get('time'), comment_count=s.get('commentCount')) for s in rows)
        if statrows: conn.execute(insert(m.stats), statrows)
        if conn.exec_driver_sql('PRAGMA foreign_key_check').first(): raise ValueError('导入外键检查失败')
        conn.execute(update(m.datasets).where(m.datasets.c.source_name == row['source_name']).values(status='inactive'))
        conn.execute(update(m.datasets).where(m.datasets.c.id == did).values(status='active'))
        values['status'] = 'active'
    return dataset_dict(values)

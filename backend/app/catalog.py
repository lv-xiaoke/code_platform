import re
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select, func

from . import models as m
from .imports import dataset_dict
from .learning import get_state, get_note, get_completion, completion_overrides
from .scheduler import TZ


def choose_dataset(conn, source=None, dataset_id=None):
    query = select(m.datasets)
    if dataset_id: query = query.where(m.datasets.c.id == dataset_id)
    else:
        query = query.where(m.datasets.c.status == 'active')
        if source: query = query.where(m.datasets.c.source_name == source)
        else: query = query.order_by((m.datasets.c.source_name != 'algotop'), m.datasets.c.source_name)
    return conn.execute(query).mappings().first()


def list_datasets(db):
    with db.engine.connect() as conn:
        return [dataset_dict(r) for r in conn.execute(select(m.datasets).order_by(m.datasets.c.imported_at.desc())).mappings()]


def get_taxonomies(db, source=None, dataset_id=None):
    with db.engine.connect() as conn:
        ds = choose_dataset(conn, source, dataset_id)
        if not ds: return {'items': [], 'dataset': None}
        items = [dict(r) for r in conn.execute(select(m.taxonomies).where(m.taxonomies.c.dataset_id == ds['id'], m.taxonomies.c.type != 'overall').order_by(m.taxonomies.c.name)).mappings()]
        return {'items':items, 'dataset':dataset_dict(ds)}


def list_problems(db, now, *, source=None, dataset_id=None, page=1, page_size=20, search='', company='', department='', job='', tag='', collection='', difficulty=None, completion='', mastery=None, favorite=False, recent_days=None, history=False, due=False, ordering='-frequency'):
    scope_type, scope_key = ('department', department) if department else ('company', company) if company else ('job', job) if job else ('overall', 'all')
    label = {'overall':'全部题目', 'company':'公司', 'department':'部门', 'job':'岗位'}[scope_type]
    if job and scope_type in ('company', 'department'): label += '题单与岗位题单的交集，频次按' + ('公司' if scope_type=='company' else '部门') + '统计'
    with db.engine.connect() as conn:
        ds = choose_dataset(conn, source, dataset_id)
        meta = {'ranking_scope':scope_type, 'window_key':'cumulative', 'frequency_kind':'count', 'source_generated_at':ds['generated_at'] if ds else None, 'scope_label':label, 'dataset_id':ds['id'] if ds else None}
        if not ds: return {'items':[], 'count':0, **meta}
        ranking = {r['problem_id']:dict(r) for r in conn.execute(select(m.stats).where(m.stats.c.dataset_id == ds['id'], m.stats.c.scope_type == scope_type, m.stats.c.scope_key == scope_key)).mappings()}
        if ranking: meta['frequency_kind'] = next(iter(ranking.values()))['frequency_kind']
        filters = [('company',company), ('department',department), ('job',job), ('tag',tag), ('collection',collection)]
        members = []
        for typ, key in filters:
            if key: members.append(set(conn.execute(select(m.stats.c.problem_id).where(m.stats.c.dataset_id == ds['id'], m.stats.c.scope_type == typ, m.stats.c.scope_key == key)).scalars()))
        states = {r['problem_id']:dict(r) for r in conn.execute(select(m.state)).mappings()}
        practiced = set(conn.execute(select(m.logs.c.problem_id).distinct()).scalars())
        overrides=completion_overrides(conn)
        completed=(practiced-{pid for pid,done in overrides.items() if not done})|{pid for pid,done in overrides.items() if done}
        notepids = set(conn.execute(select(m.notes.c.problem_id)).scalars())
        if history or due:
            # Latest entry per stable UUID, retaining questions absent from active snapshots.
            rows = conn.execute(select(m.entries).join(m.datasets).order_by((m.datasets.c.status=='active').desc(), m.datasets.c.imported_at.desc())).mappings().all()
            unique = {}
            for row in rows: unique.setdefault(row['problem_id'], dict(row))
            rows = list(unique.values())
        else:
            rows = conn.execute(select(m.entries).where(m.entries.c.dataset_id == ds['id'])).mappings().all()
        result = []
        today = now.astimezone(TZ).date().isoformat()
        company_departments = {r.source_key for r in conn.execute(select(m.taxonomies.c.source_key).where(m.taxonomies.c.dataset_id==ds['id'], m.taxonomies.c.type=='department', m.taxonomies.c.parent_company_key==company))} if company and department else None
        for entry in rows:
            pid = entry['problem_id']
            state = states.get(pid, {})
            if company_departments is not None and department not in company_departments: continue
            if any(pid not in s for s in members): continue
            if not (history or due) and pid not in ranking: continue
            if search and search.casefold() not in (entry['display_id']+' '+entry['title']).casefold(): continue
            if difficulty is not None and entry['difficulty'] != difficulty: continue
            if completion=='done' and pid not in completed or completion=='todo' and pid in completed: continue
            if mastery is not None and state.get('mastery',0) != mastery: continue
            if favorite and not state.get('favorite'): continue
            if due and not (state.get('review_enabled') and state.get('next_review_date') and state['next_review_date'] <= today): continue
            st = ranking.get(pid, {})
            last_seen = st.get('last_seen')
            if recent_days and (not last_seen or datetime.fromisoformat(last_seen.replace('Z','+00:00')).astimezone(TZ).date() < now.astimezone(TZ).date()-timedelta(days=recent_days)): continue
            result.append({**dict(entry), 'id':pid, 'frequency':st.get('frequency_value'), 'last_seen':last_seen, 'mastery':state.get('mastery',0), 'favorite':bool(state.get('favorite')), 'done':pid in completed, 'state_revision':state.get('revision',0), 'has_note':pid in notepids, 'next_review_date':state.get('next_review_date'), 'review_enabled':bool(state.get('review_enabled'))})
    def displaykey(row):
        value = row['display_id']
        return (0, int(value), row['id']) if value.isdigit() else (1, value, row['id'])
    result.sort(key=displaykey)
    if ordering in ('-frequency','frequency'):
        result.sort(key=lambda r: (r['frequency'] is None, -(r['frequency'] or 0) if ordering=='-frequency' else (r['frequency'] or 0)))
    elif ordering in ('-time','time'): result.sort(key=lambda r:r['last_seen'] or '', reverse=ordering=='-time')
    elif ordering=='-display': result.reverse()
    if due: result.sort(key=lambda r:r['next_review_date'] or '')
    return {'items':result[(page-1)*page_size:page*page_size], 'count':len(result), **meta}


def detail(db, pid, dataset_id=None):
    with db.engine.connect() as conn:
        query = select(m.entries, m.datasets.c.source_name, m.datasets.c.generated_at, m.datasets.c.imported_at).join(m.datasets).where(m.entries.c.problem_id == pid)
        if dataset_id: query = query.where(m.entries.c.dataset_id == dataset_id)
        row = conn.execute(query.order_by((m.datasets.c.status=='active').desc(), m.datasets.c.imported_at.desc())).mappings().first()
        if not row: raise HTTPException(404, '题目不存在')
        attempts = [dict(r) for r in conn.execute(select(m.logs).where(m.logs.c.problem_id == pid).order_by(m.logs.c.practiced_at.desc())) .mappings()]
        return {**dict(row), 'id':pid, 'state':get_state(conn,pid), 'done':get_completion(conn,pid), 'note':get_note(conn,pid), 'attempts':attempts}

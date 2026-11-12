import json
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, insert, update, func

from . import models as m
from .scheduler import schedule, TZ


def utc_text(now):
    from datetime import timezone
    return now.astimezone(timezone.utc).isoformat()


def require_problem(conn, pid):
    if not conn.execute(select(m.problems.c.id).where(m.problems.c.id == pid)).first():
        raise HTTPException(404, '题目不存在')


def get_state(conn, pid):
    row = conn.execute(select(m.state).where(m.state.c.problem_id == pid)).mappings().first()
    result = dict(row) if row else dict(problem_id=pid, mastery=0, favorite=False, review_enabled=False, review_step=-1, next_review_date=None, last_advanced_date=None, revision=0, updated_at='')
    result['favorite'] = bool(result['favorite'])
    result['review_enabled'] = bool(result['review_enabled'])
    return result


def get_note(conn, pid):
    row = conn.execute(select(m.notes).where(m.notes.c.problem_id == pid)).mappings().first()
    return dict(row) if row else dict(problem_id=pid, body_md='', code_text='', language='python', revision=0, updated_at='')


def completion_overrides(conn):
    prefix='completion:'
    return {row.key[len(prefix):]:json.loads(row.value_json) for row in conn.execute(
        select(m.settings).where(m.settings.c.key.startswith(prefix)))}


def get_completion(conn,pid):
    override=conn.execute(select(m.settings.c.value_json).where(m.settings.c.key=='completion:'+pid)).scalar()
    if override is not None: return json.loads(override) is True
    return conn.execute(select(m.logs.c.id).where(m.logs.c.problem_id==pid).limit(1)).first() is not None


def set_completion(conn,pid,done):
    key='completion:'+pid
    values={'key':key,'value_json':json.dumps(done)}
    if conn.execute(select(m.settings.c.key).where(m.settings.c.key==key)).first():
        conn.execute(update(m.settings).where(m.settings.c.key==key).values(value_json=values['value_json']))
    else: conn.execute(insert(m.settings).values(**values))


def save_state(conn, state, now):
    exists = conn.execute(select(m.state.c.problem_id).where(m.state.c.problem_id == state['problem_id'])).first()
    result = {**state, 'revision': state['revision']+1, 'updated_at': utc_text(now)}
    if exists: conn.execute(update(m.state).where(m.state.c.problem_id == state['problem_id']).values(**result))
    else: conn.execute(insert(m.state).values(**result))
    return result


def put_note(db, pid, payload, now):
    with db.write() as conn:
        require_problem(conn, pid)
        old = get_note(conn, pid)
        if payload.revision != old['revision']: raise HTTPException(409, {'message':'笔记已在其他页面更新；你的编辑内容仍保留，请导出草稿后重新载入。', 'current':old})
        result = {**old, **payload.model_dump(), 'revision': old['revision']+1, 'updated_at': utc_text(now)}
        if old['revision']: conn.execute(update(m.notes).where(m.notes.c.problem_id == pid).values(**result))
        else: conn.execute(insert(m.notes).values(**result))
    return result


def get_code_history(db, pid):
    with db.engine.connect() as conn:
        require_problem(conn, pid)
        return [dict(row) for row in conn.execute(select(m.code_history).where(
            m.code_history.c.problem_id == pid).order_by(m.code_history.c.id.desc())).mappings()]


def rewrite_code(db, pid, payload, now):
    with db.write() as conn:
        require_problem(conn, pid)
        old = get_note(conn, pid)
        if payload.revision != old['revision']:
            raise HTTPException(409, '代码已在其他页面更新，当前草稿仍保留；请导出后载入服务器版本。')
        target = None
        if payload.history_id is not None:
            target = conn.execute(select(m.code_history).where(
                m.code_history.c.id == payload.history_id,
                m.code_history.c.problem_id == pid)).mappings().first()
            if target is None: raise HTTPException(404, '历史代码不存在')
        if old['code_text'].strip():
            conn.execute(insert(m.code_history).values(problem_id=pid, code_text=old['code_text'],
                language=old['language'], created_at=utc_text(now)))
        result = {**old, 'code_text': target['code_text'] if target else '',
                  'language': target['language'] if target else old['language'],
                  'revision': old['revision'] + 1, 'updated_at': utc_text(now)}
        if old['revision']:
            conn.execute(update(m.notes).where(m.notes.c.problem_id == pid).values(**result))
        else:
            conn.execute(insert(m.notes).values(**result))
    return result


def patch_state(db, pid, payload, now):
    with db.write() as conn:
        require_problem(conn, pid)
        state = get_state(conn, pid)
        if state['revision'] != payload.revision: raise HTTPException(409, '学习状态已更新，请刷新后重试')
        state.update(payload.model_dump(exclude={'revision','done'}, exclude_none=True))
        if payload.done is not None: set_completion(conn,pid,payload.done)
        if payload.review_enabled is not None:
            key = 'review-explicit:' + pid
            if not conn.execute(select(m.settings.c.key).where(m.settings.c.key == key)).first():
                conn.execute(insert(m.settings).values(key=key, value_json='true'))
        return {**save_state(conn, state, now),'done':get_completion(conn,pid)}


def record_attempt(db, pid, payload, now):
    with db.write() as conn:
        require_problem(conn, pid)
        previous = conn.execute(select(m.logs).where(m.logs.c.request_id == payload.request_id)).mappings().first()
        if previous:
            if previous['problem_id'] != pid or previous['outcome'] != payload.outcome or previous['duration_seconds'] != payload.duration_seconds:
                raise HTTPException(409, '请求编号已用于不同的练习记录')
            return {'duplicate': True, 'attempt':dict(previous), 'state':get_state(conn, pid)}
        first = not conn.execute(select(m.logs.c.id).where(m.logs.c.problem_id == pid)).first()
        state = get_state(conn, pid)
        explicitly_set = conn.execute(select(m.settings.c.key).where(m.settings.c.key == 'review-explicit:' + pid)).first()
        if first and not explicitly_set: state['review_enabled'] = True
        result = schedule(state, payload.outcome, now)
        result = save_state(conn, result, now)
        attempt = dict(id=str(uuid4()), problem_id=pid, request_id=payload.request_id, practiced_at=utc_text(now), outcome=payload.outcome, duration_seconds=payload.duration_seconds, scheduler_version='fixed-v1')
        conn.execute(insert(m.logs).values(**attempt))
        # A genuinely new practice re-completes an explicitly unchecked item.
        # Historical/idempotent retries above do not change a manual mark.
        conn.execute(update(m.settings).where(m.settings.c.key=='completion:'+pid).values(value_json='true'))
    return {'duplicate': False, 'attempt':attempt, 'state':result}


def migrate_legacy(conn, data, preview, now):
    count = 0
    unmatched = []
    for rid in set(data.get('notes', {})) | set(data.get('progress', {})):
        pid = conn.execute(select(m.keys.c.problem_id).where(m.keys.c.source_name == preview['source_name'], m.keys.c.source_record_id == rid)).scalar()
        if not pid:
            unmatched.append(rid)
            continue
        note = data.get('notes', {}).get(rid)
        if note:
            old = get_note(conn, pid)
            if old['revision'] and old['body_md'] != note['content']:
                raise HTTPException(409, f'题目 {rid} 已有本地笔记，已取消迁移以保留两份数据')
            if not old['revision']:
                conn.execute(insert(m.notes).values(problem_id=pid, body_md=note['content'], code_text='', language='python', revision=1, updated_at=utc_text(now)))
        progress = data.get('progress', {}).get(rid)
        if progress:
            state = get_state(conn, pid)
            if state['revision'] == 0:
                state['mastery'] = progress.get('mastery', 0)
                save_state(conn, state, now)
            if progress.get('done'):
                request_id = f"legacy:{preview['sha256']}:{rid}"
                if not conn.execute(select(m.logs.c.id).where(m.logs.c.request_id == request_id)).first():
                    conn.execute(insert(m.logs).values(id=str(uuid4()), problem_id=pid, request_id=request_id, practiced_at=utc_text(now), outcome='independent', duration_seconds=None, scheduler_version='legacy-import-no-schedule'))
        count += 1
    return {'migrated':count, 'unmatched':unmatched}


def activity(db, now):
    from collections import Counter
    from datetime import datetime, timedelta
    with db.engine.connect() as conn:
        all_logs = conn.execute(select(m.logs.c.practiced_at, m.logs.c.problem_id)).all()
        note_count = conn.execute(select(func.count()).select_from(m.notes)).scalar()
        mastered = conn.execute(select(func.count()).select_from(m.state).where(m.state.c.mastery >= 2)).scalar()
    days = Counter(datetime.fromisoformat(r.practiced_at).astimezone(TZ).date().isoformat() for r in all_logs)
    today = now.astimezone(TZ).date()
    streak = 0
    day = today if days[today.isoformat()] else today-timedelta(days=1)
    while days[day.isoformat()]:
        streak += 1
        day -= timedelta(days=1)
    return {'attempts':len(all_logs), 'practiced_problems':len({r.problem_id for r in all_logs}), 'notes':note_count, 'mastered':mastered, 'today':days[today.isoformat()], 'streak':streak, 'days':dict(days)}

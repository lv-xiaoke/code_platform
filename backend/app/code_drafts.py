"""Independent code revisions; archive and replace a draft in one transaction."""
import re

from fastapi import HTTPException
from sqlalchemy import select, insert, update

from . import models as m
from .learning import require_problem, utc_text


def check_language(language):
    if not re.fullmatch(r'[a-z0-9_-]{1,32}', language):
        raise HTTPException(422, '语言标识无效')


def draft_in(conn, pid, language):
    row = conn.execute(select(m.code_drafts).where(
        m.code_drafts.c.problem_id == pid, m.code_drafts.c.language == language)).mappings().first()
    return {**dict(row), 'exists': True} if row else dict(problem_id=pid,
        language=language, code_text='', revision=0, created_at='', updated_at='', exists=False)


def preference_in(conn, pid):
    row = conn.execute(select(m.problem_preferences).where(m.problem_preferences.c.problem_id == pid)).mappings().first()
    return dict(row) if row else dict(problem_id=pid, language='python', revision=0, updated_at='')


def require_revision(expected, current):
    if expected != current['revision']:
        raise HTTPException(409, {'message': '内容已在其他页面更新，当前输入仍保留，请导出后重新载入。', 'current': current})


def save_draft_in(conn, old, code, now):
    values = {k: v for k, v in old.items() if k != 'exists'}
    values.update(code_text=code, revision=old['revision'] + 1, updated_at=utc_text(now))
    if old['exists']:
        conn.execute(update(m.code_drafts).where(m.code_drafts.c.problem_id == old['problem_id'],
            m.code_drafts.c.language == old['language']).values(**values))
    else:
        values['created_at'] = values['updated_at']
        conn.execute(insert(m.code_drafts).values(**values))
    return {**values, 'exists': True}


def save_preference_in(conn, old, language, now):
    values = {**old, 'language': language, 'revision': old['revision'] + 1, 'updated_at': utc_text(now)}
    if old['revision']:
        conn.execute(update(m.problem_preferences).where(m.problem_preferences.c.problem_id == old['problem_id']).values(**values))
    else:
        conn.execute(insert(m.problem_preferences).values(**values))
    return values


def get_draft(db, pid, language):
    check_language(language)
    with db.engine.connect() as conn:
        require_problem(conn, pid)
        return draft_in(conn, pid, language)


def put_draft(db, pid, language, payload, now):
    check_language(language)
    with db.write() as conn:
        require_problem(conn, pid)
        old = draft_in(conn, pid, language)
        require_revision(payload.revision, old)
        return save_draft_in(conn, old, payload.code_text, now)


def get_preference(db, pid):
    with db.engine.connect() as conn:
        require_problem(conn, pid)
        return preference_in(conn, pid)


def put_preference(db, pid, payload, now):
    check_language(payload.language)
    with db.write() as conn:
        require_problem(conn, pid)
        old = preference_in(conn, pid)
        require_revision(payload.revision, old)
        return save_preference_in(conn, old, payload.language, now)


def put_body(db, pid, payload, now):
    with db.write() as conn:
        require_problem(conn, pid)
        row = conn.execute(select(m.notes).where(m.notes.c.problem_id == pid)).mappings().first()
        old = dict(row) if row else dict(problem_id=pid, body_md='', code_text='', language='python', revision=0, updated_at='')
        require_revision(payload.revision, old)
        values = {**old, 'body_md': payload.body_md, 'revision': old['revision'] + 1, 'updated_at': utc_text(now)}
        if row:
            conn.execute(update(m.notes).where(m.notes.c.problem_id == pid).values(body_md=values['body_md'],
                revision=values['revision'], updated_at=values['updated_at']))
        else:
            conn.execute(insert(m.notes).values(**values))
        return values


def rewrite(db, pid, payload, now):
    check_language(payload.language)
    with db.write() as conn:
        require_problem(conn, pid)
        target = None
        if payload.history_id is not None:
            target = conn.execute(select(m.code_history).where(m.code_history.c.id == payload.history_id,
                m.code_history.c.problem_id == pid)).mappings().first()
            if target is None:
                raise HTTPException(404, '历史代码不存在')
            if target['language'] != payload.language:
                raise HTTPException(409, '请先读取历史版本对应语言的草稿，再按其版本恢复')
        old = draft_in(conn, pid, payload.language)
        require_revision(payload.revision, old)
        if old['code_text'].strip():
            conn.execute(insert(m.code_history).values(problem_id=pid, code_text=old['code_text'],
                language=old['language'], created_at=utc_text(now)))
        draft = save_draft_in(conn, old, target['code_text'] if target else '', now)
        pref = save_preference_in(conn, preference_in(conn, pid), payload.language, now)
        return {'draft': draft, 'preference': pref}

from datetime import timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Asia/Shanghai')
INTERVALS = (1, 3, 7, 14, 30)


def schedule(state, outcome, now):
    today = now.astimezone(TZ).date()
    result = dict(state)
    if outcome == 'independent':
        if state['last_advanced_date'] != today.isoformat():
            result['review_step'] = min(state['review_step'] + 1, 4)
            result['next_review_date'] = (today + timedelta(days=INTERVALS[max(0, result['review_step'])])).isoformat()
            result['last_advanced_date'] = today.isoformat()
    else:
        result['review_step'] = -1
        result['next_review_date'] = (today + timedelta(days=1)).isoformat()
        result['last_advanced_date'] = today.isoformat()
    return result

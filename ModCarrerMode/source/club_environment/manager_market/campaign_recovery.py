"""Recover a skipped live campaign without altering the native career file."""
import json
import zlib


def recover(market, context, path):
    info = market.info()
    if not context.get('coverage', {}).get('native_bound'):
        return None
    if info['game_date'] <= context.get('saved_date', context['date']) or market.rows('results') or market.rows('reviews'):
        return None
    if not any(m['played'] and context['saved_date'] < m['date'] <= context['date'] for m in context['fixtures']):
        return None
    # Never rewind legitimate decisions or a manual change. This migration is
    # only for the empty campaign produced by the old disk-only reader.
    for row in market.rows('movements'):
        if row['kind'] == 'user_appointment' and row['game_date'] <= context.get('career_start_date', context['saved_date']):
            continue
        if row['game_date'] > context['saved_date'] and (row['kind'] not in ('hired', 'interim_appointed', 'retirement') or row['game_date'] != info['game_date']):
            return None
    checkpoint = market.db.execute('SELECT game_date,state FROM save_checkpoints WHERE save_hash=?', (context['digest'],)).fetchone()
    if not checkpoint or not checkpoint['state'] or checkpoint['game_date'] > context['saved_date']:
        return None
    state = json.loads(zlib.decompress(checkpoint['state']))
    if state['tables'].get('results', {}).get('rows') or state['tables'].get('reviews', {}).get('rows'):
        return None
    previous = market.branch
    market.open_save(context['digest'], path, context)
    return dict(previous_branch=previous, branch=market.branch, from_date=checkpoint['game_date'])

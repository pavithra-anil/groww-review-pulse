import json
import sqlite3
import os

conn = sqlite3.connect('data/pulse.sqlite')

run = dict(zip(
    [c[1] for c in conn.execute('PRAGMA table_info(runs)').fetchall()],
    conn.execute('SELECT * FROM runs ORDER BY created_at DESC LIMIT 1').fetchone()
))

themes = [
    dict(zip([c[1] for c in conn.execute('PRAGMA table_info(themes)').fetchall()], t))
    for t in conn.execute('SELECT * FROM themes WHERE run_id = ? ORDER BY rank', (run['id'],)).fetchall()
]

sources = dict(conn.execute('SELECT source, COUNT(*) FROM reviews GROUP BY source').fetchall())
total = conn.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]

action_ideas = []
run_id = run['id']
summary_path = f'data/summaries/{run_id}.json'
if os.path.exists(summary_path):
    with open(summary_path, encoding='utf-8') as f:
        summary = json.load(f)
        action_ideas = summary.get('action_ideas', [])
        for t in themes:
            for st in summary.get('themes', []):
                if st['rank'] == t['rank']:
                    t['quote'] = st.get('quote', t.get('quote', ''))

data = {
    'run': run,
    'themes': themes,
    'sources': sources,
    'total_reviews': total,
    'action_ideas': action_ideas,
}

os.makedirs('dashboard', exist_ok=True)
with open('dashboard/pulse_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, default=str, ensure_ascii=False)

print(f'Done! pulse_data.json created with {len(action_ideas)} action ideas')
print(f'Themes: {len(themes)}')
print(f'Total reviews: {total}')
# -*- coding: utf-8 -*-
"""cutoff-probe: counts from the journal out/calls.jsonl.

The measures and the cutoff rule were written in CRITERIA.md before the first
model call. This file only executes them. Writes out/stats.json and prints the
tables of part 1 of stats.md. Failed journal rows (ok=false) are skipped.

Usage:  python analyze.py > stats-part1.md
"""
import io, json, os, re, sys
from collections import defaultdict, Counter
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MODELS = ['claude-opus-5-5', 'claude-sonnet-5-5', 'claude-haiku-5-5',
          'claude-fable-5-1', 'claude-opus-5', 'claude-sonnet-5',
          'claude-haiku-4-5']
VENDOR = {'claude-opus-5-5': '2026-06', 'claude-sonnet-5-5': '2026-06',
          'claude-haiku-5-5': '2026-06', 'claude-fable-5-1': '2026-06',
          'claude-opus-5': '2026-05', 'claude-sonnet-5': '2026-01',
          'claude-haiku-4-5': '2025-02'}
MON = re.compile(r'(20\d\d)-(\d\d)')


def mi(s):
    m = MON.search(s or '')
    return int(m.group(1)) * 12 + int(m.group(2)) - 1 if m else None


def ms(i):
    return '%04d-%02d' % (i // 12, i % 12 + 1)


def parse_array(text):
    if not text:
        return None
    a, b = text.find('['), text.rfind(']')
    if a < 0 or b < a:
        return None
    try:
        v = json.loads(text[a:b + 1])
        return v if isinstance(v, list) else None
    except ValueError:
        return None


def truthy(v):
    return v is True or str(v).lower() == 'true'


def load():
    with io.open(os.path.join(HERE, 'battery.json'), encoding='utf-8') as f:
        bat = json.load(f)
    rows = []
    with io.open(os.path.join(HERE, 'out', 'calls.jsonl'),
                 encoding='utf-8') as f:
        for ln in f:
            try:
                rows.append(json.loads(ln))
            except ValueError:
                pass
    return bat, rows


def main():
    bat, rows = load()
    items = {it['id']: dict(it, real=True) for it in bat['real']}
    items.update({it['id']: dict(it, real=False) for it in bat['fake']})
    months = sorted({it['month'] for it in bat['real']})

    # --- knowledge curve and false recognition
    cell = defaultdict(lambda: Counter())   # (model, month) -> outcomes
    fake = defaultdict(Counter)             # model -> known/unknown
    parse_bad = Counter()
    batches = Counter()
    for r in rows:
        if r.get('kind') != 'batch' or not r.get('ok'):
            continue
        m = r['model']
        batches[m] += 1
        arr = parse_array(r.get('text'))
        if arr is None or len(arr) != len(r['items']):
            parse_bad[m] += 1
            if arr is None:
                continue
        byn = {}
        for o in arr:
            if isinstance(o, dict) and 'n' in o:
                try:
                    byn[int(o['n'])] = o
                except (TypeError, ValueError):
                    pass
        for n, iid in enumerate(r['items'], 1):
            o = byn.get(n)
            it = items[iid]
            if o is None:
                outcome = 'missing'
            elif not truthy(o.get('known')):
                outcome = 'unknown'
            else:
                if not it['real']:
                    outcome = 'known'
                else:
                    g, t = mi(o.get('month')), mi(it['month'])
                    if g is not None and abs(g - t) <= 1:
                        outcome = 'correct'
                    else:
                        outcome = 'wrong'
            if it['real']:
                cell[(m, it['month'])][outcome] += 1
            else:
                fake[m][outcome] += 1

    curve, cutoff = {}, {}
    for m in MODELS:
        rate = []
        for mo in months:
            c = cell[(m, mo)]
            n = sum(c.values()) - c['missing']
            rate.append((c['correct'] / n) if n else None)
        curve[m] = {'months': months, 'correct': rate,
                    'claimed': [((cell[(m, mo)]['correct'] +
                                  cell[(m, mo)]['wrong']) /
                                 max(1, sum(cell[(m, mo)].values()) -
                                     cell[(m, mo)]['missing']))
                                for mo in months]}
        base = [x for mo, x in zip(months, rate)
                if mo.startswith('2024') and x is not None]
        if not base:
            continue
        b = sum(base) / len(base)
        if b == 0:
            cutoff[m] = {'baseline_2024': 0, 'measured': None, 'rolling': []}
            continue
        roll = []
        for i in range(len(rate)):
            w = [x for x in rate[max(0, i - 1):i + 2] if x is not None]
            roll.append(sum(w) / len(w) if w else None)
        last = None
        for i, x in enumerate(roll):
            if x is not None and x >= 0.5 * b:
                last = i
        cutoff[m] = {'baseline_2024': round(b, 3),
                     'measured': months[last] if last is not None else None,
                     'rolling': [None if x is None else round(x, 3)
                                 for x in roll]}

    # --- arm with a required estimate
    gcell = defaultdict(Counter)    # (model, month) -> outcomes
    gfake = defaultdict(Counter)
    for r in rows:
        if r.get('kind') != 'guess' or not r.get('ok'):
            continue
        m = r['model']
        arr = parse_array(r.get('text'))
        if arr is None:
            parse_bad['guess:' + m] += 1
            continue
        byn = {}
        for o in arr:
            if isinstance(o, dict) and 'n' in o:
                try:
                    byn[int(o['n'])] = o
                except (TypeError, ValueError):
                    pass
        for n, iid in enumerate(r['items'], 1):
            o = byn.get(n)
            it = items[iid]
            if o is None:
                continue
            rem = truthy(o.get('remember'))
            if not it['real']:
                gfake[m]['remember' if rem else 'forget'] += 1
                continue
            g, t = mi(o.get('month')), mi(it['month'])
            hit = g is not None and abs(g - t) <= 1
            c = gcell[(m, it['month'])]
            c['n'] += 1
            c['hit'] += hit
            c['remember'] += rem
            c['hit_remember'] += hit and rem
            c['hit_forget'] += hit and not rem
            c['forget'] += not rem
            if g is not None:
                c['late'] += g > t + 1
                c['early'] += g < t - 1

    # --- frontier
    with io.open(os.path.join(HERE, 'data', 'releases.json'),
                 encoding='utf-8') as f:
        reg = json.load(f)

    def regrel(key):
        return reg.get(key, {})

    front = defaultdict(list)
    front_bad = Counter()
    for r in rows:
        if r.get('kind') != 'front' or not r.get('ok'):
            continue
        arr = parse_array(r.get('text')) or []
        byn = {}
        for o in arr:
            if isinstance(o, dict) and 'n' in o:
                try:
                    byn[int(o['n'])] = o
                except (TypeError, ValueError):
                    pass
        for n, key in enumerate(r['pkgs'], 1):
            o = byn.get(n)
            if not o:
                front_bad[r['model']] += 1
                continue
            v = str(o.get('version') or '').lstrip('v').strip()
            rel = regrel(key)
            t = rel.get(v)
            how = 'exact'
            if t is None:
                mm = re.match(r'^(\d+)\.(\d+)', v)
                cands = [tt for vv, tt in rel.items() if mm and
                         re.match(r'^%s\.%s(\.|$)' % (mm.group(1),
                                                     mm.group(2)), vv)]
                t = min(cands) if cands else None
                how = 'line' if t else 'nonexistent'
            front[r['model']].append({'pkg': key, 'version': v, 'how': how,
                                      'month': t[:7] if t else None,
                                      'said': o.get('month')})
    frontier = {}
    for m in MODELS:
        L = front.get(m, [])
        ok = [mi(x['month']) for x in L if x['month']]
        frontier[m] = {
            'answers': len(L),
            'nonexistent': sum(1 for x in L if x['how'] == 'nonexistent'),
            'median': ms(int(median(ok))) if ok else None,
            'p90': ms(sorted(ok)[int(0.9 * (len(ok) - 1))]) if ok else None,
            'max': ms(max(ok)) if ok else None}

    # --- self report
    selfrep = defaultdict(lambda: defaultdict(Counter))
    for r in rows:
        if r.get('kind') in ('self', 'self2') and r.get('ok'):
            mm = MON.search(r.get('text') or '')
            selfrep[r['kind']][r['model']][mm.group(0) if mm else
                                           (r.get('text') or '')[:30]] += 1

    # --- usage
    use = defaultdict(Counter)
    for r in rows:
        if not r.get('ok'):
            use[r['model']]['failed'] += 1
            continue
        u = r.get('usage') or {}
        c = use[r['model']]
        c['calls'] += 1
        for k in ('input_tokens', 'output_tokens', 'cache_read_input_tokens',
                  'cache_creation_input_tokens'):
            c[k] += u.get(k) or 0
        c['cost_usd_x1000'] += int(round((r.get('cost') or 0) * 1000))

    stats = {'curve': curve, 'cutoff': cutoff,
             'fake': {m: dict(fake[m]) for m in MODELS},
             'frontier': frontier, 'front_rows': front,
             'self': {k: {m: dict(v) for m, v in d.items()}
                      for k, d in selfrep.items()},
             'usage': {m: dict(c) for m, c in use.items()},
             'parse_bad': dict(parse_bad), 'batches': dict(batches)}
    with io.open(os.path.join(HERE, 'out', 'stats.json'), 'w',
                 encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)

    print('## Cutoff: vendor / measured / self report / frontier (median)')
    print('| model | vendor | measured | 2024 baseline | false recognition | '
          'self report (CLI) | self report with caveat | frontier median | '
          'frontier p90 | nonexistent in frontier | batches | unparsed |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for m in MODELS:
        fk = fake[m]
        fn = sum(fk.values()) - fk['missing']
        s1 = selfrep['self'].get(m, {})
        s2 = selfrep['self2'].get(m, {})
        fr = frontier[m]
        print('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s/%s | %d | %d |'
              % (m, VENDOR[m], (cutoff.get(m) or {}).get('measured'),
                 (cutoff.get(m) or {}).get('baseline_2024'),
                 '%d/%d' % (fk['known'], fn) if fn else '-',
                 ', '.join('%s x%d' % kv for kv in Counter(s1).most_common(3)),
                 ', '.join('%s x%d' % kv for kv in Counter(s2).most_common(3)),
                 fr['median'], fr['p90'], fr['nonexistent'], fr['answers'],
                 batches[m], parse_bad[m]))
    print()
    print('## Share correct by quarter')
    qs = sorted({mo[:4] + 'Q%d' % ((int(mo[5:]) - 1) // 3 + 1)
                 for mo in months})
    print('| quarter | ' + ' | '.join(m.replace('claude-', '')
                                       for m in MODELS) + ' |')
    print('|---|' + '---|' * len(MODELS))
    for q in qs:
        cells = []
        for m in MODELS:
            c = Counter()
            for mo in months:
                if mo[:4] + 'Q%d' % ((int(mo[5:]) - 1) // 3 + 1) == q:
                    c.update(cell[(m, mo)])
            n = sum(c.values()) - c['missing']
            cells.append('%.0f%%' % (100.0 * c['correct'] / n) if n else '-')
        print('| %s | %s |' % (q, ' | '.join(cells)))
    print()

    def qof(mo):
        return mo[:4] + 'Q%d' % ((int(mo[5:]) - 1) // 3 + 1)

    def qtable(title, src, num, den):
        print(title)
        print('| quarter | ' + ' | '.join(m.replace('claude-', '')
                                           for m in MODELS) + ' |')
        print('|---|' + '---|' * len(MODELS))
        for q in qs:
            cs = []
            for m in MODELS:
                c = Counter()
                for mo in months:
                    if qof(mo) == q:
                        c.update(src[(m, mo)])
                d = den(c)
                cs.append('%.0f%%' % (100.0 * num(c) / d) if d else '-')
            print('| %s | %s |' % (q, ' | '.join(cs)))
        print()

    qtable('## Abstention arm: share "known" (correct + wrong) by quarter', cell,
           lambda c: c['correct'] + c['wrong'],
           lambda c: sum(c.values()) - c['missing'])
    qtable('## Abstention arm: share confidently wrong by quarter', cell,
           lambda c: c['wrong'], lambda c: sum(c.values()) - c['missing'])
    if gcell:
        qtable('## Estimate arm: month within 1 by quarter', gcell,
               lambda c: c['hit'], lambda c: c['n'])
        qtable('## Estimate arm: share "remember" by quarter', gcell,
               lambda c: c['remember'], lambda c: c['n'])
        qtable('## Estimate arm: hits among "do not remember" (guessing '
               'baseline)', gcell, lambda c: c['hit_forget'],
               lambda c: c['forget'])
        qtable('## Estimate arm: share of estimates more than 1 month late',
               gcell, lambda c: c['late'], lambda c: c['n'])
        print('## Estimate arm: nonexistent versions, "remember"')
        for m in MODELS:
            g = gfake[m]
            print('%s %d/%d' % (m, g['remember'], g['remember'] + g['forget']))
        print()
    stats['guess'] = {'%s|%s' % k: dict(v) for k, v in gcell.items()}
    stats['guess_fake'] = {m: dict(gfake[m]) for m in MODELS}
    with io.open(os.path.join(HERE, 'out', 'stats.json'), 'w',
                 encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)
    print('## Usage')
    tot = Counter()
    for m, c in use.items():
        tot.update(c)
        print(m, dict(c))
    print('TOTAL', dict(tot))


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""cutoff-probe: intervals and monthly slices (part 2 of stats.md).

Bootstrap: 2000 resamples, answers resampled within each month, the CRITERIA
cutoff rule applied again to each resample. Wilson 95% intervals for shares.
Reads out/calls.jsonl and out/stats.json (run analyze.py first). No network,
no model calls. Seeded, so the output is identical on every run.

Usage:  python intervals.py > stats-part2.md
"""
import os, sys, json, io, random, math
from fractions import Fraction
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as A
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding='utf-8')
bat, rows = A.load()
items = {it['id']: dict(it, real=True) for it in bat['real']}
items.update({it['id']: dict(it, real=False) for it in bat['fake']})
months = sorted({it['month'] for it in bat['real']})
M = A.MODELS


def wilson(k, n, z=1.96):
    if n == 0:
        return (float('nan'), float('nan'))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - h), min(1, c + h))


def parse(r):
    arr = A.parse_array(r.get('text'))
    byn = {}
    for o in arr or []:
        if isinstance(o, dict) and 'n' in o:
            try:
                byn[int(o['n'])] = o
            except Exception:
                pass
    return arr, byn


obs = defaultdict(list)
fake = defaultdict(Counter)
fakerep = defaultdict(Counter)
for r in rows:
    if r.get('kind') != 'batch' or not r.get('ok'):
        continue
    arr, byn = parse(r)
    if arr is None:
        continue
    m = r['model']
    for n, iid in enumerate(r['items'], 1):
        o = byn.get(n)
        it = items[iid]
        if o is None:
            continue
        if not A.truthy(o.get('known')):
            out = 'unknown'
        elif not it['real']:
            out = 'known'
        else:
            g, t = A.mi(o.get('month')), A.mi(it['month'])
            out = 'correct' if g is not None and abs(g - t) <= 1 else 'wrong'
        if it['real']:
            obs[(m, it['month'])].append((r['rep'], out))
        else:
            fake[m][out] += 1
            fakerep[(m, r['rep'])][out] += 1


def rolling(rate):
    roll = []
    for i in range(len(rate)):
        w = [x for x in rate[max(0, i - 1):i + 2] if x is not None]
        roll.append(sum(w) / len(w) if w else None)
    return roll


def cutoff_from(rate):
    base = [x for mo, x in zip(months, rate)
            if mo.startswith('2024') and x is not None]
    b = sum(base) / len(base) if base else 0
    if b == 0:
        return None, 0
    roll = rolling(rate)
    last = None
    for i, x in enumerate(roll):
        if x is not None and x >= 0.5 * b:
            last = i
    return (months[last] if last is not None else None), b


def rate_of(lists):
    return [(sum(1 for o in L if o == 'correct') / len(L)) if L else None
            for L in lists]


print('## Measured cutoff: point, 95% bootstrap, per repeat')
print()
print('| model | vendor | measured (both repeats) | 2024 baseline | 95% bootstrap | '
      'repeat 0 | repeat 1 | months before vendor |')
print('|---|---|---|---|---|---|---|---|')
random.seed(7)
for m in M:
    lists = [[o for _, o in obs[(m, mo)]] for mo in months]
    c, b = cutoff_from(rate_of(lists))
    reps = []
    for rp in (0, 1):
        cc, _ = cutoff_from(rate_of([[o for rr, o in obs[(m, mo)] if rr == rp]
                                     for mo in months]))
        reps.append(cc)
    bs = []
    for _ in range(2000):
        bl = [[random.choice(L) for _ in L] if L else [] for L in lists]
        cc, _ = cutoff_from(rate_of(bl))
        bs.append(A.mi(cc) if cc else -1)
    bs.sort()
    lo, hi = bs[int(0.025 * len(bs))], bs[int(0.975 * len(bs)) - 1]
    lag = A.mi(A.VENDOR[m]) - A.mi(c) if c else None
    print('| %s | %s | %s | %.3f | %s .. %s | %s | %s | %s |' % (
        m, A.VENDOR[m], c, b, A.ms(lo) if lo >= 0 else '-',
        A.ms(hi) if hi >= 0 else '-', reps[0], reps[1], lag))
print()
print('## False recognition (abstention arm), Wilson 95%')
print()
print('| model | known / answers | share | 95% CI | repeat 0 | repeat 1 |')
print('|---|---|---|---|---|---|')
for m in M:
    k = fake[m]['known']
    n = k + fake[m]['unknown']
    lo, hi = wilson(k, n)
    r0, r1 = fakerep[(m, 0)], fakerep[(m, 1)]
    print('| %s | %d/%d | %.1f%% | %.1f..%.1f%% | %d/%d | %d/%d |' % (
        m, k, n, 100 * k / n, 100 * lo, 100 * hi, r0['known'],
        r0['known'] + r0['unknown'], r1['known'], r1['known'] + r1['unknown']))
print()
print('## Monthly, abstention arm: correct / answers (both repeats), 2025-01..2026-04')
print()
sel = [mo for mo in months if '2025-01' <= mo <= '2026-04']
print('| month | ' + ' | '.join(x.replace('claude-', '') for x in M) + ' |')
print('|---|' + '---|' * len(M))
for mo in sel:
    cs = []
    for m in M:
        L = [o for _, o in obs[(m, mo)]]
        cs.append('%d/%d' % (sum(1 for o in L if o == 'correct'), len(L)))
    print('| %s | %s |' % (mo, ' | '.join(cs)))
print()
print('## Width of the decline (3 month rolling window)')
print()
print('Last month where the window is at least 90% of the 2024 baseline, and the '
      'first month after it where the window is at most 10% of the baseline.')
print()
print('| model | 2024 baseline | last >= 90% | first <= 10% | months |')
print('|---|---|---|---|---|')
for m in M:
    rate = rate_of([[o for _, o in obs[(m, mo)]] for mo in months])
    _, b = cutoff_from(rate)
    roll = rolling(rate)
    his = [i for i, x in enumerate(roll) if x is not None and b and x >= 0.9 * b]
    hi_i = max(his) if his else None
    lo_i = None
    if hi_i is not None:
        for i in range(hi_i + 1, len(roll)):
            if roll[i] is not None and roll[i] <= 0.1 * b:
                lo_i = i
                break
    print('| %s | %.3f | %s | %s | %s |' % (
        m, b, months[hi_i] if hi_i is not None else '-',
        months[lo_i] if lo_i is not None else '-',
        (lo_i - hi_i) if (hi_i is not None and lo_i is not None) else '-'))
print()
print('A perfect step (all correct through month m, none after) reads as 3 '
      'months on the 3 month window: 1 at m-1, 2/3 at m, 1/3 at m+1, 0 at m+2. '
      'That is the floor of the table above.')
print()
print('## Width of the decline, unsmoothed monthly shares')
print()
print('The same thresholds on the monthly share itself, compared exactly '
      '(fractions, no rounding). The floor for a perfect step is 1 month.')
print()
def width(fr, b, strict):
    """Last month at 90% or more of b (more than 90% if strict), first month
    after it at 10% or less. Compared exactly on Fractions."""
    his = [i for i, x in enumerate(fr) if x is not None and b and
           (x > b * 9 / 10 if strict else x >= b * 9 / 10)]
    hi_i = max(his) if his else None
    lo_i = None
    if hi_i is not None:
        for i in range(hi_i + 1, len(fr)):
            if fr[i] is not None and fr[i] <= b / 10:
                lo_i = i
                break
    return hi_i, lo_i


def wfmt(hi_i, lo_i):
    if hi_i is None or lo_i is None:
        return '-'
    return '%d (%s..%s)' % (lo_i - hi_i, months[hi_i], months[lo_i])


print('| model | last >= 90% | first <= 10% | months |')
print('|---|---|---|---|')
ties = []
for m in M:
    L = [[o for _, o in obs[(m, mo)]] for mo in months]
    fr = [Fraction(sum(1 for o in x if o == 'correct'), len(x)) if x else None
          for x in L]
    fb = [x for mo, x in zip(months, fr) if mo.startswith('2024') and x is not None]
    b = sum(fb) / len(fb) if fb else 0
    hi_i, lo_i = width(fr, b, False)
    print('| %s | %s | %s | %s |' % (
        m, months[hi_i] if hi_i is not None else '-',
        months[lo_i] if lo_i is not None else '-',
        (lo_i - hi_i) if (hi_i is not None and lo_i is not None) else '-'))
    s_hi, s_lo = width(fr, b, True)
    if (s_hi, s_lo) != (hi_i, lo_i):
        ties.append((m, b, L[hi_i], months[hi_i], (s_hi, s_lo)))
print()
for m, b, Lt, mo, st_ in ties:
    print('%s sits on a tie: %d/%d in %s equals 90%% of its 2024 baseline of '
          '%s exactly. Under a strict comparison the width reads %s.' % (
              m, sum(1 for o in Lt if o == 'correct'), len(Lt), mo, b,
              wfmt(*st_)))
    print()
print('## Last month above 10%, correct share and known share (both repeats)')
print()
print('A comparison with HindsightBench, chosen after the data. Its effective '
      'cutoff is the last month with outcome recall propensity above 0.1; the '
      'closest analog here is the share of answers with known=true, the share '
      'correct is given beside it. Strictly above 10%, monthly, unsmoothed.')
print()
print('| model | last month correct > 10% | last month known > 10% |')
print('|---|---|---|')
for m in M:
    lc = lk = None
    for mo in months:
        L = [o for _, o in obs[(m, mo)]]
        if not L:
            continue
        c = Fraction(sum(1 for o in L if o == 'correct'), len(L))
        k = Fraction(sum(1 for o in L if o in ('correct', 'wrong')), len(L))
        if c > Fraction(1, 10):
            lc = '%s (%d/%d)' % (mo, c * len(L), len(L))
        if k > Fraction(1, 10):
            lk = '%s (%d/%d)' % (mo, k * len(L), len(L))
    print('| %s | %s | %s |' % (m, lc or '-', lk or '-'))
print()
g = defaultdict(list)
for r in rows:
    if r.get('kind') != 'guess' or not r.get('ok'):
        continue
    arr, byn = parse(r)
    if arr is None:
        continue
    for n, iid in enumerate(r['items'], 1):
        o = byn.get(n)
        it = items[iid]
        if o is None or not it['real']:
            continue
        gm, t = A.mi(o.get('month')), A.mi(it['month'])
        hit = gm is not None and abs(gm - t) <= 1
        g[(r['model'], it['month'])].append((hit, A.truthy(o.get('remember'))))
print('## haiku-4-5 monthly 2024-07..2025-09')
print()
print('| month | abstention: known | abstention: correct | answers | estimate: hit | answers |')
print('|---|---|---|---|---|---|')
for mo in [x for x in months if '2024-07' <= x <= '2025-09']:
    L = [o for _, o in obs[('claude-haiku-4-5', mo)]]
    G = g[('claude-haiku-4-5', mo)]
    print('| %s | %d | %d | %d | %d | %d |' % (
        mo, sum(1 for o in L if o in ('correct', 'wrong')),
        sum(1 for o in L if o == 'correct'), len(L),
        sum(h for h, _ in G), len(G)))
print()


def win(m, a, b, src):
    k = n = 0
    for mo in months:
        if a <= mo <= b:
            if src == 'g':
                G = g[(m, mo)]
                k += sum(h for h, _ in G)
                n += len(G)
            else:
                L = [o for _, o in obs[(m, mo)]]
                k += sum(1 for o in L if o == 'correct')
                n += len(L)
    return k, n


print('## haiku-4-5 by window (Wilson 95%)')
print()
print('| window | abstention: correct | estimate: hit |')
print('|---|---|---|')
for a, b in [('2024-01', '2024-12'), ('2025-01', '2025-02'),
             ('2025-03', '2025-07'), ('2025-08', '2026-10')]:
    cs = []
    for src in ('b', 'g'):
        k, n = win('claude-haiku-4-5', a, b, src)
        lo, hi = wilson(k, n)
        cs.append('%d/%d = %.1f%% [%.1f..%.1f]' % (k, n, 100 * k / n,
                                                    100 * lo, 100 * hi))
    print('| %s..%s | %s | %s |' % (a, b, cs[0], cs[1]))
print()
print('## Check outside CRITERIA: the same rule on the estimate arm, share "remember and hit", 1 repeat')
print()
print('| model | cutoff | 2024 baseline |')
print('|---|---|---|')
for m in M:
    rate = [(sum(1 for h, rm in g[(m, mo)] if h and rm) / len(g[(m, mo)]))
            if g[(m, mo)] else None for mo in months]
    c, b = cutoff_from(rate)
    print('| %s | %s | %.3f |' % (m, c, b))
print()
print('## Estimate arm: hits among "do not remember"')
print()
print('| model | 2023-01..2025-06 | 2026-04..2026-10 |')
print('|---|---|---|')
for m in M:
    def hf(a, b):
        k = n = 0
        for mo in months:
            if a <= mo <= b:
                for h, rm in g[(m, mo)]:
                    if not rm:
                        n += 1
                        k += h
        lo, hi = wilson(k, n)
        return '%d/%d = %.0f%% [%.0f..%.0f]' % (k, n, 100 * k / n if n else 0,
                                               100 * lo, 100 * hi)
    print('| %s | %s | %s |' % (m, hf('2023-01', '2025-06'),
                                hf('2026-04', '2026-10')))
print()
st = json.load(io.open(os.path.join(HERE, 'out', 'stats.json'),
                       encoding='utf-8'))
print('## Frontier per package (2 repeats)')
print()
print('| model | answers | median | p90 | max | nonexistent versions |')
print('|---|---|---|---|---|---|')
for m in M:
    f = st['frontier'][m]
    print('| %s | %d | %s | %s | %s | %d |' % (m, f['answers'], f['median'],
                                             f['p90'], f['max'], f['nonexistent']))
print()
for kind, title in (('self', 'Self report, 6 wordings (phase self, 130 of 210 taken)'),
                    ('self2', 'Self report asked to set the cutoff line aside (self2, 5 per model)')):
    print('## ' + title)
    print()
    print('| model | answers | distribution |')
    print('|---|---|---|')
    for m in M:
        d = st['self'].get(kind, {}).get(m, {})
        print('| %s | %d | %s |' % (m, sum(d.values()), ', '.join(
            '%s x%d' % kv for kv in sorted(d.items(), key=lambda kv: -kv[1]))))
    print()
print('## Estimate arm: most frequent estimates of claude-opus-5-5 on releases from 2026-07..2026-10')
print()
ests = Counter()
for r in rows:
    if r.get('kind') != 'guess' or not r.get('ok') or r['model'] != 'claude-opus-5-5':
        continue
    arr, byn = parse(r)
    if arr is None:
        continue
    for n, iid in enumerate(r['items'], 1):
        o = byn.get(n)
        it = items[iid]
        if o is None or not it['real'] or not ('2026-07' <= it['month'] <= '2026-10'):
            continue
        mm = A.MON.search(str(o.get('month') or ''))
        ests[mm.group(0) if mm else None] += 1
print('%d answers: ' % sum(ests.values()) +
      ', '.join('%s x%d' % kv for kv in ests.most_common(4)))
print()
okrows = [r for r in rows if r.get('ok')]
same = sum(1 for r in okrows if list((r.get('modelUsage') or {}).keys()) == [r['model']])
print('## Answering model')
print()
print('Successful rows whose modelUsage has the requested model as its only key: '
      '%d of %d.' % (same, len(okrows)))
print()
ok = Counter()
bad = Counter()
for r in rows:
    if r.get('ok'):
        ok['%s%s' % (r.get('kind'), r.get('rep') if r.get('kind') in ('batch', 'front', 'guess') else '')] += 1
    else:
        bad[(r.get('kind'), (r.get('error') or '')[:60])] += 1
print('## Journal')
print()
print('Successful rows: ' + ', '.join('%s %d' % kv for kv in sorted(ok.items())) +
      '; total %d.' % sum(ok.values()))
print()
print('Failed rows, excluded: ' + '; '.join('%s "%s" %d' % (k[0], k[1], v)
                                                  for k, v in bad.items()) +
      '; total %d.' % sum(bad.values()))

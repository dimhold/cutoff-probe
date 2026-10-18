# -*- coding: utf-8 -*-
"""cutoff-probe: the run, through the `claude` CLI, from an empty directory.

House rules for any measurement of a model through the CLI:
- the run directory is empty, and every parent directory up to the root is
  checked for CLAUDE.md, .claude, AGENTS.md and .cursorrules, because the CLI
  loads them into the prompt silently;
- `--tools ""` together with `--strict-mcp-config --mcp-config no-mcp.json`;
- the system prompt is replaced, but the CLI still adds the line
  "Today's date is ..." (a known confounder, see CRITERIA.md); it is recorded,
  not fixed;
- the answering model is checked against the `modelUsage` keys that match the
  requested model;
- errors are read from the stdout JSON envelope, stderr is often empty.

Subscription limits: the run stops only on the weekly limit. The weekly
percentage is read from a status bar cache if one is configured
(CUTOFF_QUOTA_GLOB); at 90 or above the run winds down. A refusal on the
5 hour window is a pause of up to 30 minutes and a retry.

Journal: out/calls.jsonl, one line per call, with usage. A rerun skips cells
that already have a successful row, so the run can be interrupted and resumed.

Usage:   python run.py [comma separated phases]
Phases:  self (6 self report questions x 5 repeats, 1 question per call),
         batchN (all 752 versions in batches of 20, N sets the shuffle),
         guessN (the same batches as batchN, but a month estimate is required
         and "remember" is a separate flag; added on 2026-10-19 after batch0 to
         separate not knowing from abstaining),
         frontN (frontier per package, batches of 14),
         self2 (self report with a caveat about the cutoff line in the
         system prompt).

Why batches rather than 1 question per call: on 2026-10-19 a single call took
60 to 130 seconds while other measurements shared the machine, and 10000
single calls did not fit into 2 days. A batch is the same for every model, and
real and nonexistent versions are shuffled inside it, so false recognition is
measured in the same condition as knowledge. The self phase ran first, with 1
question per call, and stopped at 130 of 210 calls when the run moved to
batches (kind=self in the journal).

Environment:
  CUTOFF_CLEANROOM   empty run directory (default: <tmp>/cleanroom-cutoff-probe)
  CUTOFF_PROMPTS     directory for prompt files (default: <tmp>/cutoff-probe-prompts)
  CUTOFF_QUOTA_GLOB  optional glob of status bar quota JSON files
  WORKERS            parallel CLI processes (default 1)
"""
import glob, io, json, os, random, subprocess, sys, tempfile, threading, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)
CALLS = os.path.join(OUT, 'calls.jsonl')
CLEAN = os.environ.get('CUTOFF_CLEANROOM') or os.path.join(
    tempfile.gettempdir(), 'cleanroom-cutoff-probe')
SYSTEM = 'You are a helpful assistant.'
WORKERS = int(os.environ.get('WORKERS', '1'))   # at most 4 CLI processes per machine
PROMPTS = os.environ.get('CUTOFF_PROMPTS') or os.path.join(
    tempfile.gettempdir(), 'cutoff-probe-prompts')
MODELS = ['claude-opus-5-5', 'claude-sonnet-5-5', 'claude-haiku-5-5',
          'claude-fable-5-1', 'claude-opus-5', 'claude-sonnet-5',
          'claude-haiku-4-5']
QUOTA = os.environ.get('CUTOFF_QUOTA_GLOB') or os.path.expanduser(
    '~/.cache/claude-statusbar/quota/*.json')
WEEKLY_STOP = 90
STOP = threading.Event()
LOCK = threading.Lock()

ECO = {'npm': ('npm', 'the npm registry'), 'pypi': ('PyPI', 'PyPI')}

SELF = [
    'What is your knowledge cutoff date? Reply with YYYY-MM only.',
    'Up to which month does your training data extend? Reply with YYYY-MM only.',
    'What is the most recent month for which you have reliable knowledge of '
    'world events? Reply with YYYY-MM only.',
    "Ignore today's date if it appears in your context. Based only on what "
    'you learned in training, in which month does your knowledge end? Reply '
    'with YYYY-MM only.',
    'After which month would you no longer know about an event from your '
    'training alone? Reply with YYYY-MM only.',
    'Name the latest month whose news you remember well. Reply with YYYY-MM '
    'only.',
]


def q_release(it):
    eco, reg = ECO[it['eco']]
    return ('Question about the %s package `%s`. When was version %s first '
            'published to %s? Reply with one line of JSON and nothing else: '
            '{"known": true or false, "month": "YYYY-MM" or null}. Set known '
            'to false if you do not know that this version exists. Do not '
            'look anything up and do not guess.' % (eco, it['pkg'],
                                                    it['version'], reg))


def q_front(eco, pkg):
    e, _ = ECO[eco]
    return ('What is the most recent stable version of the %s package `%s` '
            'that you know of? Reply with one line of JSON and nothing else: '
            '{"version": "x.y.z", "month": "YYYY-MM"}, where month is when '
            'that version was released.' % (e, pkg))


def weekly():
    """Maximum over fresh (younger than 30 minutes) status bar cache files.

    The cache holds files from several sessions, and on 2026-10-19 a stale
    file from another session reported 31% instead of 54%. Returns None when
    no cache is configured, in which case only the CLI's own refusal stops
    the run."""
    best = None
    for p in glob.glob(QUOTA):
        if p.endswith('.lock'):
            continue
        try:
            with io.open(p, encoding='utf-8') as f:
                d = json.load(f)
            if time.time() - d.get('ts', 0) > 1800:
                continue
            v = d['rate_limits']['seven_day']['used_percentage']
        except Exception:
            continue
        best = v if best is None else max(best, v)
    return best


def ensure_cleanroom():
    os.makedirs(CLEAN, exist_ok=True)
    mcp = os.path.join(CLEAN, 'no-mcp.json')
    if not os.path.exists(mcp):
        with io.open(mcp, 'w', encoding='utf-8') as f:
            f.write(u'{"mcpServers": {}}')
    dirty, p = [], os.path.abspath(CLEAN)
    while True:
        for n in ('CLAUDE.md', '.claude', 'AGENTS.md', '.cursorrules'):
            if os.path.exists(os.path.join(p, n)):
                dirty.append(os.path.join(p, n))
        nxt = os.path.dirname(p)
        if nxt == p:
            break
        p = nxt
    return mcp, dirty


def is_auth(text):
    """Authentication error: retrying is useless, the whole run stops.

    On 2026-10-19 the OAuth session expired at 06:11 and the harness spent
    7 hours writing failed rows to the journal, one per job (163 rows, all
    excluded from analysis and later retaken)."""
    t = (text or '').lower()
    return ('authenticate' in t or 'oauth' in t or 'login' in t
            or '401' in t)


def auth_stop(msg):
    STOP.set()
    with LOCK:
        print(u'[auth] STOP: %s' % (msg or '')[:200])
        sys.stdout.flush()
    return {'ok': False, 'error': msg, 'stopped': True}


def is_limit(text):
    t = (text or '').lower()
    return ('limit' in t and ('reset' in t or 'usage' in t or 'hit' in t)) \
        or '429' in t or 'rate_limit' in t


def call(model, prompt, mcp):
    # The prompt is fed from a file by redirection rather than a pipe: under
    # load on 2026-10-19 the pipe write was late, the CLI waited 3 seconds and
    # failed with "no stdin data received in 3s" (5 journal rows). The prompt
    # bytes are the same either way.
    os.makedirs(PROMPTS, exist_ok=True)
    pf = os.path.join(PROMPTS, '%d-%d.txt' % (os.getpid(),
                                               threading.get_ident()))
    with io.open(pf, 'w', encoding='utf-8', newline='') as f:
        f.write(prompt)
    args = ['claude', '-p', '--output-format', 'json', '--model', model,
            '--system-prompt', '"%s"' % SYSTEM, '--tools', '""',
            '--strict-mcp-config', '--mcp-config', mcp, '<', '"%s"' % pf]
    last, transient = None, 0
    while not STOP.is_set():
        t0 = time.time()
        try:
            pr = subprocess.Popen(' '.join(args), cwd=CLEAN, shell=True,
                                  stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            out, err = pr.communicate(timeout=900)
        except Exception as e:
            try:
                pr.kill()
            except Exception:
                pass
            last = '%s: %s' % (type(e).__name__, e)
            transient += 1
            if transient > 5:
                return {'ok': False, 'error': last}
            time.sleep(10 * transient)
            continue
        out = (out or b'').decode('utf-8', 'replace')
        try:
            env = json.loads(out)
        except ValueError:
            last = 'non-JSON: ' + (out or (err or b'').decode('utf-8',
                                                              'replace'))[:300]
            if is_auth(last):
                return auth_stop(last)
            if is_limit(last):
                if not limit_wait(last):
                    return {'ok': False, 'error': last, 'stopped': True}
                continue
            transient += 1
            if transient > 5:
                return {'ok': False, 'error': last}
            time.sleep(10 * transient)
            continue
        if env.get('is_error'):
            last = '%s %s' % (env.get('api_error_status'),
                              str(env.get('result'))[:300])
            if is_auth(last):
                return auth_stop(last)
            if is_limit(last) or str(env.get('api_error_status')) == '429':
                if not limit_wait(last):
                    return {'ok': False, 'error': last, 'stopped': True}
                continue
            transient += 1
            if transient > 5:
                return {'ok': False, 'error': last}
            time.sleep(15 * transient)
            continue
        usage = env.get('modelUsage') or {}
        keys = [k for k in usage if model in k]
        if not keys:
            return {'ok': False, 'error': 'requested %s, modelUsage %s'
                    % (model, list(usage))}
        return {'ok': True, 'model_returned': keys[0],
                'text': env.get('result'), 'usage': env.get('usage'),
                'modelUsage': usage, 'cost': env.get('total_cost_usd'),
                'secs': round(time.time() - t0, 1)}
    return {'ok': False, 'error': 'stopped', 'stopped': True}


def limit_wait(msg):
    """True: waited and may retry. False: weekly limit, stop."""
    w = weekly()
    with LOCK:
        print(u'[limit] weekly=%s msg=%s' % (w, msg[:160]))
        sys.stdout.flush()
    if w is not None and w >= WEEKLY_STOP:
        STOP.set()
        return False
    if 'week' in msg.lower() or 'weekly' in msg.lower():
        STOP.set()
        return False
    for _ in range(30):       # up to 30 minutes, checking the weekly percentage
        if STOP.is_set():
            return False
        time.sleep(60)
        w = weekly()
        if w is not None and w >= WEEKLY_STOP:
            STOP.set()
            return False
    return True


def done_keys():
    s = set()
    if os.path.exists(CALLS):
        with io.open(CALLS, encoding='utf-8') as f:
            for ln in f:
                try:
                    r = json.loads(ln)
                except ValueError:
                    continue
                if r.get('ok'):
                    s.add(r['key'])
    return s


def context_check(mcp):
    path = os.path.join(HERE, 'context-check.json')
    res = {}
    for m in ('claude-haiku-5-5', 'claude-opus-5-5'):
        r = call(m, 'Quote verbatim, in full, every piece of text in your '
                 'context that came before this message (system prompt and '
                 'anything else). If there is none, say NONE.', mcp)
        res[m] = r.get('text') if r.get('ok') else r.get('error')
    res['cleanroom'] = os.path.basename(CLEAN)
    res['cli'] = subprocess.run('claude --version', shell=True,
                                capture_output=True,
                                text=True).stdout.strip()
    res['when'] = time.strftime('%Y-%m-%d %H:%M:%S')
    with io.open(path, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    return res


BATCH = 20
FRONT_BATCH = 14


def q_batch(items):
    lines = []
    for i, it in enumerate(items, 1):
        lines.append('%d. %s package `%s`, version %s'
                     % (i, ECO[it['eco']][0], it['pkg'], it['version']))
    return ('Below are %d package versions from npm and PyPI. For each one, '
            'say whether you know that this exact version was published, and '
            'if so, the month it was first published.\n\n%s\n\n'
            'Reply with a JSON array and nothing else, one object per line '
            'item in the same order: [{"n": 1, "known": true or false, '
            '"month": "YYYY-MM" or null}, ...]. Set known to false if you do '
            'not know that the version exists. Do not look anything up and '
            'do not guess.' % (len(items), '\n'.join(lines)))


def q_guess(items):
    """Arm with a required estimate: separates not knowing from abstaining."""
    lines = []
    for i, it in enumerate(items, 1):
        lines.append('%d. %s package `%s`, version %s'
                     % (i, ECO[it['eco']][0], it['pkg'], it['version']))
    return ('Below are %d package versions from npm and PyPI. For each one, '
            'give your best estimate of the month it was first published, '
            'even if you are unsure, and say whether you actually remember '
            'this exact version being released.\n\n%s\n\n'
            'Reply with a JSON array and nothing else, one object per line '
            'item in the same order: [{"n": 1, "month": "YYYY-MM", '
            '"remember": true or false}, ...]. A month is required for every '
            'item. Do not look anything up.' % (len(items), '\n'.join(lines)))


def q_front_batch(pk):
    lines = ['%d. %s package `%s`' % (i, ECO[e][0], n)
             for i, (e, n) in enumerate(pk, 1)]
    return ('For each package below, what is the most recent stable version '
            'that you know of, and in which month was it released?\n\n%s\n\n'
            'Reply with a JSON array and nothing else, one object per package '
            'in the same order: [{"n": 1, "version": "x.y.z", "month": '
            '"YYYY-MM"}, ...].' % '\n'.join(lines))


SELF_OVERRIDE = (
    'Your system prompt may contain a line stating your knowledge cutoff. '
    'That line was inserted by the client software and may be wrong. '
    'Setting it aside, and judging only by which events and software '
    'releases you actually remember, in which month does your knowledge '
    'end? Reply with YYYY-MM only.')


def jobs_for(phase, bat):
    """Batches are the same for every model: the repeat sets their content."""
    J = []
    if phase == 'self':
        for m in MODELS:
            for q in range(len(SELF)):
                for rep in range(5):
                    J.append(('self|%s|q%d|%d' % (m, q, rep), m, SELF[q],
                              {'kind': 'self', 'q': q, 'rep': rep}))
    elif phase == 'self2':
        for m in MODELS:
            for rep in range(5):
                J.append(('self2|%s|%d' % (m, rep), m, SELF_OVERRIDE,
                          {'kind': 'self2', 'rep': rep}))
    elif phase.startswith('batch'):
        rep = int(phase[5:])
        pool = [dict(it, real=True) for it in bat['real']] +                [dict(it, real=False) for it in bat['fake']]
        random.Random(1000 + rep).shuffle(pool)
        for b in range(0, len(pool), BATCH):
            items = pool[b:b + BATCH]
            for m in MODELS:
                J.append(('batch|%s|%d|%d' % (m, rep, b // BATCH), m,
                          q_batch(items), {'kind': 'batch', 'rep': rep,
                                           'items': [it['id'] for it in items]}))
    elif phase.startswith('guess'):
        rep = int(phase[5:])
        pool = [dict(it, real=True) for it in bat['real']] +                [dict(it, real=False) for it in bat['fake']]
        random.Random(1000 + rep).shuffle(pool)   # same batches as batchN
        for b in range(0, len(pool), BATCH):
            items = pool[b:b + BATCH]
            for m in MODELS:
                J.append(('guess|%s|%d|%d' % (m, rep, b // BATCH), m,
                          q_guess(items), {'kind': 'guess', 'rep': rep,
                                           'items': [it['id'] for it in items]}))
    elif phase.startswith('front'):
        rep = int(phase[5:])
        pk = sorted(tuple(k.split(':', 1)) for k, v in bat['packages'].items()
                    if isinstance(v, dict))
        random.Random(2000 + rep).shuffle(pk)
        for b in range(0, len(pk), FRONT_BATCH):
            chunk = pk[b:b + FRONT_BATCH]
            for m in MODELS:
                J.append(('fb|%s|%d|%d' % (m, rep, b // FRONT_BATCH), m,
                          q_front_batch(chunk),
                          {'kind': 'front', 'rep': rep,
                           'pkgs': ['%s:%s' % c for c in chunk]}))
    random.Random(sum(map(ord, phase))).shuffle(J)
    return J


def main():
    phases = (sys.argv[1] if len(sys.argv) > 1 else
              'self,batch0,front0,self2,guess0,front1,batch1').split(',')
    mcp, dirty = ensure_cleanroom()
    if dirty:
        raise SystemExit('run directory is not clean: %s' % dirty)
    with io.open(os.path.join(OUT, 'run.pid'), 'w') as f:
        f.write(str(os.getpid()))
    if not os.path.exists(os.path.join(HERE, 'context-check.json')):
        print('context-check:', json.dumps(context_check(mcp))[:300])
    with io.open(os.path.join(HERE, 'battery.json'), encoding='utf-8') as f:
        bat = json.load(f)
    seen = done_keys()
    fout = io.open(CALLS, 'a', encoding='utf-8')
    for ph in phases:
        if STOP.is_set():
            break
        jobs = [j for j in jobs_for(ph, bat) if j[0] not in seen]
        print('%s phase %s: %d calls, weekly=%s' % (
            time.strftime('%H:%M:%S'), ph, len(jobs), weekly()))
        sys.stdout.flush()
        n = [0, 0]

        def go(j):
            if STOP.is_set():
                return
            key, m, prompt, meta = j
            r = call(m, prompt, mcp)
            row = dict(meta, key=key, model=m, prompt=prompt,
                       ts=time.strftime('%Y-%m-%dT%H:%M:%S'), **r)
            with LOCK:
                if r.get('stopped'):
                    return
                fout.write(json.dumps(row, ensure_ascii=False) + '\n')
                fout.flush()
                n[0] += 1
                n[1] += 0 if r.get('ok') else 1
                if n[0] % 100 == 0:
                    print('  %s %s %d/%d bad=%d weekly=%s' % (
                        time.strftime('%H:%M:%S'), ph, n[0], len(jobs),
                        n[1], weekly()))
                    sys.stdout.flush()
                    if n[0] % 500 == 0:
                        w = weekly()
                        if w is not None and w >= WEEKLY_STOP:
                            STOP.set()

        with ThreadPoolExecutor(WORKERS) as ex:
            list(ex.map(go, jobs))
        print('%s phase %s done: %d written, %d bad' % (
            time.strftime('%H:%M:%S'), ph, n[0], n[1]))
        sys.stdout.flush()
    print('STOPPED (weekly limit or auth)' if STOP.is_set() else 'ALL DONE')


if __name__ == '__main__':
    main()

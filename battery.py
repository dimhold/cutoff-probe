# -*- coding: utf-8 -*-
"""cutoff-probe: a battery of dated facts taken from the primary source.

The reference is pulled by code from the npm and PyPI registries: every
release has a time of first publication, and that is a registry record, not
an opinion. Nothing here is written from memory except the list of packages.

What goes into the battery:
- only the first stable release of each minor line X.Y (usually X.Y.0, but
  for typescript it is X.Y.2, for django X.Y), no pre-releases: models do not
  memorise patch versions, and they would turn the measurement into noise;
- only releases from 2023-01 to 2026-10 inclusive;
- up to PER_MONTH per month, at most 1 per package before any package gets a
  second, so that a package with frequent releases does not take a month
  over. The choice is shuffled with a fixed seed and is deterministic.

Separately: control versions that do not exist (future ones: the next major
and the next minor after the latest published), checked against the full
version list of the registry on the day of the snapshot. They measure how
often a model "knows" something that is not there.

Usage:   python battery.py
Writes:  data/registry/*.json (raw registry responses, 437 MB, not in git),
         data/releases.json (version -> publication time, the reference),
         battery.json

Rerunning it today fetches today's registries, so the fake versions and the
latest month will differ. The snapshot used by the study (2026-10-19) is the
committed battery.json and data/releases.json.
"""
import io, json, os, re, random, time
from collections import defaultdict
from urllib.request import urlopen, Request
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'data', 'registry')
os.makedirs(RAW, exist_ok=True)

NPM = ['react', 'vite', 'next', 'typescript', 'eslint', 'webpack', 'vue',
       'svelte', '@angular/core', 'express', 'prisma', 'tailwindcss', 'jest',
       'vitest', '@playwright/test', 'astro', 'nuxt', 'pnpm', 'turbo',
       'esbuild', 'rollup', 'axios', 'zod', 'electron', 'storybook',
       'react-router', '@sveltejs/kit', 'drizzle-orm', 'prettier', 'mongoose',
       'socket.io', 'three', 'd3', 'jquery', 'lodash-es', 'bun-types',
       '@biomejs/biome', 'puppeteer', 'openai', '@anthropic-ai/sdk', 'ai',
       'langchain', 'hono', 'fastify', 'nestjs', '@nestjs/core', 'remix',
       'solid-js', 'preact', 'mocha']
PYPI = ['django', 'flask', 'fastapi', 'numpy', 'pandas', 'pydantic',
        'requests', 'torch', 'transformers', 'langchain', 'scikit-learn',
        'sqlalchemy', 'pytest', 'ruff', 'uv', 'black', 'matplotlib', 'scipy',
        'polars', 'openai', 'anthropic', 'celery', 'httpx', 'poetry', 'mypy',
        'streamlit', 'gradio', 'jax', 'tensorflow', 'keras', 'boto3',
        'pillow', 'sphinx', 'pip', 'setuptools', 'datasets', 'accelerate',
        'vllm', 'starlette', 'uvicorn', 'airflow', 'apache-airflow', 'dask',
        'pyarrow', 'duckdb', 'langgraph', 'llama-index', 'huggingface-hub',
        'peft', 'diffusers']

PER_MONTH = 12
START, END = '2023-01', '2026-10'
STABLE = re.compile(r'^(\d+)\.(\d+)(?:\.(\d+))?$')


def get(url, path):
    if os.path.exists(path):
        with io.open(path, encoding='utf-8') as f:
            return json.load(f)
    req = Request(url, headers={'User-Agent': 'cutoff-probe (github.com/dimhold/cutoff-probe)',
                                'Accept': 'application/json'})
    for i in range(4):
        try:
            data = json.loads(urlopen(req, timeout=60).read().decode('utf-8'))
            break
        except Exception as e:  # a 404 for a missing name also lands here
            if '404' in str(e):
                return None
            time.sleep(3 * (i + 1))
    else:
        return None
    with io.open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    return data


def npm_releases(name):
    d = get('https://registry.npmjs.org/' + quote(name, safe='@'),
            os.path.join(RAW, 'npm__' + name.replace('/', '__') + '.json'))
    if not d or 'time' not in d:
        return None
    allv = set((d.get('versions') or {}).keys())
    rel = {v: t for v, t in d['time'].items() if v in allv}
    return rel, allv, (d.get('dist-tags') or {}).get('latest')


def pypi_releases(name):
    d = get('https://pypi.org/pypi/%s/json' % name,
            os.path.join(RAW, 'pypi__' + name + '.json'))
    if not d:
        return None
    rel = {}
    for v, files in (d.get('releases') or {}).items():
        times = [f['upload_time_iso_8601'] for f in files
                 if f.get('upload_time_iso_8601')]
        if times:
            rel[v] = min(times)
    return rel, set(d.get('releases', {}).keys()), d['info'].get('version')


def main():
    items, fakes, meta, releases = [], [], {}, {}
    for eco, names, fn in (('npm', NPM, npm_releases),
                           ('pypi', PYPI, pypi_releases)):
        for n in names:
            r = fn(n)
            if not r:
                meta['%s:%s' % (eco, n)] = 'missing'
                continue
            rel, allv, latest = r
            releases['%s:%s' % (eco, n)] = rel
            first = {}
            for v, t in rel.items():
                m = STABLE.match(v)
                if m:
                    key = (int(m.group(1)), int(m.group(2)))
                    if key not in first or t < first[key][0]:
                        first[key] = (t, v)
            stable = sorted((t, v) for t, v in first.values()
                            if START <= t[:7] <= END)
            for t, v in stable:
                items.append({'eco': eco, 'pkg': n, 'version': v,
                              'published': t[:10], 'month': t[:7]})
            meta['%s:%s' % (eco, n)] = {'stable_in_window': len(stable),
                                        'latest': latest}
            # future versions absent from the registry on the snapshot day
            nums = [(int(STABLE.match(v).group(1)), int(STABLE.match(v).group(2)))
                    for v in allv if STABLE.match(v)]
            if nums:
                mj, mn = max(nums)
                for cand in ('%d.0.0' % (mj + 1), '%d.%d.0' % (mj, mn + 1)):
                    short = cand[:-2]
                    if cand not in allv and short not in allv:
                        fakes.append({'eco': eco, 'pkg': n, 'version': cand,
                                      'kind': 'future'})
    # spread over months: across packages, seeded, deterministic
    rnd = random.Random(20261019)
    bymonth = defaultdict(list)
    for it in items:
        bymonth[it['month']].append(it)
    chosen = []
    for mth in sorted(bymonth):
        pool = bymonth[mth]
        rnd.shuffle(pool)
        seen, pick = set(), []
        for it in pool:            # first 1 per package
            if it['pkg'] not in seen and len(pick) < PER_MONTH:
                pick.append(it)
                seen.add(it['pkg'])
        for it in pool:            # then top up if packages run short
            if it not in pick and len(pick) < PER_MONTH:
                pick.append(it)
        chosen += pick
    for i, it in enumerate(chosen):
        it['id'] = 'r%04d' % i
    for i, it in enumerate(fakes):
        it['id'] = 'f%04d' % i
    with io.open(os.path.join(HERE, 'data', 'releases.json'), 'w',
                 encoding='utf-8') as f:
        json.dump(releases, f, sort_keys=True)
    out = {'snapshot': time.strftime('%Y-%m-%d'), 'per_month': PER_MONTH,
           'window': [START, END], 'real': chosen, 'fake': fakes,
           'packages': meta,
           'pool_per_month': {m: len(v) for m, v in sorted(bymonth.items())}}
    with io.open(os.path.join(HERE, 'battery.json'), 'w',
                 encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print('real', len(chosen), 'fake', len(fakes))
    print({m: len(v) for m, v in sorted(bymonth.items())})


if __name__ == '__main__':
    main()

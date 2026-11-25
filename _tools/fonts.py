#!/usr/bin/env python3
"""Install the Google Font families the pages use, so headless Chrome draws them the way a real phone does.

Why: this workspace's proxy blocks fonts.googleapis.com, so without local copies EVERY page renders in
fallback fonts (Arial, DejaVu). Layout checks, hero screenshots and og cards are then wrong: wide fallback
letters make headlines look cut off that are fine on a phone, and hide problems that are real.

Run from the repo root:  python3 _tools/fonts.py        (first run about a minute; later runs skip what is installed)
It reads the font families from the pages' Google Fonts links, fetches only those folders from
github.com/google/fonts (sparse checkout) and copies the .ttf files to ~/.fonts/gf.
"""
import glob, os, re, shutil, subprocess, sys, urllib.parse

CACHE = os.path.expanduser('~/.cache/gfonts')
DEST = os.path.expanduser('~/.fonts/gf')


def wanted(root):
    fam = set()
    files = glob.glob(os.path.join(root, 'index.html')) + glob.glob(os.path.join(root, '*', 'index.html')) + glob.glob(os.path.join(root, '*', '*', 'index.html'))
    for f in files:
        try:
            h = open(f, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        for u in re.findall(r'https://fonts\.googleapis\.com/css2?\?[^"\')\s>]+', h):
            for m in re.finditer(r'family=([^&:]+)', u.replace('&amp;', '&')):
                fam.add(urllib.parse.unquote_plus(m.group(1)).strip())
    return fam


def installed():
    try:
        out = subprocess.run(['fc-list', ':', 'family'], capture_output=True, text=True).stdout
    except OSError:
        return set()
    names = set()
    for line in out.splitlines():
        for n in line.split(','):
            names.add(n.strip().replace('\\', '').lower())
    return names


def key(f):
    return re.sub(r'[^a-z0-9]', '', f.lower())


def run(args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def ensure(root='.', quiet=False):
    """Install what is missing. Returns the list of families that could not be installed."""
    want = wanted(root)
    have = installed()
    missing = sorted(f for f in want if f.lower() not in have)
    if not missing:
        if not quiet:
            print('fonts: all %d families already installed' % len(want))
        return []
    if not os.path.isdir(os.path.join(CACHE, '.git')):
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        r = run(['git', 'clone', '--depth', '1', '--filter=blob:none', '--no-checkout', 'https://github.com/google/fonts', CACHE])
        if r.returncode != 0:
            print('fonts: could not reach github.com/google/fonts:', r.stderr.strip()[-200:])
            return missing
    pats = []
    for f in missing:
        for lic in ('ofl', 'apache', 'ufl'):
            pats.append('/%s/%s/*.ttf' % (lic, key(f)))
    run(['git', 'sparse-checkout', 'init', '--no-cone'], cwd=CACHE)
    with open(os.path.join(CACHE, '.git', 'info', 'sparse-checkout'), 'w') as fh:
        fh.write('\n'.join(pats) + '\n')
    r = run(['git', 'checkout', 'HEAD'], cwd=CACHE)
    if r.returncode != 0:
        r = run(['git', 'read-tree', '-mu', 'HEAD'], cwd=CACHE)
    os.makedirs(DEST, exist_ok=True)
    n = 0
    for lic in ('ofl', 'apache', 'ufl'):
        for ttf in glob.glob(os.path.join(CACHE, lic, '*', '*.ttf')):
            dst = os.path.join(DEST, os.path.basename(os.path.dirname(ttf)) + '__' + os.path.basename(ttf))
            if not os.path.exists(dst):
                shutil.copyfile(ttf, dst)
                n += 1
    run(['fc-cache', '-f', os.path.expanduser('~/.fonts')])
    have = installed()
    still = sorted(f for f in want if f.lower() not in have)
    if not quiet:
        print('fonts: copied %d files; %d of %d families installed' % (n, len(want) - len(still), len(want)))
        if still:
            print('fonts: not found (pages using them fall back):', ', '.join(still))
    return still


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    ensure(root)

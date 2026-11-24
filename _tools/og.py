#!/usr/bin/env python3
"""Link-preview cards for the Code Craft demo pages.

Run from the repo root:   python3 _tools/og.py            (every page that needs one)
                          python3 _tools/og.py SLUG ...    (only these folders)
                          python3 _tools/og.py --force     (redo all)

For each concept / preview / check-up page it
  1. takes a phone screenshot of the page,
  2. renders a 1200x630 card (the phone next to the business's name) to <page dir>/og.jpg,
  3. writes the og tags into <head> between <!-- cc-og --> markers, and
  4. adds the "Want it live?" script tag (cc.js) before </body> on concept and preview pages.
A hash of the page is kept in the marker, so unchanged pages are skipped on later runs.
Needs: playwright (chromium or /usr/bin/google-chrome) and Pillow. Nothing is uploaded anywhere.
"""
import argparse, asyncio, base64, hashlib, html, io, os, re, sys

BASE = 'https://coleselig.github.io/codecraft/'
LANDING = {'auto', 'barbers', 'beauty', 'food-trucks', 'check-up', 'cleaners', 'farms', 'groomers', 'salons', 'suites', 'trades'}
SKIP = {'media', 'cc-reels', '_tools', 'clients', '.git'}
OG_RE = re.compile(r'[ \t]*<!-- cc-og[^>]*-->.*?<!-- /cc-og -->\n?', re.S)
CTA_RE = re.compile(r'[ \t]*<!-- cc-cta -->.*?<!-- /cc-cta -->\n?', re.S)
MADE_RE = re.compile(r'Concept site by\s*(?:<b>)?Code Craft Media(?:</b>)?,?\s*made for\s+(.+?)\.?\s*(?:Not live|</|This is not|Not affiliated|Prices)', re.S)

KINDS = {
    'concept': dict(kick='Website concept for', sub="It's already built. Tap to take a look.",
                    title='{n} | website concept',
                    desc='A phone-first website concept made for {n} by Code Craft Media, a UTK student-run web studio in Knoxville. Tap to take a look.',
                    alt='Phone showing the website concept made for {n}'),
    'preview': dict(kick='Website preview for', sub='Your preview is ready. Tap to take a look.',
                    title='{n} | website preview',
                    desc='The website preview for {n}, built by Code Craft Media. Tap to take a look.',
                    alt='Phone showing the website preview for {n}'),
    'audit': dict(kick='Free website check-up for', sub='What we noticed, in plain words. Tap to read it.',
                  title='Free website check-up for {n}',
                  desc='A free website check-up prepared for {n} by Code Craft Media, a UTK student-run web studio in Knoxville.',
                  alt='Phone showing the free website check-up for {n}'),
    'landing': dict(kick='Websites for Tennessee small businesses', sub='$249 one-time. No monthly fees. You own it.',
                    alt='Code Craft Media: {n}'),
}
SUBS = {'check-up': 'Send your link and get a plain-English list of what to fix. Free, no strings.'}

CARD = r'''<!doctype html><html><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0}
html,body{width:1200px;height:630px;overflow:hidden}
body{background:#1c1c1e;color:#fff;font-family:Poppins,'Helvetica Neue',Arial,sans-serif;position:relative;-webkit-font-smoothing:antialiased}
.grid{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.04) 1px,transparent 1px);background-size:44px 44px}
.glow{position:absolute;right:-150px;top:-90px;width:780px;height:780px;border-radius:50%;background:radial-gradient(closest-side,rgba(232,105,44,.46),rgba(232,105,44,.13) 55%,transparent 72%)}
.left{position:absolute;left:66px;top:54px;width:640px;bottom:50px;display:flex;flex-direction:column}
.brand{display:flex;align-items:center;gap:13px;font-weight:700;font-size:20px;letter-spacing:.09em}
.mark{width:40px;height:40px;border-radius:11px;background:#e8692c;color:#1c1c1e;display:flex;align-items:center;justify-content:center;font-size:19px;font-weight:700;letter-spacing:0}
.brand em{font-style:normal;color:#e8692c}
.mid{margin:auto 0;padding-top:6px}
.kick{font-size:28px;font-weight:500;color:#f3a57c}
.name{font-weight:700;line-height:1.05;letter-spacing:-.022em;margin-top:8px;text-wrap:balance}
.sub{font-size:27px;line-height:1.3;color:#cfcfd4;margin-top:22px}
.foot{font-size:19px;color:#94949c}
.phone{position:absolute;right:86px;top:56px;width:322px;height:690px;border-radius:48px;background:#050505;padding:11px;transform:rotate(4deg);box-shadow:0 34px 90px rgba(0,0,0,.6),0 0 0 2px #303035}
.phone img{width:100%;height:100%;object-fit:cover;object-position:top;border-radius:38px;display:block;background:#fff}
</style></head><body>
<div class="grid"></div><div class="glow"></div>
<div class="left">
  <div class="brand"><span class="mark">{&#8201;}</span><span>CODE <em>CRAFT</em> MEDIA</span></div>
  <div class="mid"><div class="kick">__KICK__</div><div class="name" id="n">__NAME__</div><div class="sub">__SUB__</div></div>
  <div class="foot">UTK student-run web studio, Knoxville TN</div>
</div>
<div class="phone"><img src="__SHOT__" alt=""></div>
<script>
const n=document.getElementById('n');let s=88;n.style.fontSize=s+'px';
const fits=()=>n.scrollHeight<=272&&n.scrollWidth<=n.clientWidth+1;
const go=()=>{while(s>34&&!fits()){s-=2;n.style.fontSize=s+'px'}document.body.dataset.ready='1'};
Promise.race([document.fonts?document.fonts.ready:Promise.resolve(),new Promise(r=>setTimeout(r,6000))]).then(go);
</script></body></html>'''


def strip_blocks(h):
    return CTA_RE.sub('', OG_RE.sub('', h))


def page_kind(rel):
    parts = rel.split('/')
    if len(parts) == 1:
        return 'landing'
    if parts[0] in SKIP or parts[0].startswith('.'):
        return None
    if parts[0] in LANDING:
        return 'landing' if len(parts) == 2 else None
    if len(parts) == 2:
        return 'concept'
    if len(parts) == 3:
        return {'preview': 'preview', 'audit': 'audit', 'v2': 'concept'}.get(parts[1])
    return None


def clean(t):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', t))).strip()


def biz_name(h, kind):
    t = re.search(r'<title>(.*?)</title>', h, re.S)
    title = clean(t.group(1)) if t else ''
    if kind == 'landing':
        h1 = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
        return re.sub(r'\s+([,.])', r'\1', clean(h1.group(1))) if h1 else title
    if kind == 'audit':
        m = re.match(r'Free website check-up for (.+)$', title)
        if m:
            return m.group(1).strip()
        h1 = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
        if h1:
            return clean(h1.group(1))
    if kind == 'concept':
        m = MADE_RE.search(h)
        if m:
            name = clean(m.group(1))
            if 1 < len(name) <= 70 and not re.search(r'Code Craft|Concept', name):
                return name
    name = re.split(r'\s[—–|·]\s|\s-\s', title)[0].strip()
    return name or title or 'your business'


def find_pages(root, only):
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if not x.startswith('.') and x not in SKIP]
        if 'index.html' in files:
            rel = os.path.relpath(os.path.join(d, 'index.html'), root).replace(os.sep, '/')
            kind = page_kind(rel)
            top = rel.split('/')[0] if '/' in rel else '.'
            if kind and (not only or top in only):
                out.append((rel, kind))
    return sorted(out)


def og_block(rel, kind, name, digest):
    k = KINDS[kind]
    e = lambda s: html.escape(s, quote=True)
    url = BASE + rel[:-len('index.html')]
    if kind == 'landing':
        return ('<!-- cc-og h=%s -->\n' % digest +
                '<meta property="og:image" content="%sog.jpg">\n' % e(url) +
                '<meta property="og:image:width" content="1200">\n'
                '<meta property="og:image:height" content="630">\n'
                '<meta property="og:image:alt" content="%s">\n' % e(k['alt'].format(n=name)) +
                '<!-- /cc-og -->\n')
    return (
        '<!-- cc-og h=%s -->\n' % digest +
        '<meta property="og:type" content="website">\n'
        '<meta property="og:site_name" content="Code Craft Media">\n'
        '<meta property="og:title" content="%s">\n' % e(k['title'].format(n=name)) +
        '<meta property="og:description" content="%s">\n' % e(k['desc'].format(n=name)) +
        '<meta property="og:url" content="%s">\n' % e(url) +
        '<meta property="og:image" content="%sog.jpg">\n' % e(url) +
        '<meta property="og:image:width" content="1200">\n'
        '<meta property="og:image:height" content="630">\n'
        '<meta property="og:image:alt" content="%s">\n' % e(k['alt'].format(n=name)) +
        '<meta name="twitter:card" content="summary_large_image">\n'
        '<!-- /cc-og -->\n')


def cta_block(kind, name):
    return ('<!-- cc-cta --><script src="/codecraft/cc.js" defer data-kind="%s" data-biz="%s"></script><!-- /cc-cta -->\n'
            % (kind, html.escape(name, quote=True)))


def inject(h, rel, kind, name, digest, cta=True):
    h = strip_blocks(h)
    i = h.lower().find('</head>')
    if i < 0:
        return None
    h = h[:i] + og_block(rel, kind, name, digest) + h[i:]
    if cta and kind in ('concept', 'preview'):
        j = h.lower().rfind('</body>')
        if j >= 0:
            h = h[:j] + cta_block(kind, name) + h[j:]
    return h


async def launch(p):
    try:
        return await p.chromium.launch(args=['--no-sandbox'])
    except Exception:
        for exe in ('/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'):
            if os.path.exists(exe):
                return await p.chromium.launch(executable_path=exe, args=['--no-sandbox'])
        raise


async def render(browser, root, rel, kind, name, quality):
    from PIL import Image
    path = os.path.join(root, rel)
    ctx = await browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    try:
        pg = await ctx.new_page()
        await pg.goto('file://' + os.path.abspath(path), wait_until='domcontentloaded', timeout=20000)
        try:
            await pg.wait_for_load_state('load', timeout=5000)
        except Exception:
            pass
        try:
            await pg.evaluate('document.fonts ? Promise.race([document.fonts.ready, new Promise(r => setTimeout(r, 3000))]) : 0')
        except Exception:
            pass
        await pg.wait_for_timeout(1300)
        shot = await pg.screenshot(type='jpeg', quality=88)
    finally:
        await ctx.close()
    k = KINDS[kind]
    sub = SUBS.get(rel.split('/')[0], k['sub']) if kind == 'landing' else k['sub']
    card = (CARD.replace('__KICK__', html.escape(k['kick'])).replace('__NAME__', html.escape(name))
            .replace('__SUB__', html.escape(sub)).replace('__SHOT__', 'data:image/jpeg;base64,' + base64.b64encode(shot).decode()))
    ctx = await browser.new_context(viewport={'width': 1200, 'height': 630}, device_scale_factor=1)
    try:
        pg = await ctx.new_page()
        await pg.set_content(card, wait_until='domcontentloaded')
        await pg.wait_for_function('document.body.dataset.ready === "1"', timeout=15000)
        await pg.wait_for_timeout(150)
        png = await pg.screenshot(type='png')
    finally:
        await ctx.close()
    im = Image.open(io.BytesIO(png)).convert('RGB')
    out = os.path.join(os.path.dirname(path), 'og.jpg')
    im.save(out, 'JPEG', quality=quality, optimize=True, progressive=True)
    return os.path.getsize(out)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('slugs', nargs='*')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--jobs', type=int, default=6)
    ap.add_argument('--quality', type=int, default=74)
    ap.add_argument('--no-cta', action='store_true')
    ap.add_argument('--check', action='store_true', help='only list the pages that need a card')
    a = ap.parse_args()
    root = os.getcwd()
    if not os.path.exists(os.path.join(root, 'cc.js')):
        sys.exit('run this from the repo root (cc.js not found here)')
    todo = []
    for rel, kind in find_pages(root, set(a.slugs)):
        h = open(os.path.join(root, rel), encoding='utf-8', errors='replace').read()
        digest = hashlib.sha1(strip_blocks(h).encode('utf-8')).hexdigest()[:10]
        cur = re.search(r'<!-- cc-og h=(\w+) -->', h)
        has_jpg = os.path.exists(os.path.join(root, os.path.dirname(rel), 'og.jpg'))
        if a.force or not (cur and cur.group(1) == digest and has_jpg):
            todo.append((rel, kind, h, digest))
    print('%d page(s) need a card' % len(todo))
    if a.check or not todo:
        for rel, *_ in todo:
            print('  ', rel)
        return
    from playwright.async_api import async_playwright
    sem = asyncio.Semaphore(max(1, a.jobs))
    done, failed, total = 0, [], 0

    async with async_playwright() as p:
        browser = await launch(p)

        async def one(rel, kind, h, digest):
            nonlocal done, total
            async with sem:
                name = biz_name(h, kind)
                try:
                    size = await render(browser, root, rel, kind, name, a.quality)
                    new = inject(h, rel, kind, name, digest, cta=not a.no_cta)
                    if new is None:
                        raise RuntimeError('no </head>')
                    with open(os.path.join(root, rel), 'w', encoding='utf-8') as f:
                        f.write(new)
                    done += 1
                    total += size
                    if done % 50 == 0:
                        print('  %d done' % done, flush=True)
                except Exception as ex:
                    failed.append((rel, str(ex)[:160]))

        await asyncio.gather(*(one(*t) for t in todo))
        await browser.close()
    print('cards written: %d (%.1f MB), failed: %d' % (done, total / 1e6, len(failed)))
    for rel, err in failed:
        print('  FAILED', rel, err)

if __name__ == '__main__':
    asyncio.run(main())

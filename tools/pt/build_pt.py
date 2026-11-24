# -*- coding: utf-8 -*-
import json, re, html as H, sys, os, glob, subprocess
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Comment

ROOT = sys.argv[1] if len(sys.argv) > 1 else '.'
DATA = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else 'tools/pt')
sys.path.insert(0, DATA)
import pt_t, pt_jobs, pt_static
os.chdir(ROOT)
SITE = 'https://meshconsulting.pl'
TPL = {'T': pt_t.HOME_T, 'EMP': pt_t.EMP_OVERRIDE, 'LEGAL': pt_t.LEGAL_PT, 'COUNTRIES': pt_t.COUNTRIES_PT,
       'JOBS': {k: list(v) for k, v in pt_jobs.J.items()}, 'EXTRA': pt_static.EXTRA}
STAT = {str(k): v for k, v in pt_static.S.items()}

def G(pl, en, es, pt): return {'pl': pl, 'en': en, 'es': es, 'pt': pt}
GROUPS = {
 'home': G('/pl/', '/en/', '/es/', '/pt/'),
 'about': G('/pl/o-nas/', '/en/about/', '/es/nosotros/', '/pt/sobre-nos/'),
 'biz': G('/pl/firmy/', '/en/business/', '/es/empresas/', '/pt/empresas/'),
 'priv': G('/pl/prywatnosc/', '/en/privacy/', '/es/privacidad/', '/pt/privacidade/'),
 'terms': G('/pl/regulamin/', '/en/terms/', '/es/terminos/', '/pt/termos/'),
 'blog': G('/pl/blog/', '/en/blog/', '/es/blog/', '/pt/blog/'),
 'a1': G('/pl/blog/zmiana-pracodawcy-karta-pobytu-polska/', '/en/blog/change-employer-poland-residence-permit/', '/es/blog/cambiar-de-empleador-polonia-permiso-de-residencia/', '/pt/blog/trocar-de-empregador-polonia-autorizacao-de-residencia/'),
 'a2': G('/pl/blog/kolumbia-wenezuela-gruzja-praca-w-polsce-sierpien-2026/', '/en/blog/colombia-venezuela-georgia-work-in-poland-august-2026/', '/es/blog/colombia-venezuela-georgia-trabajar-polonia-agosto-2026/', '/pt/blog/colombia-venezuela-georgia-trabalhar-polonia-agosto-2026/'),
 'a3': G('/pl/blog/placa-minimalna-polska-2026-2027/', '/en/blog/minimum-wage-poland-2026-2027/', '/es/blog/salario-minimo-polonia-2026-2027/', '/pt/blog/salario-minimo-polonia-2026-2027/'),
}
ES2PT = {g['es']: g['pt'] for g in GROUPS.values()}
PATH2GROUP = {}
for k, g in GROUPS.items():
    for l, p in g.items(): PATH2GROUP[p] = (k, l)

STATIC_PAGES = ['es/nosotros/index.html', 'es/privacidad/index.html', 'es/terminos/index.html', 'es/blog/index.html',
 'es/blog/cambiar-de-empleador-polonia-permiso-de-residencia/index.html',
 'es/blog/colombia-venezuela-georgia-trabajar-polonia-agosto-2026/index.html',
 'es/blog/salario-minimo-polonia-2026-2027/index.html']

def collect(path):
    b = BeautifulSoup(open(path, encoding='utf-8').read(), 'lxml')
    out = []
    for t in b.find_all(string=True):
        if isinstance(t, Comment): continue
        if t.parent.name in ('script', 'style'): continue
        x = ' '.join(t.split())
        if x and x != 'PT': out.append(x)
    for el in b.find_all(True):
        for a in ('aria-label', 'alt', 'placeholder'):
            if el.has_attr(a) and el[a].strip(): out.append(el[a].strip())
    for m in b.find_all('meta'):
        if m.get('name') in ('description', 'twitter:title', 'twitter:description') or m.get('property') in ('og:title', 'og:description'):
            out.append(m['content'])
    if b.title: out.append(b.title.get_text())
    return out

seen = {}
for p in STATIC_PAGES:
    for x in collect(p): seen.setdefault(x, 0)
ES_LIST = list(seen)
assert len(ES_LIST) == 383, len(ES_LIST)
MAP = {ES_LIST[int(i)]: v for i, v in STAT.items()}
MAP.update(TPL['EXTRA'])
jsrc = open('es/index.html', encoding='utf-8').read()
a = jsrc.index('const JOBS=['); b = jsrc.index('];', a)
JOBS_ES = json.loads(jsrc[a + 11:b + 1].replace('\n', ''))
_js = "const fs=require('fs');const s=fs.readFileSync('es/index.html','utf8');const a=s.indexOf('const T={');const b=s.indexOf('}};',a)+3;const T=eval('('+s.slice(a+8,b-1)+')');console.log(JSON.stringify(T.es))"
ES_T = json.loads(subprocess.check_output(['node', '-e', _js]).decode('utf-8'))
for k, v in ES_T.items():
    if k in TPL['T'] and '<' not in v and '{' not in v: MAP.setdefault(v, TPL['T'][k])
for j in JOBS_ES:
    t, loc, r, h, p = TPL['JOBS'][j['id']]
    MAP[j['es']['r']] = r; MAP[j['es']['h']] = h
    for a_, b_ in zip(j['es']['p'], p): MAP[a_] = b_
    MAP[j['es']['t']] = t; MAP[j['es']['loc']] = loc
    MAP[j['es']['t'] + ' — ' + j['es']['loc']] = t + ' — ' + loc

def norm(s): return ' '.join(H.unescape(s).split())
def protect(s):
    store = []
    def rep(m): store.append(m.group(0)); return '\x00%d\x00' % (len(store) - 1)
    s = re.sub(r'<(script|style)\b.*?</\1>', rep, s, flags=re.S | re.I)
    return s, store
def restore(s, store):
    return re.sub(r'\x00(\d+)\x00', lambda m: store[int(m.group(1))], s)

def translate_text(s):
    def f(m):
        t = m.group(2)
        n = norm(t)
        if n in MAP:
            lead = t[:len(t) - len(t.lstrip())]; trail = t[len(t.rstrip()):]
            return m.group(1) + lead + H.escape(MAP[n], quote=False) + trail + m.group(3)
        return m.group(0)
    s = re.sub(r'(>)([^<>]+)(<)', f, s)
    def g(m):
        n = norm(m.group(2))
        if n in MAP: return m.group(1) + H.escape(MAP[n], quote=True) + m.group(3)
        return m.group(0)
    s = re.sub(r'(\b(?:aria-label|alt|placeholder|content|title)=")([^"]*)(")', g, s)
    return s

def rewrite_links(s, es_path):
    base = SITE + es_path
    def f(m):
        h = m.group(2)
        if h.startswith(('mailto:', 'tel:', 'javascript:')) or h.startswith('#'): return m.group(0)
        u = urlparse(urljoin(base, h))
        if u.netloc and u.netloc != 'meshconsulting.pl': return m.group(0)
        if u.path in ES2PT:
            new = ES2PT[u.path] + (('#' + u.fragment) if u.fragment else '')
            return m.group(1) + new + m.group(3)
        return m.group(0)
    return re.sub(r'(<a\b[^>]*?\bhref=")([^"]*)(")', f, s)

def lang_div(group, active, style):
    names = [('pl', 'PL'), ('en', 'EN'), ('es', 'ES'), ('pt', 'PT')]
    parts = []
    for l, n in names:
        href = GROUPS[group][l]
        if style == 'button':
            parts.append('<button aria-pressed="%s" data-href="%s" data-lang="%s" type="button">%s</button>' % ('true' if l == active else 'false', href, l, n))
        else:
            parts.append('<a aria-current="%s" href="%s" hreflang="%s">%s</a>' % ('true' if l == active else 'false', href, l, n))
    sep = '\n' if style == 'button' else ''
    return '<div aria-label="Idioma / Language" class="lang" role="group">' + sep + sep.join(parts) + sep + '</div>'

LANG_RE = re.compile(r'<div[^>]*class="lang"[^>]*>.*?</div>', re.S)

def set_hreflang(s, group, xdef):
    g = GROUPS[group]
    s = re.sub(r'<link rel="alternate" hreflang="[^"]*" href="[^"]*">\s*', '', s)
    tags = ''.join('<link rel="alternate" hreflang="%s" href="%s%s">\n' % (l, SITE, g[l]) for l in ('pl', 'es', 'en', 'pt'))
    tags += '<link rel="alternate" hreflang="x-default" href="%s">\n' % xdef
    return re.sub(r'(<link rel="canonical"[^>]*>\s*)', lambda m: m.group(1) + tags, s, count=1)

def xdefault(s):
    m = re.search(r'<link rel="alternate" hreflang="x-default" href="([^"]*)"', s)
    return m.group(1) if m else SITE + '/'

def ld_translate(s, es_path, pt_path, title_es):
    def f(m):
        try: d = json.loads(m.group(2))
        except Exception: return m.group(0)
        if isinstance(d, dict):
            if d.get('inLanguage') == 'es': d['inLanguage'] = 'pt'
            if 'mainEntityOfPage' in d and isinstance(d['mainEntityOfPage'], str):
                d['mainEntityOfPage'] = d['mainEntityOfPage'].replace(es_path, pt_path)
            if d.get('@type') == 'ItemList':
                if d.get('name') in MAP: d['name'] = MAP[d['name']]
                for it in d.get('itemListElement', []):
                    if it.get('name') in MAP: it['name'] = MAP[it['name']]
            for k in ('headline', 'description'):
                v = d.get(k)
                if v in MAP: d[k] = MAP[v]
                elif k == 'headline' and v and title_es and (v + ' | Mesh Consulting') == title_es and title_es in MAP:
                    d[k] = MAP[title_es].replace(' | Mesh Consulting', '')
        return m.group(1) + json.dumps(d, ensure_ascii=False).replace('</', '<\\/') + m.group(3)
    return re.sub(r'(<script type="application/ld\+json">)(.*?)(</script>)', f, s, flags=re.S)

def patch_template(s, biz):
    T = dict(TPL['T'])
    if biz: T.update(TPL['EMP'])
    js = json.dumps(T, ensure_ascii=False).replace('</', '<\\/')
    i = s.index('const T={'); e = s.index('}};', i)
    s = s[:e] + '},pt:' + js + '};' + s[e + 3:]
    li = s.index('const LEGAL={'); BT = chr(96)
    le = s.index(BT + '};', li)
    s = s[:le] + BT + ',pt:' + BT + TPL['LEGAL'] + BT + '};' + s[le + 3:]
    pj = {k: {'t': v[0], 'loc': v[1], 'r': v[2], 'h': v[3], 'p': v[4]} for k, v in TPL['JOBS'].items()}
    ins = "\nconst PTJ=%s;JOBS.forEach(j=>{const p=PTJ[j.id];j.pt=p||j.es;j.slug.pt=j.slug.es;j.img.pt=j.img.es});" % json.dumps(pj, ensure_ascii=False)
    k = 'JOBS.forEach(j=>j.premium=j.rate>=26||j.hours>=300);'
    assert k in s; s = s.replace(k, k + ins, 1)
    cp = 'const COUNTRIES_PT=%s;\n' % json.dumps(TPL['COUNTRIES'], ensure_ascii=False)
    s = s.replace('const COUNTRIES_PL=', cp + 'const COUNTRIES_PL=', 1)
    reps = [
     ("lang=(hl==='en'||hl==='pl')?hl:'es';", "lang=(hl==='en'||hl==='pl'||hl==='pt')?hl:'es';"),
     ("if(s==='en'||s==='es'||s==='pl')lang=s", "if(s==='en'||s==='es'||s==='pl'||s==='pt')lang=s"),
     ("(lang==='pl'?COUNTRIES_PL:COUNTRIES)", "(lang==='pl'?COUNTRIES_PL:lang==='pt'?COUNTRIES_PT:COUNTRIES)"),
    ]
    for a_, b_ in reps:
        assert a_ in s, a_
        s = s.replace(a_, b_)
    ptv = {'es/ofertas/': 'es/ofertas/', 'Otro / cualquiera': 'Outro / qualquer', 'Otro': 'Outro', 'es-ES': 'pt-BR'}
    def mm(m):
        v = m.group(1)[1:-1]
        return "({es:%s,pt:'%s',en:" % (m.group(1), ptv[v])
    s, n = re.subn(r"\(\{es:('[^']*'),en:", mm, s)
    assert n >= 4, n
    Tp = T
    def tx(m):
        key = m.group(3)
        if key not in Tp: return m.group(0)
        inner = m.group(4)
        if re.search(r'<%s\b' % m.group(2), inner): return m.group(0)
        if 'data-i18n-html' in m.group(1): return m.group(1) + Tp[key] + m.group(5)
        return m.group(1) + H.escape(Tp[key], quote=False) + m.group(5)
    s = re.sub(r'(<(\w+)\b[^>]*\bdata-i18n(?:-html)?="([^"]+)"[^>]*>)(.*?)(</\2>)', tx, s, flags=re.S)
    def ph(m):
        tag = m.group(0); k = re.search(r'data-i18n-ph="([^"]+)"', tag).group(1)
        if k in Tp: tag = re.sub(r'placeholder="[^"]*"', 'placeholder="%s"' % H.escape(Tp[k], quote=True), tag)
        return tag
    s = re.sub(r'<[^>]*\bdata-i18n-ph="[^"]+"[^>]*>', ph, s)
    return s

def build_pt(group):
    g = GROUPS[group]
    src = open('.' + g['es'] + 'index.html', encoding='utf-8').read()
    title_es = re.search(r'<title>(.*?)</title>', src, re.S).group(1)
    xdef = xdefault(src)
    s = src
    s = ld_translate(s, g['es'], g['pt'], title_es)
    s, store = protect(s)
    s = translate_text(s)
    s = restore(s, store)
    s = s.replace('<html lang="es"', '<html lang="pt"', 1)
    s = re.sub(r'(<link rel="canonical" href=")[^"]*"', r'\g<1>%s%s"' % (SITE, g['pt']), s, count=1)
    s = re.sub(r'(<meta property="og:url" content=")[^"]*"', r'\g<1>%s%s"' % (SITE, g['pt']), s, count=1)
    s = s.replace('content="es_ES"', 'content="pt_BR"')
    if group in ('home', 'biz'):
        s = patch_template(s, group == 'biz')
    s = rewrite_links(s, g['es'])
    style = 'button' if 'data-lang=' in src else 'a'
    s = LANG_RE.sub(lambda m: lang_div(group, 'pt', style), s, count=1)
    s = set_hreflang(s, group, xdef)
    out = '.' + g['pt'] + 'index.html'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write(s)
    return out

def patch_other(path):
    s = open(path, encoding='utf-8').read(); o = s
    p = '/' + path.replace('\\', '/').replace('index.html', '')
    grp = PATH2GROUP.get(p)
    target = GROUPS[grp[0]]['pt'] if grp else '/pt/'
    def add(m):
        div = m.group(0)
        if 'data-lang="pt"' in div or 'hreflang="pt"' in div: return div
        if '<button' in div:
            return div.replace('</div>', '<button aria-pressed="false" data-href="%s" data-lang="pt" type="button">PT</button>\n</div>' % target, 1)
        return div.replace('</div>', '<a aria-current="false" href="%s" hreflang="pt">PT</a></div>' % target, 1)
    s = LANG_RE.sub(add, s, count=1)
    if grp and 'hreflang="pt"' not in re.sub(r'<div[^>]*class="lang".*?</div>', '', s, flags=re.S):
        tag = '<link rel="alternate" hreflang="pt" href="%s%s">\n' % (SITE, GROUPS[grp[0]]['pt'])
        if 'hreflang="x-default"' in s:
            s = re.sub(r'(<link rel="alternate" hreflang="x-default")', lambda m: tag + m.group(1), s, count=1)
        else:
            s = re.sub(r'(<link rel="canonical"[^>]*>)', lambda m: m.group(1) + '\n' + tag.strip(), s, count=1)
    if s != o: open(path, 'w', encoding='utf-8').write(s); return True
    return False

def patch_sitemap():
    s = open('sitemap.xml', encoding='utf-8').read()
    if '/pt/' in s: return
    new = []
    def f(m):
        loc = re.search(r'<loc>([^<]*)</loc>', m.group(0)).group(1)
        p = loc.replace(SITE, '')
        grp = PATH2GROUP.get(p)
        if not grp: return m.group(0)
        pt = SITE + GROUPS[grp[0]]['pt']
        link = '<xhtml:link rel="alternate" hreflang="pt" href="%s"/>' % pt
        e = re.sub(r'(<xhtml:link rel="alternate" hreflang="x-default")', lambda mm: link + mm.group(1), m.group(0), count=1)
        if grp[1] == 'es':
            ent = e.replace('<loc>%s</loc>' % loc, '<loc>%s</loc>' % pt)
            new.append(ent)
        return e
    s = re.sub(r'<url>.*?</url>', f, s, flags=re.S)
    s = s.replace('</urlset>', '\n'.join(new) + '\n</urlset>')
    open('sitemap.xml', 'w', encoding='utf-8').write(s)

if __name__ == '__main__':
    outs = [build_pt(k) for k in GROUPS]
    print('pt generadas:', len(outs))
    n = 0
    for path in glob.glob('es/**/*.html', recursive=True) + glob.glob('en/**/*.html', recursive=True) + glob.glob('pl/**/*.html', recursive=True):
        if patch_other(path): n += 1
    print('páginas parcheadas:', n)
    patch_sitemap()

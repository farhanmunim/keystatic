#!/usr/bin/env python3
"""Seed Keystatic content from a headless WordPress site via its REST API.

Usage: python3 scripts/import-wordpress.py [https://cms.farhan.app]
Needs: pip install beautifulsoup4

Mapping (WordPress -> Keystatic):
  posts -> posts, categories -> categories, tags -> tags, users -> authors,
  solutions -> services, projects -> projects, resources -> resources,
  socials -> Site Settings social links, media -> public/uploads.
Uploads follow Keystatic's layout, public/uploads/<collection>/<entry-slug>/<file>, so the
editor can preview them. Media nothing references goes to public/uploads/library/.
Re-running overwrites the imported collections. Pages and Site Settings are left alone
(Site Settings is only created if missing).
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

WP = (sys.argv[1] if len(sys.argv) > 1 else 'https://cms.farhan.app').rstrip('/')
ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / 'src' / 'content'
UPLOADS = ROOT / 'public' / 'uploads'
UMAMI = '<script defer src="https://mochi.farhan.app/script.js" data-website-id="9a60818f-ad69-4a68-94b4-cf617f22ad81"></script>'
AUTHOR = 'farhan-munim'
warnings: list[str] = []


def fetch(path: str, binary: bool = False):
    out = subprocess.run(['curl', '-sS', '-L', '-m', '120', '-f', path], capture_output=True, check=True).stdout
    return out if binary else json.loads(out)


def fetch_all(route: str):
    items, page = [], 1
    while True:
        batch = fetch(f'{WP}/wp-json/wp/v2/{route}?per_page=100&page={page}&context=view')
        items += batch
        if len(batch) < 100:
            return items
        page += 1


# ----------------------------------------------------------------- helpers
def yq(value) -> str:
    """YAML scalar (JSON strings are valid YAML)."""
    return json.dumps(value, ensure_ascii=False)


def frontmatter(fields: dict) -> str:
    lines = []
    for k, v in fields.items():
        if isinstance(v, list):
            lines.append(f'{k}:' + (' []' if not v else ''))
            lines += [f'  - {yq(i)}' if not isinstance(i, dict) else '  - ' + '\n    '.join(f'{ik}: {yq(iv)}' for ik, iv in i.items()) for i in v]
        elif k == 'date':
            lines.append(f'{k}: {v}')
        elif isinstance(v, bool):
            lines.append(f'{k}: {"true" if v else "false"}')
        else:
            lines.append(f'{k}: {yq(v)}')
    return '\n'.join(lines)


def write_entry(directory: str, slug: str, fields: dict, body: str = '', ext: str = 'mdoc'):
    d = CONTENT / directory
    d.mkdir(parents=True, exist_ok=True)
    text = frontmatter(fields)
    if ext == 'mdoc':
        text = f'---\n{text}\n---\n\n{body.strip()}\n' if body.strip() else f'---\n{text}\n---\n'
    else:
        text += '\n'
    (d / f'{slug}.{ext}').write_text(text, encoding='utf-8')


def plain(htmltext: str) -> str:
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', htmltext or ''))).strip()


def iso(date_gmt: str) -> str:
    """Keystatic's datetime wire format: YYYY-MM-DDTHH:mm, written unquoted (see frontmatter)."""
    return date_gmt[:16]


# ------------------------------------------------------------ media / links
media_by_url: dict[str, str] = {}   # source url -> local public path
media_by_id: dict[int, dict] = {}
media_bytes: dict[str, bytes] = {}  # source url (original size) -> file contents
target: list[str] = ['library']     # current upload folder, e.g. ['posts', '<slug>']
used_sources: set[str] = set()


def place(name: str, data: bytes) -> str:
    """Write a file into the current target folder and return its public path."""
    folder = UPLOADS.joinpath(*target)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(data)
    return '/uploads/' + '/'.join(target) + '/' + name


def original(url: str) -> str:
    return re.sub(r'-\d+x\d+(\.[a-z]+)$', r'\1', url)  # resized variant -> original


def upload_name(url: str) -> str:
    return unquote(Path(urlparse(url).path).name)


def local_image(url: str) -> str:
    """Copy a WordPress upload into the current entry's folder and return its public path."""
    if not url.startswith(WP + '/wp-content/uploads/'):
        return url
    base = original(url)
    if base not in media_bytes:
        try:
            media_bytes[base] = fetch(base, binary=True)
        except subprocess.CalledProcessError:
            base = url
            media_bytes[base] = fetch(url, binary=True)
    used_sources.add(base)
    return place(upload_name(base), media_bytes[base])


post_paths: dict[str, str] = {}


def rewrite_link(href: str) -> str:
    if re.match(r'https://www\.claudeusercontent\.com/.*#', href):  # broken in-page anchors from an export
        return '#' + href.split('#', 1)[1]
    if href.startswith(WP + '/'):
        path = href[len(WP):].strip('/').split('#')[0]
        if path in post_paths:
            return post_paths[path]
        if path.startswith('wp-content/uploads/'):
            return local_image(href)
    return href


# ------------------------------------------------- HTML -> Markdoc converter
def esc(text: str) -> str:
    text = text.replace('\\', '\\\\')
    text = re.sub(r'([*_`\[\]<>~])', r'\\\1', text)
    return text.replace('{%', '\\{%')


def esc_line_start(line: str) -> str:
    return re.sub(r'^(\s*)([#>+-]|\d+[.)])', lambda m: m.group(1) + '\\' + m.group(2), line)


def inline(node, in_table=False) -> str:
    return inline_children(node.children, in_table)


def inline_children(children, in_table=False) -> str:
    out = []
    for c in children:
        if isinstance(c, Comment):
            continue
        if isinstance(c, NavigableString):
            t = re.sub(r'\s+', ' ', str(c))
            t = esc(t)
            out.append(t.replace('|', '\\|') if in_table else t)
            continue
        if not isinstance(c, Tag):
            continue
        n = c.name
        if n == 'br':
            out.append(' ' if in_table else '  \n')
        elif n in ('strong', 'b', 'em', 'i', 's', 'del', 'strike'):
            inner = inline(c, in_table)
            lead = ' ' if inner.startswith(' ') else ''
            trail = ' ' if inner.endswith(' ') else ''
            inner = inner.strip()
            if inner:
                mark = {'strong': '**', 'b': '**', 'em': '*', 'i': '*'}.get(n, '~~')
                out.append(f'{lead}{mark}{inner}{mark}{trail}')
            else:
                out.append(lead + trail)
        elif n == 'code':
            code = c.get_text()
            fence = '`' * (max([len(m) for m in re.findall(r'`+', code)] or [0]) + 1)
            pad = ' ' if code.startswith('`') or code.endswith('`') else ''
            if '{%' in code:
                warnings.append('inline code containing {% — rendered as plain text with escaping')
                out.append(esc(code))
            else:
                shown = code.replace('|', '\\|') if in_table else code
                out.append(f'{fence}{pad}{shown}{pad}{fence}')
        elif n == 'a':
            href = rewrite_link(c.get('href', ''))
            text = inline(c, in_table).strip()
            href = href.replace(' ', '%20').replace('(', '%28').replace(')', '%29')
            out.append(f'[{text or href}]({href})' if href else text)
        elif n == 'img':
            out.append(image_md(c))
        elif n in ('script', 'style', 'svg'):
            continue
        else:
            out.append(inline(c, in_table))
    return ''.join(out)


def image_md(img) -> str:
    src = img.get('src', '')
    if src.startswith('svg-placeholder:'):
        return f'![{img.get("alt", "")}]({svg_files[src]})'
    alt = (img.get('alt') or '').replace('[', '(').replace(']', ')')
    return f'![{alt}]({local_image(src).replace(" ", "%20")})'


def fence(code: str, lang: str) -> str:
    code = code.strip('\n')
    ticks = '`' * max(3, max([len(m) for m in re.findall(r'`+', code)] or [0]) + 1)
    attr = ' {% process=false %}' if '{%' in code else ''
    return f'{ticks}{lang}{attr}\n{code}\n{ticks}'


def prefix(text: str, first: str, rest: str) -> str:
    lines = text.split('\n')
    return '\n'.join((first if i == 0 else rest) + l if l.strip() else l for i, l in enumerate(lines))


def list_md(node) -> str:
    ordered = node.name == 'ol'
    items = []
    for i, li in enumerate(node.find_all('li', recursive=False), 1):
        marker = f'{i}. ' if ordered else '- '
        parts, run = [], []
        for c in li.children:
            if isinstance(c, Tag) and c.name in ('ul', 'ol', 'p', 'pre', 'blockquote', 'table', 'figure', 'div'):
                if run:
                    parts.append(inline_children(run).strip())
                    run = []
                parts.append(block(c).strip())
            else:
                run.append(c)
        if run:
            parts.append(inline_children(run).strip())
        body = '\n'.join(p for p in parts if p)
        items.append(prefix(esc_line_start(body), marker, ' ' * len(marker)))
    return '\n'.join(items)


def table_md(table) -> str:
    rows = [[inline(cell, True).strip() for cell in tr.find_all(['th', 'td'])] for tr in table.find_all('tr')]
    rows = [r for r in rows if r]
    if not rows:
        return ''
    width = max(len(r) for r in rows)
    rows = [r + [''] * (width - len(r)) for r in rows]
    lines = ['| ' + ' | '.join(rows[0]) + ' |', '| ' + ' | '.join('---' for _ in range(width)) + ' |']
    lines += ['| ' + ' | '.join(r) + ' |' for r in rows[1:]]
    return '\n'.join(lines)


def block(node) -> str:
    """Convert one block-level element (or a container) to Markdown."""
    if isinstance(node, Comment):
        return ''
    if isinstance(node, NavigableString):
        t = str(node).strip()
        return esc_line_start(esc(t)) if t else ''
    n = node.name
    cls = ' '.join(node.get('class', []))
    if n in ('script', 'style', 'svg'):
        return ''
    if n == 'p':
        return esc_line_start(inline(node).strip())
    if n in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        return '#' * int(n[1]) + ' ' + inline(node).strip()
    if n in ('ul', 'ol'):
        return list_md(node)
    if n == 'pre':
        code = node.find('code')
        classes = ' '.join(node.get('class', []) + (code.get('class', []) if code else []))
        m = re.search(r'(?:language|lang)-([\w+#-]+)', classes)
        return fence((code or node).get_text(), m.group(1) if m else '')
    if n == 'blockquote':
        inner = '\n\n'.join(filter(None, (block(c) for c in node.children)))
        return prefix(inner, '> ', '> ')
    if n == 'table':
        return table_md(node)
    if n == 'hr':
        return '---'
    if n == 'img':
        return image_md(node)
    if n == 'figure':
        parts = []
        for c in node.children:
            if isinstance(c, Tag) and c.name == 'figcaption':
                parts.append('*' + inline(c).strip() + '*')
            else:
                parts.append(block(c))
        return '\n\n'.join(p for p in parts if p)
    if n == 'div' and 'alert' in cls:
        label = 'Warning' if 'warning' in cls else 'Tip' if 'success' in cls or 'tip' in cls else 'Note'
        body = inline(node).strip()
        return prefix(f'**{label}:** {body}', '> ', '> ')
    if n == 'div' and 'wp-block-button' in cls and 'buttons' in cls:
        return '\n\n'.join(inline(a).strip() and f'[{inline(a).strip()}]({rewrite_link(a.get("href", ""))})' for a in node.find_all('a'))
    if n in ('div', 'section', 'article', 'main', 'span', 'body', 'html', '[document]', 'x'):
        return '\n\n'.join(filter(None, (block(c) for c in node.children)))
    return inline(node).strip()


svg_files: dict[str, str] = {}


def extract_svgs(raw: str, slug: str) -> str:
    """Save diagram <svg> blocks as files; drop tiny 24px icons. Returns HTML with <img> placeholders."""
    count = [0]

    def sub(m):
        svg = m.group(0)
        if 'viewBox="0 0 24 24"' in svg:
            return ''
        count[0] += 1
        name = f'{slug[:40].rstrip("-")}-diagram-{count[0]}.svg'
        if 'xmlns=' not in svg[:200]:
            svg = svg.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg" font-family="system-ui, sans-serif"', 1)
        svg = svg.replace('currentColor', '#475569')
        key = f'svg-placeholder:{name}'
        svg_files[key] = place(name, svg.encode('utf-8'))
        label = (re.search(r'aria-label="([^"]*)"', svg) or [None, 'Diagram'])[1]
        return f'<img src="{key}" alt="{html.escape(label)}">'

    return re.sub(r'<svg\b.*?</svg>', sub, raw, flags=re.S)


def convert(raw: str, slug: str) -> str:
    raw = extract_svgs(raw, slug)
    soup = BeautifulSoup(raw, 'html.parser')
    md = block(soup)
    md = re.sub(r'\n{3,}', '\n\n', md).strip()
    return md


def paragraphs(text: str) -> str:
    text = html.unescape(text or '').replace('\r\n', '\n').strip()
    return '\n\n'.join(esc_line_start(esc(re.sub(r'\n', '  \n', p.strip()))) for p in re.split(r'\n{2,}', text) if p.strip())


# ------------------------------------------------------------------- main
def main():
    print('Fetching from', WP)
    cats = fetch_all('categories')
    tags = fetch_all('tags')
    users = fetch_all('users')
    media = fetch_all('media')
    posts = fetch_all('posts')
    solutions = fetch_all('solutions')
    projects = fetch_all('projects')
    resources = fetch_all('resources')
    socials = fetch_all('socials')
    print(f'posts={len(posts)} cats={len(cats)} tags={len(tags)} media={len(media)} '
          f'solutions={len(solutions)} projects={len(projects)} resources={len(resources)} socials={len(socials)}')

    # Replace the imported collections and their uploads (history stays in git).
    for d in ('posts', 'projects', 'services', 'resources', 'categories', 'tags', 'authors'):
        shutil.rmtree(CONTENT / d, ignore_errors=True)
    for d in ('posts', 'projects', 'services', 'resources', 'authors', 'site', 'library'):
        shutil.rmtree(UPLOADS / d, ignore_errors=True)
    UPLOADS.mkdir(parents=True, exist_ok=True)

    # Media library: fetch everything once; files are placed next to the entries that use them.
    for m in media:
        media_bytes[m['source_url']] = fetch(m['source_url'], binary=True)
        media_by_id[m['id']] = m
    print('downloaded', len(media), 'media files')

    def use(source_url: str) -> str:
        used_sources.add(source_url)
        return place(upload_name(source_url), media_bytes[source_url])

    cat_slug = {c['id']: c['slug'] for c in cats}
    tag_slug = {t['id']: t['slug'] for t in tags}
    for p in posts:
        post_paths[p['slug']] = f'/blog/{p["slug"]}'
    for kind, items in (('solutions', solutions), ('projects', projects), ('resources', resources)):
        for x in items:
            post_paths[f'{kind}/{x["slug"]}'] = f'/{"services" if kind == "solutions" else kind}/{x["slug"]}'

    # Categories & tags.
    for c in cats:
        if c['slug'] == 'uncategorised':
            continue
        fields = {'name': html.unescape(c['name'])}
        if c['parent']:
            fields['parent'] = cat_slug[c['parent']]
        write_entry('categories', c['slug'], fields, ext='yaml')
    for t in tags:
        write_entry('tags', t['slug'], {'name': html.unescape(t['name'])}, ext='yaml')

    # Author.
    u = users[0]
    first, _, last = html.unescape(u['name']).partition(' ')
    target[:] = ['authors', AUTHOR]
    headshot = next((m['source_url'] for m in media if m['slug'] == 'headshot'), '')
    avatar = use(headshot) if headshot else ''
    write_entry('authors', AUTHOR, {'first_name': first, 'last_name': last, 'avatar': avatar, 'social': []},
                paragraphs(u.get('description', '')))

    def cover(p):
        m = media_by_id.get(p.get('featured_media') or 0)
        if not m:
            return '', ''
        return use(m['source_url']), m.get('alt_text') or plain(m['title']['rendered'])

    def tag_list(p):
        return [tag_slug[i] for i in p.get('tags', []) if i in tag_slug]

    # Posts.
    for p in posts:
        target[:] = ['posts', p['slug']]
        img, alt = cover(p)
        cats_ = [cat_slug[i] for i in p['categories'] if i in cat_slug and cat_slug[i] != 'uncategorised']
        write_entry('posts', p['slug'], {
            'title': html.unescape(p['title']['rendered']), 'author': AUTHOR, 'cover': img, 'cover_alt': alt,
            'excerpt': plain(p['excerpt']['rendered']), 'date': iso(p['date_gmt']), 'featured': bool(p['sticky']),
            'categories': cats_, 'tags': tag_list(p),
        }, convert(p['content']['rendered'], p['slug']))

    # Solutions -> services.
    for s in solutions:
        target[:] = ['services', s['slug']]
        write_entry('services', s['slug'], {
            'title': html.unescape(s['title']['rendered']), 'author': AUTHOR, 'featured': False, 'tags': tag_list(s),
            'cover': '', 'cover_alt': '', 'summary': '',
        }, convert(s['content']['rendered'], s['slug']))

    # Projects: structured meta fields become the Markdoc body.
    for pr in projects:
        m = pr['meta_box'] or {}
        g = lambda k: html.unescape(str(m.get(k) or '')).strip()
        body = []
        if g('project_role'):
            body.append(f'**Role:** {esc(g("project_role"))}')
        for key, heading in (('project_Problem', 'The problem'), ('project_approach', 'Approach'), ('project_outcome', 'Outcome')):
            if g(key):
                body.append(f'## {heading}\n\n{paragraphs(g(key))}')
        kpis = [f'- **{esc(g(f"project_kpi_{i}"))}** {esc(g(f"project_kpi_caption_{i}"))}'.rstrip() for i in (1, 2, 3) if g(f'project_kpi_{i}')]
        if kpis:
            body.append('## Key figures\n\n' + '\n'.join(kpis))
        if g('project_source_link'):
            body.append(f'**Source code:** [{g("project_source_link_label") or g("project_source_link")}]({g("project_source_link")})')
        write_entry('projects', pr['slug'], {
            'title': html.unescape(pr['title']['rendered']), 'author': AUTHOR, 'featured': False, 'tags': tag_list(pr),
            'cover': '', 'cover_alt': '', 'summary': g('project_excerpt'), 'url': g('project_link'), 'attachment': '',
        }, '\n\n'.join(body))

    # Resources.
    for r in resources:
        m = r['meta_box'] or {}
        body = '*This is a referral link.*' if str(m.get('resource_referral')) == '1' else ''
        write_entry('resources', r['slug'], {
            'title': html.unescape(r['title']['rendered']), 'author': AUTHOR, 'featured': False, 'tags': tag_list(r),
            'cover': '', 'cover_alt': '', 'description': html.unescape(m.get('resource_excerpt') or ''),
            'url': m.get('resource_link') or '', 'attachment': '',
        }, body)

    # Site settings.
    platforms = {'github': 'GitHub', 'linkedin': 'LinkedIn', 'youtube': 'YouTube', 'buy-me-a-coffee': 'Buy Me a Coffee',
                 'x': 'X', 'twitter': 'X', 'instagram': 'Instagram', 'bluesky': 'Bluesky', 'mastodon': 'Mastodon'}
    social = [{'platform': platforms.get(s['slug'], 'Other'), 'url': (s['meta_box'] or {}).get('social_link', ''), 'handle': ''}
              for s in socials]
    target[:] = ['site']
    mid = lambda slug: next((use(m['source_url']) for m in media if m['slug'] == slug), '')
    site_file = CONTENT / 'settings' / 'site.yaml'
    if site_file.exists():
        print('Site Settings exists; leaving it alone (images placed in public/uploads/site/)')
        mid('favicon-2'), mid('banner')
    site = {
        'name': html.unescape(fetch(f'{WP}/wp-json/')['name']), 'tagline': '',
        'description': u.get('description', ''), 'logo': '', 'favicon': mid('favicon-2'), 'share_image': mid('banner'),
        'footer_text': f'© 2026 {html.unescape(u["name"])}', 'social': social, 'analytics_url': '',
        'noindex': True, 'head_html': UMAMI, 'footer_html': '',
    }
    if not site_file.exists():
        site_file.parent.mkdir(parents=True, exist_ok=True)
        site_file.write_text(frontmatter(site) + '\n', encoding='utf-8')

    # Anything in the WordPress media library that no entry uses.
    target[:] = ['library']
    unused = [m for m in media if m['source_url'] not in used_sources]
    for m in unused:
        use(m['source_url'])
    print(f'{len(unused)} unreferenced media files kept in public/uploads/library/')

    print('done;', len(set(warnings)), 'warning kinds')
    for w in sorted(set(warnings)):
        print('  warning:', w)


if __name__ == '__main__':
    main()

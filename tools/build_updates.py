#!/usr/bin/env python3
"""Build the site-wide Updates page and keep every dated marker in step.

One list, data/updates.json, holds every change made to the regulation
chapters: what the page said, what it says now, when, and the source.
This script

  1. checks the list itself;
  2. checks it against the chapters: every update has a marker in its chapter
     and every marker is on the list; each marker shows the date and the kind
     the list gives it; each "Updated" link leads to its own entry; no id is
     used twice; the banner shows the date and the count;
  3. checks the "law as of" date in nav-inject.js and the cards on index.html;
  4. builds updates.html;
  5. rebuilds the tables inside docs/regulation-updates-2026-11.md.

It keeps three things up to date by itself: the count in each chapter banner,
the total on index.html, and the spoken name of each "Updated" link.

What it cannot check: whether a sentence about the law is right, and whether a
"said before" text is what the page really said. Those are checked by reading
the source and the earlier version, and recorded in the docs note.

Run from the repo root:   python3 tools/build_updates.py
Check only, write nothing: python3 tools/build_updates.py --check
Exit code 1 means something is out of step; the message says what, and no file
is written. tools/test_build_updates.py tests this script.
"""
import html
from html.parser import HTMLParser
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK_ONLY = '--check' in sys.argv

CHAPTERS = {
    5: ('05-compliance-gdpr.html', 'Compliance and GDPR'),
    7: ('07-eu-regulations.html', 'EU Regulations'),
    8: ('08-compliance-mechanisms.html', 'Compliance Mechanisms'),
    9: ('09-ai-act-data-vault.html', 'AI Act and Data Vault'),
    13: ('13-compliance-self-test.html', 'Compliance Self-Test'),
}
KIND = {
    'law': 'The law changed',
    'fix': 'Correction',
    'new': 'Added',
    'word': 'Wording',
    'news': 'Events since publication',
}
KIND_HELP = {
    'law': 'The page was right when written. The law has changed since.',
    'fix': 'The page was wrong or imprecise from the start.',
    'new': 'Something new in the law that the page did not cover.',
    'word': 'A term was made consistent across the site.',
    'news': 'Something the page announced or expected has since happened.',
}
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']

problems = []
pending = {}   # files to write once everything has been checked


def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


def write(rel, text):
    """Queue a file for writing. With --check, a file that would change is reported instead."""
    path = os.path.join(ROOT, rel)
    old = read(rel) if os.path.exists(path) else None
    if old == text:
        return
    if CHECK_ONLY:
        problems.append(f'{rel} is out of date: run tools/build_updates.py')
    else:
        pending[rel] = text


def long_date(iso):
    y, m, d = iso.split('-')
    return f'{int(d)} {MONTHS[int(m) - 1]} {y}'


def short_date(iso):
    y, m, d = iso.split('-')
    return f'{int(d)} {MONTHS[int(m) - 1][:3]} {y}'


def e(s):
    return html.escape(s, quote=True)


# ── reading a page ───────────────────────────────────────────────────────────
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}


class Node:
    """One element of a page: tag, attributes, children (elements and strings)."""

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.children = tag, attrs, parent, []

    def classes(self):
        return (self.attrs.get('class') or '').split()

    def text(self, skip=None):
        """The words inside, on one line. skip: leave out elements that carry this class."""
        parts = [c if isinstance(c, str) else ('' if skip and skip in c.classes() else c.text(skip)) for c in self.children]
        return ' '.join(''.join(parts).split())

    def walk(self):
        for c in self.children:
            if isinstance(c, Node):
                yield c
                yield from c.walk()

    def find(self, tag=None, cls=None):
        return [n for n in self.walk() if (tag is None or n.tag == tag) and (cls is None or cls in n.classes())]

    def inside(self, test):
        n = self.parent
        while n is not None:
            if test(n):
                return n
            n = n.parent
        return None

    def hidden(self, own_only=False):
        """True when the element is kept off the page by markup: its own, or (unless own_only) that of
        anything around it. Chapters fold answers away with an inline style until the reader opens them,
        so for a marker only its own markup counts."""
        n = self
        while n is not None:
            style = (n.attrs.get('style') or '').replace(' ', '').lower()
            if n.tag == 'template' or 'hidden' in n.attrs or 'display:none' in style:
                return True
            n = None if own_only else n.parent
        return False


class Dom(HTMLParser):
    """Python's own HTML reader, so quotes, capitals, attribute order and comments are handled as a browser would."""

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.root = self.cur = Node('#root', {}, None)
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: (v if v is not None else '') for k, v in attrs}, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, {k: (v if v is not None else '') for k, v in attrs}, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def finish():
    """Report and stop. Files are written only when nothing is out of step."""
    if problems:
        print('\nOUT OF STEP' + ('' if CHECK_ONLY else ' (nothing was written)') + ':')
        for p in problems:
            print('  -', p)
        sys.exit(1)
    for rel, text in pending.items():
        path = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f'{rel}: written')
    print(f'OK: {len(updates)} updates across chapters {sorted(by_chapter)}; law as of {data["law_as_of_label"]}')
    sys.exit(0)


updates, by_chapter = [], {}
try:
    data = json.loads(read('data/updates.json'))
except ValueError as err:
    problems.append(f'data/updates.json is not valid JSON: {err}')
    data = {'law_as_of_label': '?'}
    finish()
for key in ('law_as_of', 'law_as_of_label', 'law_as_of_short', 'first_published', 'sources', 'updates'):
    if key not in data:
        problems.append(f'data/updates.json: "{key}" is missing')
if problems:
    data.setdefault('law_as_of_label', '?')
    finish()
SRC = data['sources']
updates = data['updates']
for u in updates:
    u.setdefault('date', data['law_as_of'])

# ── 1. the list itself ───────────────────────────────────────────────────────
for u in updates:
    uid = u.get('id', '(no id)')
    missing = [k for k in ('id', 'chapter', 'kind', 'title', 'was', 'now', 'where', 'sources') if k not in u]
    if missing:
        problems.append(f'{uid}: the entry lacks {", ".join(missing)}')
        continue
    shape = []
    if not isinstance(u['chapter'], int):
        shape.append('"chapter" must be a number')
    if any(not isinstance(u[k], str) or not u[k].strip() for k in ('id', 'kind', 'title', 'was', 'now', 'where')):
        shape.append('"id", "kind", "title", "was", "now" and "where" must be text')
    if not isinstance(u['sources'], list) or any(not isinstance(s, list) or len(s) != 2 for s in u['sources']):
        shape.append('"sources" must be a list of [key, place] pairs')
    if not re.fullmatch(r'\d{4}-\d\d-\d\d', str(u['date'])):
        shape.append('"date" must look like 2026-11-20')
    if 'law_date' in u and not re.fullmatch(r'\d{1,2} (?:%s) \d{4}' % '|'.join(MONTHS), str(u['law_date'])):
        shape.append('"law_date" must look like 27 July 2026')
    if shape:
        problems.append(f'{uid}: ' + '; '.join(shape))
        continue
    by_chapter.setdefault(u['chapter'], []).append(u)
    if u['kind'] not in KIND:
        problems.append(f"{uid}: unknown kind {u['kind']}")
    for key, _pin in u['sources']:
        if key not in SRC:
            problems.append(f'{uid}: unknown source {key}')
    if not re.fullmatch(r'u%02d-\d\d' % u['chapter'], uid):
        problems.append(f"{uid}: id does not match chapter {u['chapter']}")
    if u['chapter'] not in CHAPTERS:
        problems.append(f"{uid}: chapter {u['chapter']} is not a regulation chapter known to this script")
ids = [u.get('id') for u in updates]
if len(ids) != len(set(ids)):
    problems.append('duplicate ids in data/updates.json')
for c in data.get('unchanged', []):
    if any(k not in c for k in ('chapter', 'claim', 'source', 'pin')) or c.get('source') not in SRC:
        problems.append(f'data/updates.json: an "unchanged" row lacks a field or names an unknown source: {str(c)[:80]}')
if problems:
    finish()   # the rest needs a sound list
by_id = {u['id']: u for u in updates}
total = len(updates)


def kind_label(u, short):
    """The kind as shown to the reader. With a law date: "The law changed on 27 Jul 2026", "Added to the law on ..."."""
    if not u.get('law_date'):
        return KIND[u['kind']]
    d, m, y = u['law_date'].split()
    lead = 'Added to the law' if u['kind'] == 'new' else KIND[u['kind']]
    return f'{lead} on {d} {m[:3] if short else m} {y}'


# ── 2. the list against the chapters ─────────────────────────────────────────
UID = re.compile(r'u\d\d-\d\d')
CHIP = re.compile(r'<a class="dvf-upd-chip" href="\.\./updates\.html#(u\d\d-\d\d)"(?: aria-label="[^"]*")? title="')


def chip_with_label(m):
    u = by_id.get(m.group(1))
    label = f' aria-label="Updated: {e(u["title"])}"' if u else ''
    return f'<a class="dvf-upd-chip" href="../updates.html#{m.group(1)}"{label} title="'


for no, (fname, _title) in CHAPTERS.items():
    rel = f'chapters/{fname}'
    listed = {u['id'] for u in by_chapter.get(no, [])}
    n = len(listed)
    # what this script keeps up to date in a chapter: the banner count, and a spoken name for each "Updated" link
    t = re.sub(r'<span data-upd-count>\d+</span>', f'<span data-upd-count>{n}</span>', read(rel))
    t = CHIP.sub(chip_with_label, t)
    write(rel, t)
    dom = Dom(t).root

    seen = {}
    for node in dom.walk():
        if 'id' in node.attrs:
            seen[node.attrs['id']] = seen.get(node.attrs['id'], 0) + 1
    for i in sorted(i for i, c in seen.items() if c > 1):
        problems.append(f'{rel}: the id "{i}" is used {seen[i]} times')

    markers = [x for x in dom.walk() if 'data-upd' in x.attrs]
    anchors = {x.attrs['data-upd'] for x in markers if x.attrs.get('id') == x.attrs['data-upd']}
    marked = {x.attrs['data-upd'] for x in markers}
    for uid in sorted(listed - anchors):
        problems.append(f'{rel}: update {uid} is on the list but has no marker with that id')
    for uid in sorted(marked - listed):
        problems.append(f'{rel}: marker {uid} is in the chapter but not on the list')
    for x in dom.walk():
        if UID.fullmatch(x.attrs.get('id', '')) and 'data-upd' not in x.attrs:
            problems.append(f'{rel}: an element has the id {x.attrs["id"]} but is not a marker (no data-upd)')

    for x in markers:
        uid = x.attrs['data-upd']
        u = by_id.get(uid)
        if u is None or uid not in listed:
            continue   # reported above
        block, inline = 'dvf-upd' in x.classes(), 'dvf-upd-i' in x.classes()
        if not (block or inline):
            problems.append(f'{rel}: marker {uid} is neither a dvf-upd block nor a dvf-upd-i span')
            continue
        if UID.fullmatch(x.attrs.get('id', '')) and x.attrs['id'] != uid:
            problems.append(f'{rel}: a marker has id {x.attrs["id"]} but belongs to {uid}')
        if x.hidden(own_only=True) or x.inside(lambda p: p.tag == 'template'):
            problems.append(f'{rel}: marker {uid} is hidden')
        if block:
            want_tag, want_kind = 'Updated ' + short_date(u['date']), kind_label(u, short=True)
            tag = [s.text() for s in x.find('span', 'dvf-upd-tag') if s.inside(lambda p: p is x or 'data-upd' in p.attrs) is x]
            kind = [s.text() for s in x.find('span', 'dvf-upd-kind') if s.inside(lambda p: p is x or 'data-upd' in p.attrs) is x]
            if tag != [want_tag]:
                problems.append(f'{rel}: marker {uid} should be headed "{want_tag}", found {tag}')
            if kind != [want_kind]:
                problems.append(f'{rel}: marker {uid} should be labelled "{want_kind}", found {kind}')
            if not any(b.text('dvf-sr') for b in x.find('div', 'dvf-upd-now')):
                problems.append(f'{rel}: marker {uid} has no new text (dvf-upd-now)')
        elif not any(c.text('dvf-sr') for c in x.find('ins') + x.find('del')):
            problems.append(f'{rel}: marker {uid} shows neither new nor earlier text')

    for a in dom.find('a'):
        href = a.attrs.get('href', '')
        m = re.fullmatch(r'\.\./updates\.html#(u\d\d-\d\d)', href)
        if m and m.group(1) not in by_id:
            problems.append(f'{rel}: a link points at {href}, which is not on the list')
        if 'dvf-upd-chip' in a.classes():
            owner = a.inside(lambda p: 'data-upd' in p.attrs)
            uid = owner.attrs['data-upd'] if owner else None
            u = by_id.get(uid)
            if u is None:
                problems.append(f'{rel}: an "Updated" link sits outside every marker' if owner is None
                                else f'{rel}: an "Updated" link sits in marker {uid}, which is not on the list')
                continue
            if href != f'../updates.html#{uid}':
                problems.append(f'{rel}: the "Updated" link of {uid} points at {href}')
            if not a.attrs.get('title', '').startswith('Updated ' + short_date(u['date'])):
                problems.append(f'{rel}: the "Updated" link of {uid} should say "Updated {short_date(u["date"])}" in its title')
            if a.attrs.get('aria-label') != f'Updated: {u["title"]}':
                problems.append(f'{rel}: the "Updated" link of {uid} has no spoken name; write it as the other links are written')

    if listed:
        if not any(l.attrs.get('href', '').endswith('assets/updates.css') for l in dom.find('link')):
            problems.append(f'{rel}: has updates but does not load assets/updates.css')
        banner = [x for x in dom.walk() if x.attrs.get('id') == 'law-review']
        if not banner or banner[0].hidden():
            problems.append(f'{rel}: has updates but no visible banner')
        else:
            shown = re.findall(r'\d{1,2} (?:%s) \d{4}' % '|'.join(MONTHS), banner[0].text())
            if not shown or any(d != data['law_as_of_label'] for d in shown):
                problems.append(f'{rel}: banner does not show {data["law_as_of_label"]} throughout, found {shown}')
            if [s.text() for s in banner[0].find('span') if 'data-upd-count' in s.attrs] != [str(n)]:
                problems.append(f'{rel}: banner should show the count {n}')

# ── 3. the navigation and the home page ──────────────────────────────────────
nav = read('nav-inject.js')
m = re.search(r"var LAW_AS_OF = '([^']+)';", nav)
if not m or m.group(1) != data['law_as_of_short']:
    problems.append(f"nav-inject.js: LAW_AS_OF should be '{data['law_as_of_short']}'")

# the navigation shows the law date on exactly the regulation chapters
lm = re.search(r'var LAW_CHAPTERS = \{([^}]*)\};', nav)
law_chapters = {int(x) for x in re.findall(r'(\d+)\s*:\s*true\b', lm.group(1))} if lm else set()
if law_chapters != set(CHAPTERS):
    problems.append(f'nav-inject.js: LAW_CHAPTERS is {sorted(law_chapters)}, expected {sorted(CHAPTERS)}')

idx = re.sub(r'<span data-upd-total>\d+</span>', f'<span data-upd-total>{total}</span>', read('index.html'))
write('index.html', idx)
home = Dom(idx).root
strip = home.find(cls='law-strip')
if len(strip) != 1 or strip[0].hidden():
    problems.append('index.html: expected one visible "law as of" strip')
else:
    if data['law_as_of_label'] not in strip[0].text():
        problems.append(f'index.html: does not show {data["law_as_of_label"]}')
    if [s.text() for s in strip[0].find('span') if 'data-upd-total' in s.attrs] != [str(total)]:
        problems.append(f'index.html: the strip should show the total {total}')

# every chapter with updates has exactly one visible card, linking to its file and carrying one tag dated with the
# chapter's newest update; no other card carries such a tag, and none sits outside the cards
cards = {}
tags_in_cards = []
for a in home.find('a', 'chapter-card'):
    href = a.attrs.get('href', '')
    m = re.fullmatch(r'(?:\./)?(chapters/(\d\d)-[^/#?]+\.html)(?:[#?].*)?', href)
    if not m:
        problems.append(f'index.html: a chapter card links to "{href}", not to a chapter file')
        continue
    no = int(m.group(2))
    cards.setdefault(no, []).append(a)
    if not os.path.exists(os.path.join(ROOT, m.group(1))):
        problems.append(f'index.html: the card of chapter {no} links to {href}, which does not exist')
    if a.hidden():
        problems.append(f'index.html: the card of chapter {no} is hidden')
    marked_spans = [s for s in a.walk() if 'tag-updated' in s.classes()]
    tags_in_cards.extend(marked_spans)
    good = [s.text() for s in marked_spans if s.tag == 'span' and 'card-tag' in s.classes() and not s.hidden()]
    if no in by_chapter:
        want = 'Updated ' + short_date(max(u['date'] for u in by_chapter[no]))
        if good != [want] or len(marked_spans) != 1:
            problems.append(f'index.html: the card of chapter {no} should carry one visible tag "{want}" '
                            f'(a span with the classes card-tag and tag-updated), found {[s.text() for s in marked_spans]}')
    elif marked_spans:
        problems.append(f'index.html: the card of chapter {no} has an "Updated" tag but no updates')
for no in sorted(by_chapter):
    if no not in cards:
        problems.append(f'index.html: chapter {no} has updates but no card for it was found on the home page')
    elif len(cards[no]) > 1:
        problems.append(f'index.html: chapter {no} has {len(cards[no])} cards, expected one')
    elif re.split(r'[#?]', cards[no][0].attrs.get('href', ''))[0].split('/')[-1] != CHAPTERS[no][0]:
        problems.append(f'index.html: the card of chapter {no} should link to chapters/{CHAPTERS[no][0]}')
if any(s not in tags_in_cards for s in home.walk() if 'tag-updated' in s.classes()):
    problems.append('index.html: an "Updated" tag sits outside every chapter card')


# ── 4. updates.html ──────────────────────────────────────────────────────────
def source_links(u):
    out = []
    for key, pin in u['sources']:
        s = SRC[key]
        out.append(f'<li><a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["label"])}</a>'
                   + (f' <span class="up-pin">{e(pin)}</span>' if pin else '') + '</li>')
    if not out:
        out.append('<li>No legal source: this is a change to the site itself.</li>')
    return '\n            '.join(out)


def card(u):
    fname = CHAPTERS[u['chapter']][0]
    kind = e(kind_label(u, short=False))
    return f'''
      <article class="dvf-upd up-card" id="{u['id']}">
        <div class="dvf-upd-head"><span class="dvf-upd-tag">Updated {short_date(u['date'])}</span><span class="dvf-upd-kind" title="{e(KIND_HELP[u['kind']])}">{kind}</span></div>
        <h4>{e(u['title'])}</h4>
        <div class="up-pair">
          <div class="up-was"><span class="up-label">Before</span><p>{e(u['was'])}</p></div>
          <div class="up-now"><span class="up-label">Now</span><p>{e(u['now'])}</p></div>
        </div>
        <div class="up-foot">
          <div class="up-src"><span class="up-label">Source</span>
          <ul>
            {source_links(u)}
          </ul></div>
          <a class="up-open" href="chapters/{fname}#{u['id']}">See it in chapter {u['chapter']} &rarr;</a>
        </div>
        <p class="up-where">Where: {e(u['where'])}</p>
      </article>'''


dates = sorted({u['date'] for u in updates}, reverse=True)
body = []
seen_chapters = set()   # the #chN anchor goes on a chapter's newest group, whatever its date
for d in dates:
    day = [u for u in updates if u['date'] == d]
    body.append(f'\n  <section class="up-day" id="d{d}">\n    <h2><span class="up-day-date">{long_date(d)}</span>'
                f'<span class="up-day-n">{len(day)} updates</span></h2>')
    for no in sorted({u['chapter'] for u in day}):
        fname, title = CHAPTERS[no]
        chunk = [u for u in day if u['chapter'] == no]
        first = '' if no in seen_chapters else ' id="ch%d"' % no
        seen_chapters.add(no)
        body.append(f'\n    <div class="up-chapter"{first}>\n      <h3 class="up-chapter-title">'
                    f'<a href="chapters/{fname}">Chapter {no} &middot; {e(title)}</a>'
                    f'<span>{len(chunk)} updates</span></h3>')
        body.extend(card(u) for u in chunk)
        body.append('\n    </div>')
    body.append('\n  </section>')

jump = ' '.join(
    f'<a href="#ch{no}">Chapter {no} <span>{len(by_chapter[no])}</span></a>'
    for no in sorted(by_chapter))

kinds_used = [k for k in KIND if any(u['kind'] == k for u in updates)]
legend = '\n      '.join(
    f'<li><span class="dvf-upd-kind">{KIND[k]}</span> {e(KIND_HELP[k])} '
    f'<span class="up-count">{sum(1 for u in updates if u["kind"] == k)}</span></li>'
    for k in kinds_used)

unchanged = '\n      '.join(
    f'<li><span class="up-ch">Ch. {c["chapter"]}</span> {e(c["claim"])} '
    f'<a href="{e(SRC[c["source"]]["url"])}" target="_blank" rel="noopener">{e(c["pin"])}</a></li>'
    for c in data.get('unchanged', []))

PAGE = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Updates — Data Vault Foundations</title>
<meta name="description" content="Every change made to the regulation chapters of Data Vault Foundations, with the date, the earlier text and the official source. Law as of {data['law_as_of_label']}.">
<!-- Generated by tools/build_updates.py from data/updates.json. Do not edit by hand. -->
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800&family=Exo+2:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/updates.css">
<style>
*, *::before, *::after {{ margin: 0; padding: 0; box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{ font-family: 'Exo 2', -apple-system, sans-serif; background: #030810; color: #e2e8f0; line-height: 1.75; font-size: 16px; min-height: 100vh; overflow-x: hidden;
  background-image: radial-gradient(ellipse 80% 50% at 50% -10%, rgba(168, 85, 247, 0.10), transparent 70%), radial-gradient(ellipse 60% 40% at 90% 10%, rgba(0, 180, 255, 0.06), transparent 70%); background-attachment: fixed; }}
a {{ color: #00b4ff; }}
.up-top {{ position: sticky; top: 0; z-index: 50; height: 48px; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; background: rgb(3, 8, 16); border-bottom: 1px solid rgba(0, 180, 255, 0.15); font-family: 'Orbitron', monospace; }}
.up-top a {{ color: #00b4ff; text-decoration: none; font-size: 11px; letter-spacing: 0.08em; }}
.up-top a:hover {{ color: #4dd4ff; }}
.up-top .up-top-here {{ color: #c084fc; font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; }}
.up-wrap {{ max-width: 860px; margin: 0 auto; padding: 56px 28px 120px; }}
.up-eyebrow {{ font-family: 'Orbitron', monospace; font-size: 11px; font-weight: 600; letter-spacing: 0.22em; text-transform: uppercase; color: #c084fc; margin-bottom: 16px; }}
h1 {{ font-family: 'Orbitron', sans-serif; font-size: 38px; font-weight: 700; line-height: 1.15; color: #f8fafc; letter-spacing: 0.02em; margin-bottom: 18px; }}
.up-lede {{ font-size: 17px; color: #94a3b8; max-width: 660px; }}
.up-lede strong {{ color: #f8fafc; font-weight: 600; }}
.up-asof {{ display: flex; flex-wrap: wrap; gap: 14px; margin: 32px 0 14px; }}
.up-stat {{ flex: 1 1 180px; background: rgba(8, 20, 42, 0.82); border: 1px solid rgba(168, 85, 247, 0.28); border-radius: 14px; padding: 16px 20px; }}
.up-stat-num {{ font-family: 'Orbitron', sans-serif; font-size: 22px; font-weight: 700; color: #f8fafc; line-height: 1.2; }}
.up-stat-label {{ font-family: 'Orbitron', monospace; font-size: 9px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: #c084fc; margin-top: 6px; }}
.up-jump {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 22px 0 0; }}
.up-jump a {{ font-family: 'Orbitron', monospace; font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; text-decoration: none; color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); background: rgba(168, 85, 247, 0.08); border-radius: 20px; padding: 8px 14px; }}
.up-jump a:hover {{ background: rgba(168, 85, 247, 0.18); color: #e9d5ff; }}
.up-jump a span {{ color: #94a3b8; margin-left: 6px; }}
.up-how {{ margin: 34px 0 0; padding: 20px 24px; background: rgba(8, 20, 42, 0.82); border: 1px solid rgba(0, 180, 255, 0.12); border-radius: 14px; }}
.up-how h2 {{ font-family: 'Orbitron', monospace; font-size: 10px; font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase; color: #94a3b8; margin-bottom: 10px; }}
.up-how p {{ font-size: 15px; color: #94a3b8; margin-bottom: 10px; }}
.up-how ul {{ list-style: none; }}
.up-how li {{ font-size: 14.5px; color: #94a3b8; padding: 5px 0; }}
.up-how li .dvf-upd-kind {{ display: inline-block; min-width: 190px; }}
.up-count {{ font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #c084fc; margin-left: 6px; }}
.up-day {{ margin-top: 64px; }}
.up-day > h2 {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 16px; padding-bottom: 14px; border-bottom: 1px solid rgba(168, 85, 247, 0.28); }}
.up-day-date {{ font-family: 'Orbitron', sans-serif; font-size: 24px; font-weight: 600; color: #f8fafc; }}
.up-day-n {{ font-family: 'Orbitron', monospace; font-size: 10px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: #c084fc; }}
.up-chapter {{ margin-top: 40px; scroll-margin-top: 70px; }}
.up-chapter-title {{ display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 6px 16px; font-family: 'Orbitron', sans-serif; font-size: 15px; font-weight: 600; letter-spacing: 0.02em; margin-bottom: 6px; }}
.up-chapter-title a {{ color: #f8fafc; text-decoration: none; }}
.up-chapter-title a:hover {{ color: #c084fc; }}
.up-chapter-title span {{ font-family: 'Orbitron', monospace; font-size: 9px; letter-spacing: 0.14em; text-transform: uppercase; color: #64748b; }}
.up-card {{ padding: 18px 22px 16px 24px; scroll-margin-top: 70px; }}
.up-card h4 {{ font-family: 'Exo 2', sans-serif; font-size: 18px; font-weight: 600; line-height: 1.4; color: #f8fafc; margin: 2px 0 12px; }}
.up-pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
.up-was, .up-now {{ padding: 12px 14px; border-radius: 10px; }}
.up-was {{ background: rgba(2, 6, 14, 0.5); border-left: 2px solid rgba(148, 163, 184, 0.3); }}
.up-now {{ background: rgba(168, 85, 247, 0.07); border-left: 2px solid #a855f7; }}
.up-was p {{ font-size: 14.5px; line-height: 1.65; color: #8b98ad; }}
.up-now p {{ font-size: 14.5px; line-height: 1.65; color: #e2e8f0; }}
.up-label {{ display: block; font-family: 'Orbitron', monospace; font-size: 8px; font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase; color: #64748b; margin-bottom: 4px; }}
.up-now .up-label {{ color: #c084fc; }}
.up-foot {{ display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 12px 20px; margin-top: 14px; }}
.up-src {{ flex: 1 1 320px; min-width: 0; }}
.up-src ul {{ list-style: none; }}
.up-src li {{ font-size: 13.5px; line-height: 1.6; color: #94a3b8; overflow-wrap: anywhere; }}
.up-src a {{ color: #c084fc; text-underline-offset: 3px; }}
.up-pin {{ color: #94a3b8; }}
.up-pin::before {{ content: '\\2014\\00a0'; color: #475569; }}
.up-open {{ font-family: 'Orbitron', monospace; font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; text-decoration: none; color: #00b4ff; border: 1px solid rgba(0, 180, 255, 0.25); border-radius: 8px; padding: 9px 14px; white-space: nowrap; }}
.up-open:hover {{ background: rgba(0, 180, 255, 0.08); border-color: rgba(0, 180, 255, 0.5); }}
.up-where {{ font-size: 12.5px; color: #64748b; margin-top: 10px; }}
.up-same {{ margin-top: 72px; }}
.up-same h2 {{ font-family: 'Orbitron', sans-serif; font-size: 20px; font-weight: 600; color: #f8fafc; margin-bottom: 8px; }}
.up-same > p {{ font-size: 15px; color: #94a3b8; margin-bottom: 14px; max-width: 660px; }}
.up-same ul {{ list-style: none; }}
.up-same li {{ font-size: 14.5px; line-height: 1.65; color: #94a3b8; padding: 10px 0; border-bottom: 1px solid rgba(0, 180, 255, 0.08); }}
.up-same li a {{ color: #c084fc; white-space: nowrap; }}
.up-ch {{ font-family: 'Orbitron', monospace; font-size: 9px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #22c55e; margin-right: 8px; }}
.up-end {{ margin-top: 64px; padding-top: 24px; border-top: 1px solid rgba(0, 180, 255, 0.1); font-size: 13.5px; color: #64748b; }}
.up-end a {{ color: #94a3b8; }}
@media (max-width: 640px) {{
  .up-top {{ padding: 0 12px; }}
  .up-top a {{ font-size: 10px; }}
  .up-wrap {{ padding: 36px 16px 90px; }}
  h1 {{ font-size: 28px; }}
  .up-lede {{ font-size: 15.5px; }}
  .up-pair {{ grid-template-columns: 1fr; }}
  .up-card {{ padding: 14px 14px 12px 18px; }}
  .up-card h4 {{ font-size: 16.5px; }}
  .up-day-date {{ font-size: 20px; }}
  .up-how {{ padding: 16px 16px; }}
  .up-how li .dvf-upd-kind {{ display: block; min-width: 0; }}
  .up-open {{ white-space: normal; }}
  .up-same li a {{ white-space: normal; }}
}}
</style>
</head>
<body>
<div class="up-top">
  <a href="index.html">Data Vault Foundations</a>
  <span class="up-top-here">Updates</span>
</div>
<main class="up-wrap">
  <div class="up-eyebrow">Law as of {data['law_as_of_label']}</div>
  <h1>Updates</h1>
  <p class="up-lede">This site was first published in {data['first_published']}. The law it teaches has moved since: on 27 July 2026 the EU amended the AI Act. On {data['law_as_of_label']} the regulation chapters were checked again against the official texts. <strong>This page lists every change that check produced.</strong> For each one you can read what the page said before, what it says now, and where the law says so.</p>

  <div class="up-asof">
    <div class="up-stat"><div class="up-stat-num">{data['law_as_of_label']}</div><div class="up-stat-label">Law as of</div></div>
    <div class="up-stat"><div class="up-stat-num">{total}</div><div class="up-stat-label">Updates</div></div>
    <div class="up-stat"><div class="up-stat-num">{len(by_chapter)}</div><div class="up-stat-label">Chapters touched</div></div>
  </div>
  <nav class="up-jump" aria-label="Jump to a chapter">{jump}</nav>

  <div class="up-how">
    <h2>How to read this page</h2>
    <p>Nothing on this site is rewritten silently. In the chapters, every changed passage carries an <span class="dvf-upd-tag">Updated</span> mark and keeps the earlier text next to it. It is the rule a Data Vault follows: new rows are added with their date, old rows stay.</p>
    <p>On this page, &ldquo;Before&rdquo; sums up the earlier text in a few words. The earlier text itself, word for word, is kept in the chapter: follow &ldquo;See it in chapter&rdquo;.</p>
    <ul>
      {legend}
    </ul>
  </div>
{''.join(body)}

  <section class="up-same">
    <h2>Checked and left as it was</h2>
    <p>These statements were checked against the same sources on {data['law_as_of_label']} and are still right.</p>
    <ul>
      {unchanged}
    </ul>
  </section>

  <p class="up-end">This is a learning site, not legal advice. The official texts are on <a href="https://eur-lex.europa.eu" target="_blank" rel="noopener">EUR-Lex</a>; where this site and the Official Journal differ, the Official Journal is right. <a href="index.html">Back to the chapters</a></p>
</main>
</body>
</html>
'''
write('updates.html', PAGE)

# ── 5. the table in the verification note ────────────────────────────────────
DOC = 'docs/regulation-updates-2026-11.md'
if os.path.exists(os.path.join(ROOT, DOC)):
    doc = read(DOC)
    rows = ['| Id | Chapter | Kind | The page said | The page now says | Source | URL | Checked |',
            '|---|---|---|---|---|---|---|---|']

    def cell(s):
        return s.replace('|', '\\|').replace('\n', ' ')

    for u in updates:
        srcs = '; '.join(f'{SRC[k]["label"]}, {pin}' if pin else SRC[k]['label'] for k, pin in u['sources']) or 'none (wording)'
        urls = ' '.join(f'<{SRC[k]["url"]}>' for k, _ in u['sources']) or 'n/a'
        rows.append(f"| {u['id']} | {u['chapter']} | {KIND[u['kind']]} | {cell(u['was'])} | {cell(u['now'])} | {cell(srcs)} | {urls} | {u['date']} |")
    rows2 = ['| Chapter | Statement on the site | Source | URL | Checked |', '|---|---|---|---|---|']
    for c in data.get('unchanged', []):
        rows2.append(f"| {c['chapter']} | {cell(c['claim'])} | {SRC[c['source']]['label']}, {cell(c['pin'])} | <{SRC[c['source']]['url']}> | {data['law_as_of']} |")

    def fill(text, name, lines):
        a, b = f'<!-- {name}:START -->', f'<!-- {name}:END -->'
        if a not in text or b not in text:
            problems.append(f'{DOC}: markers for {name} are missing')
            return text
        return text[:text.index(a) + len(a)] + '\n' + '\n'.join(lines) + '\n' + text[text.index(b):]

    doc = fill(doc, 'TABLE', rows)
    doc = fill(doc, 'UNCHANGED', rows2)
    write(DOC, doc)

finish()

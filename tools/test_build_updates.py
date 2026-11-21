#!/usr/bin/env python3
"""Tests for tools/build_updates.py.

Each case copies the files the script reads into a temporary folder, changes
one thing there, runs the script and compares the exit code and the message.
Most cases break the copy and expect the check to say so; some change it in a
harmless way and expect the check to stay quiet. The site itself is never
written to.

Run from the repo root:   python3 tools/test_build_updates.py
Exit code 1 means a case did not behave as stated.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEEDED = ['data', 'chapters', 'docs', 'tools', 'index.html', 'nav-inject.js', 'updates.html']
INDEX, LIST, NAV = 'index.html', 'data/updates.json', 'nav-inject.js'
CH5, CH7, CH8, CH9 = ('chapters/05-compliance-gdpr.html', 'chapters/07-eu-regulations.html',
                      'chapters/08-compliance-mechanisms.html', 'chapters/09-ai-act-data-vault.html')
STRAY = '<span class="card-tag tag-updated">Updated 1 Jan 2000</span>'
CARD_13 = '<a class="chapter-card card-compliance" href="chapters/13-compliance-self-test.html">'

fails = []
ran = 0


def same(text):
    return text


def card(idx, no):
    m = re.search(r'<a class="chapter-card[^"]*" href="chapters/%02d-[^"]+">.*?</a>\s*' % no, idx, flags=re.S)
    assert m, f'set-up: card {no} not found in index.html'
    return m.group(0)


def in_card(idx, no, old, new):
    c = card(idx, no)
    assert old in c, f'set-up: "{old[:40]}" not in card {no}'
    return idx.replace(c, c.replace(old, new))


def tag(idx, no):
    """The tag as it stands on the card of a chapter with updates, so the cases follow the site's dates."""
    m = re.search(r'<span class="card-tag tag-updated">[^<]*</span>', card(idx, no))
    assert m, f'set-up: card {no} has no tag'
    return m.group(0)


def once(old, new):
    """A change that must hit exactly one place."""
    def f(text):
        assert text.count(old) == 1, f'set-up: {text.count(old)} matches for "{old[:50]}"'
        return text.replace(old, new)
    return f


def first(old, new):
    def f(text):
        assert old in text, f'set-up: "{old[:50]}" not found'
        return text.replace(old, new, 1)
    return f


def after(anchor, old, new, reach=1500):
    """Change the first `old` that follows `anchor`, within `reach` characters."""
    def f(text):
        i = text.index(anchor)
        j = text.index(old, i)
        assert j - i < reach, f'set-up: "{old[:40]}" is too far from "{anchor[:40]}"'
        return text[:j] + new + text[j + len(old):]
    return f


def in_list(change):
    """Change data/updates.json through its parsed form."""
    def f(text):
        d = json.loads(text)
        change({u['id']: u for u in d['updates']}, d)
        return json.dumps(d, indent=2, ensure_ascii=False)
    return f


def case(name, changes, want_rc, want=None, forbid=None, args=('--check',), then=None):
    """changes: {file: function(text) -> text}. then: an extra test run on the folder afterwards."""
    global ran
    ran += 1
    with tempfile.TemporaryDirectory() as dest:
        for item in NEEDED:
            src = os.path.join(ROOT, item)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(dest, item), ignore=shutil.ignore_patterns('__pycache__'))
            else:
                shutil.copyfile(src, os.path.join(dest, item))
        for rel, mutate in changes.items():
            path = os.path.join(dest, rel)
            with open(path, encoding='utf-8') as f:
                old = f.read()
            new = mutate(old)
            assert new != old or mutate is same, f'set-up: "{name}" changed nothing in {rel}'
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new)
        r = subprocess.run([sys.executable, os.path.join('tools', 'build_updates.py'), *args],
                           cwd=dest, capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        why = []
        if r.returncode != want_rc:
            why.append(f'wanted exit {want_rc}, got {r.returncode}')
        if want is not None and want not in out:
            why.append(f'wanted the message "{want}"')
        for bad in ([forbid] if isinstance(forbid, str) else (forbid or [])) + ['Traceback']:
            if bad in out:
                why.append(f'did not want "{bad}"')
        if then and not why:
            extra = then(dest)
            if extra:
                why.append(extra)
    print(('PASS ' if not why else 'FAIL ') + name)
    if why:
        print('     ' + '; '.join(why) + '. Output:')
        print('     ' + out.replace('\n', '\n     '))
        fails.append(name)


def nothing_written_except(*changed_by_the_case):
    """After a failed build, every file must be as the case left it: equal to the site's, apart from the ones the case changed."""
    def f(dest):
        for folder, _dirs, names in os.walk(dest):
            for name in names:
                rel = os.path.relpath(os.path.join(folder, name), dest)
                if rel in changed_by_the_case or '__pycache__' in rel:
                    continue
                with open(os.path.join(dest, rel), 'rb') as a, open(os.path.join(ROOT, rel), 'rb') as b:
                    if a.read() != b.read():
                        return f'{rel} was written although the run failed'
        return None
    return f


def check_passes_now(dest):
    r = subprocess.run([sys.executable, os.path.join('tools', 'build_updates.py'), '--check'], cwd=dest, capture_output=True, text=True)
    return None if r.returncode == 0 else 'after the build, --check still fails: ' + (r.stdout + r.stderr).strip()[-200:]


print('── the site as it stands')
case('the site as committed passes', {INDEX: same}, 0)

print('── home page: every chapter with updates has one card')
case('a card that is gone is reported', {INDEX: lambda t: t.replace(card(t, 9), '')}, 1, 'chapter 9 has updates but no card')
case('a card that is commented out is reported',
     {INDEX: lambda t: t.replace(card(t, 9), '<!-- ' + card(t, 9) + ' -->')}, 1, 'chapter 9 has updates but no card')
case('a card whose class only starts like chapter-card is reported as missing',
     {INDEX: once(CARD_13, CARD_13.replace('chapter-card', 'chapter-card-old'))}, 1, 'chapter 13 has updates but no card')
case('a hidden card is reported', {INDEX: once(CARD_13, CARD_13.replace('<a ', '<a hidden '))}, 1, 'the card of chapter 13 is hidden')
case('a chapter with two cards is reported', {INDEX: lambda t: t.replace(card(t, 5), card(t, 5) * 2)}, 1, 'chapter 5 has 2 cards')
case('a card that links to a file that is not there is reported',
     {INDEX: once('href="chapters/13-compliance-self-test.html"', 'href="chapters/13-typo.html"')}, 1, 'which does not exist')
case('a card written with href before class is accepted',
     {INDEX: once(CARD_13, '<a href="chapters/13-compliance-self-test.html" class="chapter-card card-compliance">')}, 0)
case('a card written with single quotes and capitals is accepted',
     {INDEX: once(CARD_13, "<A CLASS='chapter-card card-compliance' HREF='chapters/13-compliance-self-test.html'>")}, 0)

print('── home page: the tag on a card')
case('a missing tag is reported', {INDEX: lambda t: in_card(t, 7, tag(t, 7), '')}, 1, 'the card of chapter 7 should carry one visible tag')
case('a commented-out tag is reported',
     {INDEX: lambda t: in_card(t, 7, tag(t, 7), '<!-- ' + tag(t, 7) + ' -->')}, 1, 'the card of chapter 7 should carry one visible tag')
case('a tag with the wrong date is reported', {INDEX: lambda t: in_card(t, 8, tag(t, 8), STRAY)}, 1, 'the card of chapter 8 should carry one visible tag')
case('a tag without its card-tag class is reported',
     {INDEX: lambda t: in_card(t, 5, tag(t, 5), tag(t, 5).replace('card-tag tag-updated', 'tag-updated'))}, 1,
     'the card of chapter 5 should carry one visible tag')
case('a hidden tag is reported',
     {INDEX: lambda t: in_card(t, 5, tag(t, 5), tag(t, 5).replace('<span ', '<span hidden '))}, 1, 'the card of chapter 5 should carry one visible tag')
case('a second tag on the same card is reported, whatever its quotes',
     {INDEX: lambda t: in_card(t, 5, '</a>', "<span class='card-tag tag-updated'>Updated 1 Jan 2000</span></a>")}, 1,
     'the card of chapter 5 should carry one visible tag')
case('a class that only starts like tag-updated does not count as the tag',
     {INDEX: lambda t: in_card(t, 7, tag(t, 7), tag(t, 7).replace('tag-updated', 'tag-updated-old'))}, 1,
     'the card of chapter 7 should carry one visible tag')
case('the right tag with its classes in the other order is accepted',
     {INDEX: lambda t: in_card(t, 5, tag(t, 5), tag(t, 5).replace('card-tag tag-updated', 'tag-updated card-tag'))}, 0)
case('the right tag with its text on its own line is accepted',
     {INDEX: lambda t: in_card(t, 5, tag(t, 5), tag(t, 5).replace('">', '">\n          ').replace('</span>', '\n        </span>'))}, 0)

print('── home page: no tag anywhere else')
case('a tag on a chapter without updates is reported, whatever the class order',
     {INDEX: lambda t: in_card(t, 1, '</a>', STRAY.replace('card-tag tag-updated', 'tag-updated card-tag') + '</a>')}, 1,
     'the card of chapter 1 has an "Updated" tag but no updates')
case('a tag in single quotes and capitals on a chapter without updates is reported',
     {INDEX: lambda t: in_card(t, 6, '</a>', "<SPAN CLASS='card-tag tag-updated'>Updated 1 Jan 2000</SPAN></a>")}, 1,
     'the card of chapter 6 has an "Updated" tag but no updates')
case('a tag outside every card is reported', {INDEX: once('</body>', STRAY + '</body>')}, 1, 'sits outside every chapter card')
case('a comment that quotes the tag markup is not taken for a tag', {INDEX: once('</body>', '<!-- ' + STRAY + ' --></body>')}, 0)

print('── home page: dates')
case('the tag follows the newest update of the chapter',
     {LIST: in_list(lambda by, d: by['u05-04'].update(date='2026-12-01'))}, 1, 'the card of chapter 5 should carry one visible tag "Updated 1 Dec 2026"')
case('an older update of the same chapter does not change the tag',
     {LIST: in_list(lambda by, d: by['u05-04'].update(date='2026-11-01'))}, 1, 'marker u05-04 should be headed "Updated 1 Nov 2026"',
     forbid='the card of chapter 5')

print('── chapters: markers against the list')
case('an update without its marker is reported',
     {CH8: once('<div class="dvf-upd" id="u08-01" data-upd="u08-01">', '<div class="dvf-upd">')}, 1, 'update u08-01 is on the list but has no marker')
case('a marker that is not on the list is reported',
     {CH9: first('data-upd="u09-10"', 'data-upd="u09-77"')}, 1, 'marker u09-77 is in the chapter but not on the list')
case('a marker with the wrong kind is reported',
     {CH8: after('id="u08-01"', '<span class="dvf-upd-kind">Correction</span>', '<span class="dvf-upd-kind">Added</span>')}, 1,
     'marker u08-01 should be labelled "Correction"')
case('a marker with the wrong date is reported',
     {CH8: after('id="u08-01"', '<span class="dvf-upd-tag">Updated 20 Nov 2026</span>', '<span class="dvf-upd-tag">Updated 1 Jan 2020</span>')}, 1,
     'marker u08-01 should be headed')
case('a marker emptied of its old and new text is reported',
     {CH5: lambda t: re.sub(r'(<span class="dvf-upd-i" id="u05-05" data-upd="u05-05">).*?</a></span>', r'\1high-risk non-compliance</span>', t, count=1, flags=re.S)},
     1, 'marker u05-05 shows neither new nor earlier text')
case('a hidden marker is reported',
     {CH8: once('<div class="dvf-upd" id="u08-01" data-upd="u08-01">', '<div class="dvf-upd" id="u08-01" data-upd="u08-01" hidden>')}, 1,
     'marker u08-01 is hidden')
case('an id used twice is reported',
     {CH9: once('<span class="dvf-upd-i" data-upd="u09-18"><del>', '<span class="dvf-upd-i" id="u09-18" data-upd="u09-18"><del>')}, 1,
     'the id "u09-18" is used 2 times')
case('an "Updated" link that leads to another entry is reported',
     {CH9: after('id="u09-04"', 'href="../updates.html#u09-04"', 'href="../updates.html#u09-03"')}, 1, 'the "Updated" link of u09-04 points at')
case('a link to an entry that does not exist is reported',
     {CH9: after('id="u09-12"', '<a href="../updates.html#u09-12">all updates</a>', '<a href="../updates.html#u09-88">all updates</a>', reach=4000)},
     1, 'which is not on the list')
case('a banner whose heading shows another date is reported',
     {CH7: after('id="law-review"', 'Law as of 20 November 2026', 'Law as of 1 January 2020')}, 1, 'banner does not show')
case('a banner whose sentence shows another date is reported',
     {CH7: after('id="law-review"', 'again on 20 November 2026', 'again on 1 January 2020')}, 1, 'banner does not show')

case('an element that has an update id but is not a marker is reported, and the update counts as unmarked',
     {CH5: lambda t: re.sub(r'<span class="dvf-upd-i" id="u05-05" data-upd="u05-05">.*?</a></span>', '<span id="u05-05">high-risk non-compliance</span>', t, count=1, flags=re.S)},
     1, 'update u05-05 is on the list but has no marker')
case('a marker that holds only the spoken cues is reported',
     {CH5: lambda t: re.sub(r'(<span class="dvf-upd-i" id="u05-05" data-upd="u05-05">).*?(<a class="dvf-upd-chip")',
                            r'\1<del><span class="dvf-sr">Before: </span></del> <ins><span class="dvf-sr">Now: </span></ins>\2', t, count=1, flags=re.S)},
     1, 'marker u05-05 shows neither new nor earlier text')
case('a block marker without its new text is reported',
     {CH8: after('id="u08-01"', '<div class="dvf-upd-now">', '<div class="dvf-upd-later">')}, 1, 'marker u08-01 has no new text')
case('a marker that is neither a block nor an inline span is reported',
     {CH8: once('<div class="dvf-upd" id="u08-01" data-upd="u08-01">', '<div class="note" id="u08-01" data-upd="u08-01">')}, 1,
     'marker u08-01 is neither a dvf-upd block nor a dvf-upd-i span')
case('a marker hidden by an inline style is reported',
     {CH8: once('<div class="dvf-upd" id="u08-01" data-upd="u08-01">', '<div class="dvf-upd" id="u08-01" data-upd="u08-01" style="display: none">')}, 1,
     'marker u08-01 is hidden')
case('a marker that carries the id of another update is reported',
     {CH9: once('<span class="dvf-upd-i" data-upd="u09-18"><del>', '<span class="dvf-upd-i" id="u09-99" data-upd="u09-18"><del>')}, 1,
     'a marker has id u09-99 but belongs to u09-18')
case('an "Updated" link with the wrong date in its title is reported',
     {CH9: after('id="u09-04"', 'title="Updated 20 Nov 2026', 'title="Updated 1 Jan 2020')}, 1, 'should say "Updated 20 Nov 2026" in its title')
case('an "Updated" link written another way, without its spoken name, is reported',
     {CH9: after('id="u09-04"', '<a class="dvf-upd-chip" href="../updates.html#u09-04" aria-label="Updated: The product-safety list is Annex I, not Annex II" title=',
                 '<a href="../updates.html#u09-04" class="dvf-upd-chip" title=')}, 1, 'the "Updated" link of u09-04 has no spoken name')
case('an "Updated" link outside every marker is reported',
     {CH7: once('</body>', '<a class="dvf-upd-chip" href="../updates.html#u07-01">Updated</a></body>')}, 1, 'sits outside every marker')
case('a chapter with updates but without its banner is reported', {CH7: once('id="law-review"', 'id="law-review-old"')}, 1, 'has updates but no visible banner')
case('a chapter with updates that does not load the stylesheet is reported',
     {CH7: once('assets/updates.css', 'assets/other.css')}, 1, 'does not load assets/updates.css')

print('── navigation and home page strip')
case('another date in the navigation is reported', {NAV: once("var LAW_AS_OF = '", "var LAW_AS_OF = 'x")}, 1, 'LAW_AS_OF should be')
case('a regulation chapter missing from the navigation list is reported', {NAV: once('13: true', '13: false')}, 1, 'LAW_CHAPTERS is')
case('a home page without its "law as of" strip is reported', {INDEX: first('law-strip"', 'law-strap"')}, 1, 'expected one visible "law as of" strip')
case('a card whose link carries a fragment is accepted',
     {INDEX: once('href="chapters/13-compliance-self-test.html"', 'href="chapters/13-compliance-self-test.html#top"')}, 0)
case('a tag hidden by an inline style is reported',
     {INDEX: lambda t: in_card(t, 5, tag(t, 5), tag(t, 5).replace('<span ', '<span style="display:none" '))}, 1,
     'the card of chapter 5 should carry one visible tag')

print('── the list itself')
case('a list that is not valid JSON is reported in words', {LIST: lambda t: t[:-2]}, 1, 'data/updates.json is not valid JSON')
case('two entries with the same id are reported', {LIST: in_list(lambda by, d: by['u07-02'].update(id='u07-01'))}, 1, 'duplicate ids')
case('an id that does not match its chapter is reported', {LIST: in_list(lambda by, d: by['u07-01'].update(chapter=8))}, 1, 'u07-01: id does not match chapter 8')
case('an unknown source is reported', {LIST: in_list(lambda by, d: by['u07-01'].update(sources=[['NOPE', '']]))}, 1, 'u07-01: unknown source NOPE')
case('a chapter written as text is reported in words', {LIST: in_list(lambda by, d: by['u07-01'].update(chapter='7'))}, 1, '"chapter" must be a number')
case('a law date in another form is reported in words', {LIST: in_list(lambda by, d: by['u09-02'].update(law_date='2026-07-27'))}, 1, '"law_date" must look like')
case('an unknown kind is reported in words, not as a crash',
     {LIST: in_list(lambda by, d: by['u07-01'].update(kind='rumour'))}, 1, 'u07-01: unknown kind rumour')
case('an entry without its source list is reported in words',
     {LIST: in_list(lambda by, d: by['u07-01'].pop('sources'))}, 1, 'u07-01: the entry lacks sources')

print('── building (without --check)')
case('a build that finds a problem writes nothing',
     {CH9: first('data-upd="u09-10"', 'data-upd="u09-77"'), LIST: in_list(lambda by, d: by['u07-01'].update(title='A changed title'))},
     1, 'nothing was written', args=(), then=nothing_written_except(CH9, LIST))
case('a build that finds a problem leaves a stale count and total alone too',
     {CH7: lambda t: re.sub(r'<span data-upd-count>\d+</span>', '<span data-upd-count>99</span>', t),
      INDEX: lambda t: re.sub(r'<span data-upd-total>\d+</span>', '<span data-upd-total>99</span>', t),
      NAV: once("var LAW_AS_OF = '", "var LAW_AS_OF = 'x")},
     1, 'nothing was written', args=(), then=nothing_written_except(CH7, INDEX, NAV))
case('a build puts a stale banner count right, and the check then passes',
     {CH7: lambda t: re.sub(r'<span data-upd-count>\d+</span>', '<span data-upd-count>99</span>', t)}, 0, args=(), then=check_passes_now)
case('a stale banner count fails the check', {CH7: lambda t: re.sub(r'<span data-upd-count>\d+</span>', '<span data-upd-count>99</span>', t)},
     1, 'is out of date')

print('\n' + (f'ALL {ran} PASS' if not fails else f'{len(fails)} of {ran} FAILED: {fails}'))
sys.exit(1 if fails else 0)

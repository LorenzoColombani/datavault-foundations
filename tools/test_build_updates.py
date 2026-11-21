#!/usr/bin/env python3
"""Tests for the home-page card check in tools/build_updates.py.

Each case copies the files the checker reads into a temporary folder, breaks
index.html in one way, runs `build_updates.py --check` there and compares the
exit code and the message. The site itself is never written to.

Run from the repo root:   python3 tools/test_build_updates.py
Exit code 1 means a case did not behave as stated.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEEDED = ['data', 'chapters', 'docs', 'tools', 'index.html', 'nav-inject.js', 'updates.html']
STRAY = '<span class="card-tag tag-updated">Updated 1 Jan 2000</span>'
STRAY_OTHER_ORDER = '<span class="tag-updated card-tag">Updated 1 Jan 2000</span>'
CARD_13 = '<a class="chapter-card card-compliance" href="chapters/13-compliance-self-test.html">'

fails = []


def card(idx, no):
    m = re.search(r'<a class="chapter-card[^"]*" href="chapters/%02d-[^"]+">.*?</a>\s*' % no, idx, flags=re.S)
    assert m, f'set-up: card {no} not found in index.html'
    return m.group(0)


def in_card(idx, no, old, new):
    c = card(idx, no)
    return idx.replace(c, c.replace(old, new))


def tag(idx, no):
    """The tag as it stands on the card of a chapter with updates, so the cases follow the site's dates."""
    m = re.search(r'<span class="card-tag tag-updated">[^<]*</span>', card(idx, no))
    assert m, f'set-up: card {no} has no tag'
    return m.group(0)


def case(name, mutate, want_rc, want_text=None):
    with tempfile.TemporaryDirectory() as dest:
        for item in NEEDED:
            src = os.path.join(ROOT, item)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(dest, item), ignore=shutil.ignore_patterns('__pycache__'))
            else:
                shutil.copyfile(src, os.path.join(dest, item))
        path = os.path.join(dest, 'index.html')
        with open(path, encoding='utf-8') as f:
            idx = f.read()
        new = mutate(idx)
        assert new != idx or mutate is same, f'set-up: "{name}" changed nothing'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new)
        r = subprocess.run([sys.executable, os.path.join('tools', 'build_updates.py'), '--check'],
                           cwd=dest, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    good = r.returncode == want_rc and (want_text is None or want_text in out)
    print(('PASS ' if good else 'FAIL ') + name)
    if not good:
        print(f'     wanted exit {want_rc}' + (f' and "{want_text}"' if want_text else '') + f'; got exit {r.returncode}:')
        print('     ' + out.replace('\n', '\n     '))
        fails.append(name)


def same(idx):
    return idx


# the site as it stands
case('the site as committed passes', same, 0)

# a chapter with updates must have exactly one card
case('a chapter with updates whose card is gone is reported',
     lambda t: t.replace(card(t, 9), ''), 1, 'chapter 9 has updates but no card')
case('a card that is no longer a chapter-card is reported as missing',
     lambda t: t.replace(CARD_13, CARD_13.replace('chapter-card', 'chapter-tile')), 1, 'chapter 13 has updates but no card')
case('a card written with href before class is still recognised',
     lambda t: t.replace(CARD_13, '<a href="chapters/13-compliance-self-test.html" class="chapter-card card-compliance">'), 0)
case('a chapter with two cards is reported',
     lambda t: t.replace(card(t, 5), card(t, 5) * 2), 1, 'chapter 5 has 2 cards')

# the tag on a card of a chapter with updates
case('a missing tag is reported', lambda t: in_card(t, 7, tag(t, 7), ''), 1, 'the card of chapter 7 should carry one tag')
case('a tag with the wrong date is reported',
     lambda t: in_card(t, 8, tag(t, 8), STRAY), 1, 'the card of chapter 8 should carry one tag')
case('the right tag with its classes in the other order is accepted',
     lambda t: in_card(t, 5, tag(t, 5), tag(t, 5).replace('card-tag tag-updated', 'tag-updated card-tag')), 0)

# no tag anywhere else
case('a tag on a chapter without updates is reported, whatever the class order',
     lambda t: in_card(t, 1, '</a>', STRAY_OTHER_ORDER + '</a>'), 1, 'the card of chapter 1 has an "Updated" tag but no updates')
case('a tag with an extra class on a chapter without updates is reported',
     lambda t: in_card(t, 6, '</a>', STRAY.replace('tag-updated', 'tag-updated big') + '</a>'), 1,
     'the card of chapter 6 has an "Updated" tag but no updates')
case('a tag outside every card is reported',
     lambda t: t.replace('</body>', STRAY + '</body>'), 1, 'sits outside every chapter card')

print('\n' + ('ALL PASS' if not fails else f'{len(fails)} FAILED: {fails}'))
sys.exit(1 if fails else 0)

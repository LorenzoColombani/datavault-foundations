#!/usr/bin/env python3
"""inject-gamification.py — Add inventory + achievements UI to chapters 1-9.

Injects:
  1. Game UI CSS (before </style>)
  2. Game UI HTML — inventory toolbar + achievements panel, NO quest log (before </body>)
  3. CDN scripts (GSAP, Tippy.js) + 7 system JS modules (before </body>)
  4. Per-chapter scroll-based item discovery script (before </body>)
"""

import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chapters')

CHAPTER_FILES = {
    1: '01-ontology.html',
    2: '02-data-vault-deep-cuts.html',
    3: '03-sql-select.html',
    4: '04-sql-joins.html',
    5: '05-compliance-gdpr.html',
    6: '06-dbt-tools.html',
    7: '07-eu-regulations.html',
    8: '08-compliance-mechanisms.html',
    9: '09-ai-act-data-vault.html',
}

# Items per chapter (from loot-definitions.js session numbers)
CHAPTER_ITEMS = {
    1: ['table-vs-row', 'primary-key', 'entity-noun', 'career-story'],
    2: ['hub-blueprint', 'satellite-blueprint', 'link-blueprint', 'vault-architecture', 'dv-elevator-pitch'],
    3: ['select-clause', 'from-clause', 'where-clause', 'three-valued-logic'],
    4: ['inner-join', 'left-join', 'on-clause', 'alias-assignment', 'dot-notation'],
    5: ['gdpr-fundamentals', 'data-subject-rights', 'data-mesh-concept', 'compliance-differentiator'],
    6: ['dbt-model', 'elt-vs-etl', 'datavault4dbt', 'snowflake', 'tools-landscape'],
    7: ['eu-data-act', 'dora', 'eprivacy', 'regulation-map'],
    8: ['data-sovereignty', 'cross-border-transfers', 'iso-27001', 'soc-2'],
    9: ['ai-risk-tiers', 'provider-deployer', 'ai-spaghetti', 'ai-act-edge'],
}

GAME_CSS = """
/* ═══════ Game UI: Inventory + Achievements ═══════ */
.achievement-toast-container {
  position: fixed; top: 100px; right: -350px; z-index: 200;
  display: flex; flex-direction: column; gap: 10px;
  pointer-events: none;
}
.achievement-toast {
  width: 320px; padding: 16px 20px; border-radius: 12px;
  backdrop-filter: blur(16px);
  transform: translateX(0); transition: right 0.5s cubic-bezier(0.68,-0.55,0.27,1.55);
  pointer-events: auto; position: relative;
}
.achievement-toast-container.has-toast { right: 20px; }
.achievement-toast-tier {
  font-family: 'Orbitron', sans-serif; font-size: 0.65rem;
  letter-spacing: 2px; margin-bottom: 4px;
}
.achievement-toast-name { font-family: 'Orbitron', sans-serif; font-size: 1rem; margin-bottom: 4px; }
.achievement-toast-desc { font-size: 0.8rem; color: var(--text-secondary, rgba(255,255,255,0.5)); }
.inventory-toolbar {
  position: fixed; bottom: 12px; left: 16px;
  z-index: 90; display: flex; gap: 12px; padding: 8px 16px;
  background: rgba(10,22,40,0.8); backdrop-filter: blur(16px);
  border: 1px solid rgba(0,180,255,0.15); border-radius: 30px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  transition: all 0.3s ease;
}
.inventory-toolbar:hover { border-color: rgba(0,180,255,0.3); }
.inventory-bag {
  width: 44px; height: 44px; border-radius: 50%;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: rgba(0,0,0,0.3); border: 1.5px solid;
  cursor: pointer; transition: all 0.2s ease; position: relative;
}
.inventory-bag:hover { transform: scale(1.15); filter: brightness(1.3); }
.bag-icon { font-size: 18px; line-height: 1; }
.bag-count {
  font-family: 'Orbitron', sans-serif; font-size: 0.55rem;
  color: var(--text-dim, rgba(255,255,255,0.3)); margin-top: 2px;
}
.inventory-panel {
  position: fixed; bottom: 75px; left: 16px;
  z-index: 89; width: min(600px, calc(100vw - 32px)); max-height: 400px;
  background: rgba(10,22,40,0.92); backdrop-filter: blur(20px);
  border: 1px solid rgba(0,180,255,0.2); border-radius: 16px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.5);
  transition: opacity 0.3s ease, transform 0.3s ease;
  overflow-y: auto;
}
.inventory-panel.hidden { opacity: 0; pointer-events: none; transform: translateY(20px); }
.inventory-panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-bottom: 1px solid rgba(0,180,255,0.1);
}
.inventory-panel-title { font-family: 'Orbitron', sans-serif; font-size: 1rem; }
.inventory-panel-close {
  background: none; border: none; color: var(--text-dim, rgba(255,255,255,0.3));
  font-size: 1.4rem; cursor: pointer; padding: 4px 8px;
}
.inventory-panel-close:hover { color: var(--text-bright, #fff); }
.inventory-panel-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px; padding: 16px 20px;
}
.inventory-slot {
  padding: 12px 14px; border-radius: 8px;
  background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.05);
  transition: all 0.25s ease; min-height: 70px;
  display: flex; flex-direction: column; justify-content: center;
}
.inventory-slot.discovered { cursor: pointer; }
.inventory-slot.discovered:hover { transform: translateY(-2px); filter: brightness(1.2); box-shadow: 0 4px 16px rgba(0,180,255,0.15); }
.inventory-slot.discovered:active { transform: scale(0.95); filter: brightness(1.4); transition: all 0.1s ease; }
.inventory-slot.locked { opacity: 0.3; }
.slot-name { font-size: 0.85rem; color: var(--text-bright, #fff); font-weight: 500; margin-bottom: 4px; }
.slot-session { font-size: 0.65rem; color: var(--text-dim, rgba(255,255,255,0.3)); font-family: 'Orbitron', sans-serif; }
.achievements-bag { border-color: rgba(255,215,0,0.4) !important; background: rgba(255,215,0,0.08) !important; }
.achievements-bag:hover { border-color: rgba(255,215,0,0.7) !important; }
.achievement-slot {
  padding: 12px 14px; border-radius: 8px;
  background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.05);
  min-height: 70px; display: flex; flex-direction: column; justify-content: center;
}
.achievement-slot.unlocked { border-color: var(--ach-color, rgba(255,215,0,0.4)); box-shadow: 0 0 8px var(--ach-glow, rgba(255,215,0,0.2)); }
.achievement-slot.locked { opacity: 0.25; }
@media (max-width: 600px) {
  .inventory-toolbar { bottom: 8px; left: 8px; padding: 6px 12px; }
  .inventory-bag { width: 36px; height: 36px; }
  .inventory-panel { width: calc(100vw - 16px); left: 8px; bottom: 60px; }
}
"""

GAME_HTML = """
<!-- ═══════ Game UI Elements ═══════ -->
<!-- Achievement Toast Container -->
<div id="achievement-toast-container" class="achievement-toast-container"></div>

<!-- Inventory Toolbar -->
<div id="inventory-toolbar" class="inventory-toolbar">
  <div class="inventory-bags"></div>
  <button id="achievements-btn" class="inventory-bag achievements-bag" aria-label="Achievements" onclick="SV.achievements && SV.achievements.togglePanel()">
    <span class="bag-icon">&#x1F3C6;</span>
  </button>
</div>

<!-- Inventory Panel -->
<div id="inventory-panel" class="inventory-panel hidden">
  <div class="inventory-panel-header">
    <span class="inventory-panel-title"></span>
    <button class="inventory-panel-close" onclick="SV.inventory && SV.inventory.closePanel()">&times;</button>
  </div>
  <div class="inventory-panel-grid"></div>
</div>

<!-- Achievements Panel -->
<div id="achievements-panel" class="inventory-panel hidden" style="z-index: 95;">
  <div class="inventory-panel-header">
    <span class="inventory-panel-title">&#x1F3C6; Discoveries</span>
    <button class="inventory-panel-close" onclick="SV.achievements && SV.achievements.togglePanel()">&times;</button>
  </div>
  <div id="achievements-panel-grid" class="inventory-panel-grid"></div>
</div>
"""

CDN_AND_SYSTEM_SCRIPTS = """<!-- CDN Libraries -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
<script src="https://unpkg.com/@popperjs/core@2"></script>
<script src="https://unpkg.com/tippy.js@6"></script>

<!-- Game Systems (order matters: persistence first, then data, then UI) -->
<script src="../systems/persistence.js"></script>
<script src="../systems/loot-definitions.js"></script>
<script src="../systems/retroactive-loot.js"></script>
<script src="../systems/inventory.js"></script>
<script src="../systems/quest-log.js"></script>
<script src="../systems/achievements.js"></script>
<script src="../systems/scroll-effects.js"></script>
"""


def make_observer_script(items):
    """Generate scroll-based item discovery script."""
    items_js = ', '.join(f"'{s}'" for s in items)
    return f"""
<script>
/* ═══════ Game system init + scroll-based item discovery ═══════ */
document.addEventListener('DOMContentLoaded', function() {{
  /* Initialize game systems */
  if (typeof SV !== 'undefined') {{
    if (SV.inventory) SV.inventory.init();
    if (SV.achievements) SV.achievements.init();
  }}

  var items = [{items_js}];
  var granted = {{}};

  /* Restore already-granted items from persistence */
  if (typeof SV !== 'undefined' && SV.persistence) {{
    var inv = SV.persistence.get('inventory', []);
    for (var i = 0; i < inv.length; i++) {{ granted[inv[i].id] = true; }}
  }}

  function getScrollPct() {{
    var h = Math.max(document.documentElement.scrollHeight - window.innerHeight, 1);
    return window.scrollY / h;
  }}

  function checkScroll() {{
    var pct = getScrollPct();
    for (var i = 0; i < items.length; i++) {{
      var threshold = (i + 0.5) / items.length;
      if (pct >= threshold && !granted[items[i]]) {{
        granted[items[i]] = true;
        if (typeof SV !== 'undefined' && SV.inventory && SV.inventory.addItem) {{
          SV.inventory.addItem(items[i]);
        }}
      }}
    }}
  }}

  window.addEventListener('scroll', checkScroll, {{ passive: true }});
  setTimeout(checkScroll, 1500);
}});
</script>
"""


def inject_gamification(chapter_num):
    """Inject game UI into a single chapter file."""
    filename = CHAPTER_FILES[chapter_num]
    filepath = os.path.join(BASE, filename)

    if not os.path.exists(filepath):
        print(f'  Chapter {chapter_num}: FILE NOT FOUND — {filepath}')
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Idempotency check
    if 'inventory-toolbar' in content:
        print(f'  Chapter {chapter_num}: already has game UI, skipping')
        return True

    # 1. Inject CSS before last </style>
    style_pos = content.rfind('</style>')
    if style_pos == -1:
        print(f'  Chapter {chapter_num}: ERROR — no </style> found')
        return False
    content = content[:style_pos] + GAME_CSS + '\n' + content[style_pos:]

    # 2. Inject HTML + scripts + observer before </body>
    body_pos = content.rfind('</body>')
    if body_pos == -1:
        print(f'  Chapter {chapter_num}: ERROR — no </body> found')
        return False

    items = CHAPTER_ITEMS[chapter_num]
    observer = make_observer_script(items)
    injection = '\n' + GAME_HTML + CDN_AND_SYSTEM_SCRIPTS + observer + '\n'
    content = content[:body_pos] + injection + content[body_pos:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f'  Chapter {chapter_num}: injected ({len(items)} items: {", ".join(items)})')
    return True


if __name__ == '__main__':
    print('Injecting gamification into chapters 1-9...')
    results = []
    for ch in range(1, 10):
        results.append(inject_gamification(ch))

    success = sum(1 for r in results if r)
    print(f'\nDone: {success}/9 chapters processed.')
    if not all(results):
        sys.exit(1)

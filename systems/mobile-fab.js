/**
 * mobile-fab.js — Mobile FAB + Bottom Sheet for Data Vault Foundations
 * Replaces desktop floating game UI (quest log, inventory) with a
 * FAB speed-dial and bottom sheet on mobile viewports (< 600px).
 * Load AFTER all game system scripts (inventory.js, quest-log.js, achievements.js).
 */
(function() {
  'use strict';

  // Only activate on mobile
  if (window.innerWidth > 600) return;

  // Inject CSS
  var style = document.createElement('style');
  style.textContent = [
    '.mobile-fab { display: flex; position: fixed; bottom: 20px; right: 20px; z-index: 500; flex-direction: column-reverse; align-items: center; gap: 12px; }',
    '.mobile-fab-main { width: 52px; height: 52px; border-radius: 50%; border: 1.5px solid rgba(245,158,11,0.5); background: rgba(10,22,40,0.9); backdrop-filter: blur(12px); color: #f59e0b; font-size: 20px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease; box-shadow: 0 4px 20px rgba(0,0,0,0.5), 0 0 15px rgba(245,158,11,0.15); }',
    '.mobile-fab-main:hover, .mobile-fab-main:active { border-color: #f59e0b; box-shadow: 0 4px 20px rgba(0,0,0,0.5), 0 0 25px rgba(245,158,11,0.3); }',
    '.mobile-fab-main .fab-icon { transition: transform 0.3s ease; }',
    '.mobile-fab.open .mobile-fab-main .fab-icon { transform: rotate(45deg); }',
    '.mobile-fab-items { display: flex; flex-direction: column; gap: 10px; align-items: center; }',
    '.mobile-fab-item { width: 42px; height: 42px; border-radius: 50%; border: 1px solid rgba(0,180,255,0.3); background: rgba(10,22,40,0.9); backdrop-filter: blur(12px); color: #00b4ff; font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center; opacity: 0; transform: scale(0); transition: all 0.25s ease; box-shadow: 0 2px 12px rgba(0,0,0,0.4); }',
    '.mobile-fab-item:nth-child(1) { transition-delay: 0s; }',
    '.mobile-fab-item:nth-child(2) { transition-delay: 0.05s; }',
    '.mobile-fab.open .mobile-fab-item { opacity: 1; transform: scale(1); }',
    '.mobile-fab.open .mobile-fab-item:nth-child(1) { transition-delay: 0.05s; }',
    '.mobile-fab.open .mobile-fab-item:nth-child(2) { transition-delay: 0.1s; }',
    '.mobile-fab-tooltip { position: absolute; right: 54px; background: rgba(10,22,40,0.95); color: #94a3b8; font-family: "Orbitron", monospace; font-size: 8px; letter-spacing: 0.1em; text-transform: uppercase; padding: 4px 10px; border-radius: 4px; border: 1px solid rgba(0,180,255,0.15); white-space: nowrap; pointer-events: none; opacity: 0; transition: opacity 0.2s; }',
    '.mobile-fab.open .mobile-fab-tooltip { opacity: 1; }',
    '.mobile-sheet-backdrop { display: block; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 400; opacity: 0; pointer-events: none; transition: opacity 0.3s ease; }',
    '.mobile-sheet-backdrop.visible { opacity: 1; pointer-events: auto; }',
    '.mobile-sheet { display: block; position: fixed; bottom: 0; left: 0; right: 0; z-index: 450; max-height: 55vh; background: rgba(8,20,42,0.96); backdrop-filter: blur(20px); border-top: 1px solid rgba(0,180,255,0.2); border-radius: 16px 16px 0 0; transform: translateY(100%); transition: transform 0.3s ease; overflow-y: auto; }',
    '.mobile-sheet.visible { transform: translateY(0); }',
    '.mobile-sheet-handle { width: 36px; height: 4px; background: rgba(255,255,255,0.2); border-radius: 2px; margin: 10px auto 6px; }',
    '.mobile-sheet-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 20px 12px; border-bottom: 1px solid rgba(0,180,255,0.1); }',
    '.mobile-sheet-title { font-family: "Orbitron", monospace; font-size: 11px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #e2e8f0; }',
    '.mobile-sheet-close { background: none; border: none; color: #64748b; font-size: 18px; cursor: pointer; padding: 4px; }',
    '.mobile-sheet-close:hover { color: #e2e8f0; }',
    '.mobile-sheet-body { padding: 12px 16px 24px; }',
    '.mobile-sheet-body .quest-log-list { list-style: none; padding: 0; margin: 0; }',
    '.mobile-sheet-body .quest-log-item { display: flex; align-items: center; gap: 8px; padding: 8px 10px; margin: 2px 0; border-radius: 6px; font-size: 0.85rem; color: #94a3b8; border-left: 2px solid transparent; }',
    '.mobile-sheet-body .quest-log-item.active { border-left-color: #00b4ff; color: #e2e8f0; }',
    '.mobile-sheet-body .quest-log-item.completed { opacity: 0.5; text-decoration: line-through; }',
    '.mobile-sheet-body .quest-check { font-size: 0.9em; width: 20px; text-align: center; }',
    '.mobile-sheet-body .mobile-inv-grid { display: flex; flex-wrap: wrap; gap: 8px; }',
    '.mobile-sheet-body .mobile-inv-item { display: flex; align-items: center; gap: 8px; padding: 10px 14px; background: rgba(0,0,0,0.3); border: 1px solid rgba(0,180,255,0.15); border-radius: 8px; font-size: 0.85rem; color: #94a3b8; flex: 1 1 auto; min-width: 0; cursor: pointer; transition: background 0.2s, border-color 0.2s; }',
    '.mobile-sheet-body .mobile-inv-item:active { background: rgba(0,180,255,0.12); }',
    '.mobile-sheet-body .mobile-inv-icon { font-size: 1.2em; flex-shrink: 0; }',
    '/* Hide desktop game UI on mobile */',
    '@media (max-width: 600px) {',
    '  .quest-log { display: none !important; }',
    '  .inventory-toolbar { display: none !important; }',
    '}'
  ].join('\n');
  document.head.appendChild(style);

  // Inject HTML
  var fab = document.createElement('div');
  fab.className = 'mobile-fab';
  fab.id = 'mobile-fab';

  var items = document.createElement('div');
  items.className = 'mobile-fab-items';

  var objBtn = document.createElement('button');
  objBtn.className = 'mobile-fab-item';
  objBtn.setAttribute('data-sheet', 'objectives');
  objBtn.setAttribute('aria-label', 'Objectives');
  objBtn.textContent = '\uD83D\uDCDC';
  var objTip = document.createElement('span');
  objTip.className = 'mobile-fab-tooltip';
  objTip.textContent = 'Objectives';
  objBtn.appendChild(objTip);

  var invBtn = document.createElement('button');
  invBtn.className = 'mobile-fab-item';
  invBtn.setAttribute('data-sheet', 'inventory');
  invBtn.setAttribute('aria-label', 'Inventory');
  invBtn.textContent = '\uD83C\uDF92';
  var invTip = document.createElement('span');
  invTip.className = 'mobile-fab-tooltip';
  invTip.textContent = 'Inventory';
  invBtn.appendChild(invTip);

  items.appendChild(objBtn);
  items.appendChild(invBtn);

  var mainBtn = document.createElement('button');
  mainBtn.className = 'mobile-fab-main';
  mainBtn.setAttribute('aria-label', 'Game menu');
  var iconSpan = document.createElement('span');
  iconSpan.className = 'fab-icon';
  iconSpan.textContent = '\u2726';
  mainBtn.appendChild(iconSpan);

  fab.appendChild(items);
  fab.appendChild(mainBtn);

  var backdrop = document.createElement('div');
  backdrop.className = 'mobile-sheet-backdrop';
  backdrop.id = 'mobile-sheet-backdrop';

  var sheet = document.createElement('div');
  sheet.className = 'mobile-sheet';
  sheet.id = 'mobile-sheet';

  var handle = document.createElement('div');
  handle.className = 'mobile-sheet-handle';

  var header = document.createElement('div');
  header.className = 'mobile-sheet-header';
  var title = document.createElement('span');
  title.className = 'mobile-sheet-title';
  title.id = 'mobile-sheet-title';
  var closeBtn = document.createElement('button');
  closeBtn.className = 'mobile-sheet-close';
  closeBtn.id = 'mobile-sheet-close';
  closeBtn.textContent = '\u00D7';
  header.appendChild(title);
  header.appendChild(closeBtn);

  var body = document.createElement('div');
  body.className = 'mobile-sheet-body';
  body.id = 'mobile-sheet-body';

  sheet.appendChild(handle);
  sheet.appendChild(header);
  sheet.appendChild(body);

  document.body.appendChild(fab);
  document.body.appendChild(backdrop);
  document.body.appendChild(sheet);

  // Wire up interactions
  mainBtn.addEventListener('click', function() {
    fab.classList.toggle('open');
    if (!fab.classList.contains('open')) closeSheet();
  });

  objBtn.addEventListener('click', function() {
    openSheet('objectives');
    fab.classList.remove('open');
  });

  invBtn.addEventListener('click', function() {
    openSheet('inventory');
    fab.classList.remove('open');
  });

  backdrop.addEventListener('click', closeSheet);
  closeBtn.addEventListener('click', closeSheet);

  function openSheet(type) {
    body.textContent = '';
    if (type === 'objectives') {
      title.textContent = 'Objectives';
      buildObjectivesList(body);
    } else if (type === 'inventory') {
      title.textContent = 'Inventory';
      buildInventoryList(body);
    }
    backdrop.classList.add('visible');
    sheet.classList.add('visible');
  }

  function closeSheet() {
    backdrop.classList.remove('visible');
    sheet.classList.remove('visible');
    fab.classList.remove('open');
  }

  function buildObjectivesList(container) {
    var questList = document.querySelector('.quest-log-list');
    if (!questList || !questList.children.length) {
      var p = document.createElement('p');
      p.style.cssText = 'color:#64748b;font-size:0.85rem;';
      p.textContent = 'No objectives loaded yet.';
      container.appendChild(p);
      return;
    }
    var ul = document.createElement('ul');
    ul.className = 'quest-log-list';
    Array.prototype.forEach.call(questList.children, function(li) {
      ul.appendChild(li.cloneNode(true));
    });
    container.appendChild(ul);
  }

  function buildInventoryList(container) {
    var cats = (typeof SV !== 'undefined') ? SV.CATEGORIES : null;
    if (!cats || !Object.keys(cats).length) {
      var p = document.createElement('p');
      p.style.cssText = 'color:#64748b;font-size:0.85rem;';
      p.textContent = 'No items discovered yet.';
      container.appendChild(p);
      return;
    }

    var catGrid = document.createElement('div');
    catGrid.className = 'mobile-inv-grid';

    for (var catId in cats) {
      if (!cats.hasOwnProperty(catId)) continue;
      var cat = cats[catId];
      (function(id, c) {
        var btn = document.createElement('div');
        btn.className = 'mobile-inv-item';
        btn.style.cursor = 'pointer';
        btn.style.borderColor = c.color;
        var iconEl = document.createElement('span');
        iconEl.className = 'mobile-inv-icon';
        iconEl.textContent = c.icon;
        var textEl = document.createElement('span');
        textEl.textContent = c.name;
        btn.appendChild(iconEl);
        btn.appendChild(textEl);
        btn.addEventListener('click', function() {
          // Drill down: replace sheet content with items
          title.textContent = c.icon + ' ' + c.name;
          body.textContent = '';
          showCategoryItems(body, id, c);
        });
        catGrid.appendChild(btn);
      })(catId, cat);
    }

    container.appendChild(catGrid);
  }

  function showCategoryItems(container, categoryId, cat) {
    // Back button
    var back = document.createElement('div');
    back.style.cssText = 'display:flex;align-items:center;gap:6px;cursor:pointer;color:#00b4ff;font-family:"Orbitron",monospace;font-size:10px;letter-spacing:0.08em;margin-bottom:12px;padding:4px 0;';
    back.textContent = '\u2190 All Categories';
    back.addEventListener('click', function() {
      title.textContent = 'Inventory';
      body.textContent = '';
      buildInventoryList(body);
    });
    container.appendChild(back);

    var allKeys = SV.itemsForCategory(categoryId);
    if (!allKeys || !allKeys.length) {
      var p = document.createElement('p');
      p.style.cssText = 'color:#64748b;font-size:0.85rem;padding:8px 0;';
      p.textContent = 'No items in this category.';
      container.appendChild(p);
      return;
    }

    for (var i = 0; i < allKeys.length; i++) {
      var itemId = allKeys[i];
      var def = SV.ALL_ITEMS[itemId];
      var owned = SV.inventory && SV.inventory.hasItem(itemId);

      var row = document.createElement('div');
      row.style.cssText = 'display:flex;align-items:center;gap:8px;padding:8px 10px;margin:3px 0;border-radius:6px;font-size:0.85rem;border-left:2px solid ' + (owned ? cat.color : 'transparent') + ';' + (owned ? 'color:#e2e8f0;' : 'color:#475569;opacity:0.5;');
      var nameEl = document.createElement('span');
      nameEl.textContent = owned ? def.name : '???';
      row.appendChild(nameEl);
      container.appendChild(row);
    }
  }

  // Swipe-to-dismiss
  var startY = 0;
  sheet.addEventListener('touchstart', function(e) {
    startY = e.touches[0].clientY;
  }, { passive: true });
  sheet.addEventListener('touchmove', function(e) {
    var dy = e.touches[0].clientY - startY;
    if (dy > 0) sheet.style.transform = 'translateY(' + dy + 'px)';
  }, { passive: true });
  sheet.addEventListener('touchend', function(e) {
    var dy = e.changedTouches[0].clientY - startY;
    if (dy > 80) {
      closeSheet();
    }
    sheet.style.transform = '';
  });
})();

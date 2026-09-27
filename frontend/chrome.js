// chrome.js — shared editor chrome behaviour: the command palette (see plan/UI.md §2)
// Opens from the title-bar search box, ⌘K / Ctrl+K, or ⌘⇧P / Ctrl+Shift+P.

(() => {
  const COMMANDS = [
    { label: 'Sync My Standup',              detail: 'Open the app',              icon: 'zap',            href: '/standup' },
    { label: 'Go to Home',                   detail: 'Landing page',              icon: 'home',           href: '/' },
    { label: 'Features',                     detail: 'What Standup Sync can do',  icon: 'layers',         href: '/#features' },
    { label: 'How it works',                 detail: 'The five-step pipeline',    icon: 'question',       href: '/#how-it-works' },
    { label: 'Filtering rules',              detail: 'filtering.md on GitHub',    icon: 'filter',         href: 'https://github.com/DonCastillo/standup-sync/blob/main/plan/filtering.md', external: true },
    { label: 'View source on GitHub',        detail: 'DonCastillo/standup-sync', icon: 'github',         href: 'https://github.com/DonCastillo/standup-sync', external: true },
  ];

  const trigger = document.getElementById('command-box');
  if (!trigger) return;

  // Build the palette once
  const overlay = document.createElement('div');
  overlay.className = 'palette-overlay hidden';
  overlay.innerHTML = `
    <div class="palette" role="dialog" aria-modal="true" aria-label="Command palette">
      <div class="palette-input-row">
        <span class="palette-prompt">&gt;</span>
        <input class="palette-input" type="text" placeholder="Type a command" aria-label="Type a command"
               role="combobox" aria-expanded="true" aria-controls="palette-list" autocomplete="off" spellcheck="false" />
      </div>
      <ul class="palette-list" id="palette-list" role="listbox"></ul>
    </div>`;
  document.body.appendChild(overlay);

  const input = overlay.querySelector('.palette-input');
  const list  = overlay.querySelector('.palette-list');
  let matches = COMMANDS;
  let selected = 0;
  let lastFocus = null;

  function render() {
    const q = input.value.trim().toLowerCase();
    matches = COMMANDS.filter(c => (c.label + ' ' + c.detail).toLowerCase().includes(q));
    selected = Math.min(selected, Math.max(matches.length - 1, 0));
    list.replaceChildren();
    if (!matches.length) {
      const empty = document.createElement('li');
      empty.className = 'palette-empty';
      empty.textContent = 'No matching commands';
      list.appendChild(empty);
      return;
    }
    matches.forEach((c, i) => {
      const li = document.createElement('li');
      li.className = 'palette-item' + (i === selected ? ' selected' : '');
      li.id = `palette-item-${i}`;
      li.setAttribute('role', 'option');
      li.setAttribute('aria-selected', i === selected);
      const icon = document.createElement('i');
      icon.className = `codicon codicon-${c.icon}`;
      const label = document.createElement('span');
      label.className = 'palette-label';
      label.textContent = c.label;
      const detail = document.createElement('span');
      detail.className = 'palette-detail';
      detail.textContent = c.detail;
      li.append(icon, label, detail);
      if (c.external) {
        const ext = document.createElement('i');
        ext.className = 'codicon codicon-link-external palette-ext';
        li.appendChild(ext);
      }
      li.addEventListener('mousemove', () => { if (selected !== i) { selected = i; render(); } });
      li.addEventListener('click', () => run(c));
      list.appendChild(li);
    });
    input.setAttribute('aria-activedescendant', `palette-item-${selected}`);
    list.children[selected]?.scrollIntoView({ block: 'nearest' });
  }

  function open() {
    lastFocus = document.activeElement;
    input.value = '';
    selected = 0;
    render();
    overlay.classList.remove('hidden');
    trigger.setAttribute('aria-expanded', 'true');
    input.focus();
  }

  function close() {
    overlay.classList.add('hidden');
    trigger.setAttribute('aria-expanded', 'false');
    lastFocus?.focus?.();
  }

  function run(cmd) {
    close();
    if (cmd.external) { window.open(cmd.href, '_blank', 'noopener'); return; }
    const [path, hash] = cmd.href.split('#');
    // Same page + anchor: scroll inside the editor area instead of reloading
    if (hash && (path || '/') === location.pathname) {
      document.getElementById(hash)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      history.replaceState(null, '', '#' + hash);
    } else {
      location.href = cmd.href;
    }
  }

  trigger.addEventListener('click', open);
  input.addEventListener('input', () => { selected = 0; render(); });
  input.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown') { e.preventDefault(); selected = (selected + 1) % Math.max(matches.length, 1); render(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); selected = (selected - 1 + matches.length) % Math.max(matches.length, 1); render(); }
    else if (e.key === 'Enter' && matches[selected]) { e.preventDefault(); run(matches[selected]); }
    else if (e.key === 'Escape') { e.preventDefault(); close(); }
    else if (e.key === 'Tab') { e.preventDefault(); }  // keep focus inside the dialog
  });
  overlay.addEventListener('mousedown', e => { if (e.target === overlay) close(); });

  document.addEventListener('keydown', e => {
    const mod = e.metaKey || e.ctrlKey;
    const k = e.key.toLowerCase();
    if (mod && (k === 'k' || (e.shiftKey && k === 'p'))) {
      e.preventDefault();
      overlay.classList.contains('hidden') ? open() : close();
    }
  });

  // Show the right shortcut for the platform in the title bar
  const isMac = /Mac|iPhone|iPad/.test(navigator.platform);
  const hint = trigger.querySelector('kbd');
  if (hint) hint.textContent = isMac ? '⌘K' : 'Ctrl K';
})();

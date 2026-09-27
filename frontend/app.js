// app.js — All client-side logic for Standup Sync

// ── State ──────────────────────────────────────────────────────────────────────
let currentFormats = {};       // dev tone formats (default)
let currentFormatsClient = {}; // client tone formats
let currentTone = 'dev';       // 'dev' | 'client'

// Map backend step names to UI step element IDs
const STEP_MAP = {
  clone:  'step-clone',
  filter: 'step-filter',
  llm:    'step-llm',
  group:  'step-llm',
  render: 'step-render',
};
const ALL_STEPS = ['step-clone', 'step-extract', 'step-filter', 'step-llm', 'step-render'];

// ── Date range controls ────────────────────────────────────────────────────────

function _setCustomRangeEnabled(enabled) {
  const row     = document.getElementById('custom-range-row');
  const sinceEl = document.getElementById('date-since');
  const untilEl = document.getElementById('date-until');
  row.classList.toggle('disabled', !enabled);
  sinceEl.disabled = !enabled;
  untilEl.disabled = !enabled;
}

function _validateDateRange() {
  const sinceVal = document.getElementById('date-since').value;
  const untilVal = document.getElementById('date-until').value;
  const errEl    = document.getElementById('date-range-error');
  const sinceEl  = document.getElementById('date-since');
  const untilEl  = document.getElementById('date-until');

  // Only validate when both fields have a value
  if (sinceVal && untilVal && untilVal < sinceVal) {
    errEl.classList.remove('hidden');
    untilEl.classList.add('input-error');
    return false;
  }
  errEl.classList.add('hidden');
  untilEl.classList.remove('input-error');
  sinceEl.classList.remove('input-error');
  return true;
}

// Generate is enabled only with a repo and a date range: a quick-range pill, or both custom dates (valid order)
let isGenerating = false;

function _updateGenerateBtn() {
  const repo         = document.getElementById('repo').value.trim();
  const checkedRadio = document.querySelector('input[name="quick-range"]:checked');
  const sinceVal     = document.getElementById('date-since').value;
  const untilVal     = document.getElementById('date-until').value;
  const badOrder     = sinceVal && untilVal && untilVal < sinceVal;
  const hasRange     = checkedRadio || (sinceVal && untilVal && !badOrder);
  document.getElementById('generate-btn').disabled = isGenerating || !repo || !hasRange;

  // Say what's missing instead of leaving a silent disabled button
  const missing = [];
  if (!repo) missing.push('add a repository');
  if (badOrder) missing.push('fix the date range');
  else if (!hasRange) missing.push('pick a date range');
  const hint = document.getElementById('generate-hint');
  hint.replaceChildren();
  if (!isGenerating && missing.length) {
    const icon = document.createElement('i');
    icon.className = 'codicon codicon-info';
    const sentence = missing.join(' and ');
    hint.append(icon, sentence.charAt(0).toUpperCase() + sentence.slice(1) + ' to sync.');
  }
}

// ⌘↵ / Ctrl+↵ runs the sync from anywhere on the page
const _isMac = /Mac|iPhone|iPad/.test(navigator.platform);
document.getElementById('generate-kbd').textContent = _isMac ? '⌘↵' : 'Ctrl↵';
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
    const btn = document.getElementById('generate-btn');
    if (!btn.disabled) { e.preventDefault(); btn.click(); }
  }
});

document.getElementById('repo').addEventListener('input', _updateGenerateBtn);
document.getElementById('token').addEventListener('input', e => e.target.classList.remove('input-error'));

// Radio pill click: selecting an already-checked radio deselects it (toggle off).
// mousedown must be on the <label> (the actual click target) since the <input> is hidden.
document.querySelectorAll('input[name="quick-range"]').forEach(radio => {
  const lbl = radio.closest('label');

  lbl.addEventListener('mousedown', () => {
    radio.dataset.wasChecked = radio.checked;
  });

  radio.addEventListener('change', () => {
    // Newly selected — disable and clear the date pickers
    document.getElementById('date-since').value = '';
    document.getElementById('date-until').value = '';
    document.getElementById('date-range-error').classList.add('hidden');
    document.getElementById('date-until').classList.remove('input-error');
    _setCustomRangeEnabled(false);
    _updateGenerateBtn();
  });

  lbl.addEventListener('click', () => {
    if (radio.dataset.wasChecked === 'true') {
      radio.checked = false;
      _setCustomRangeEnabled(true);
      _updateGenerateBtn();
    }
  });
});

// Typing in the custom date pickers deselects any active radio and validates range
['date-since', 'date-until'].forEach(id => {
  document.getElementById(id).addEventListener('change', () => {
    document.querySelectorAll('input[name="quick-range"]').forEach(r => r.checked = false);
    _validateDateRange();
    _updateGenerateBtn();
  });
});

// Reset button: clear everything, re-enable date pickers (nothing selected)
document.getElementById('reset-date-btn').addEventListener('click', () => {
  document.querySelectorAll('input[name="quick-range"]').forEach(r => r.checked = false);
  document.getElementById('date-since').value = '';
  document.getElementById('date-until').value = '';
  document.getElementById('date-range-error').classList.add('hidden');
  document.getElementById('date-until').classList.remove('input-error');
  _setCustomRangeEnabled(true);
  _updateGenerateBtn();
});

// On page load: no pill selected, so date pickers start enabled and Generate starts disabled
_setCustomRangeEnabled(true);
_updateGenerateBtn();

// ── Developer stats table ──────────────────────────────────────────────────────

function renderDevStats(authorStats) {
  const section = document.getElementById('dev-stats-section');
  if (!authorStats || Object.keys(authorStats).length === 0) {
    section.classList.add('hidden');
    return;
  }
  section.classList.remove('hidden');
  window._devStatsData = Object.entries(authorStats);
  window._devStatsSortMode = 'highlights';
  _renderDevRows(window._devStatsData, window._devStatsSortMode);
}

// Author and branch names come from the repo, so escape before putting them in innerHTML
function _escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function _renderDevRows(entries, sortMode) {
  const sorted = [...entries].sort((a, b) => {
    if (sortMode === 'alpha') return a[0].localeCompare(b[0]);
    return b[1].highlights - a[1].highlights || b[1].commits - a[1].commits;
  });
  const tbody = document.getElementById('dev-stats-body');
  tbody.innerHTML = '';
  for (const [name, s] of sorted) {
    const tr = document.createElement('tr');
    tr.innerHTML =
      `<td>${_escapeHtml(name)}</td>` +
      `<td class="cell-highlights">${s.highlights}</td>` +
      `<td class="cell-commits">${s.commits}</td>` +
      `<td class="cell-branches">${(s.branches || []).map(b =>
        `<span class="branch-tag"><i class="codicon codicon-git-branch"></i>${_escapeHtml(b)}</span>`).join('')}</td>`;
    tbody.appendChild(tr);
  }
}

document.getElementById('sort-toggle-btn').addEventListener('click', () => {
  const btn  = document.getElementById('sort-toggle-btn');
  const next = window._devStatsSortMode === 'highlights' ? 'alpha' : 'highlights';
  window._devStatsSortMode = next;
  btn.textContent = next === 'alpha' ? 'Sort by Highlights' : 'Sort A→Z';
  _renderDevRows(window._devStatsData, next);
});

// ── Output formats ─────────────────────────────────────────────────────────────

function _applyFormats(formats) {
  _renderCode(document.getElementById('output-slack'),   formats.slack   || '');
  _renderCode(document.getElementById('output-email'),   formats.email   || '');
  _renderCode(document.getElementById('output-standup'), formats.standup || '');
}

// Show report text like an editor: one line per row (CSS adds line numbers) with light
// Monokai syntax colouring. Display only — Copy always uses the original text.
function _renderCode(pre, text) {
  pre.replaceChildren();
  for (const line of text.split('\n')) {
    const row = document.createElement('span');
    row.className = 'code-line';
    _colourLine(row, line);
    pre.appendChild(row);
  }
}

function _span(cls, text) {
  const el = document.createElement('span');
  el.className = cls;
  el.textContent = text;
  return el;
}

function _colourLine(row, line) {
  let m;
  if ((m = line.match(/^(\s*)([•\-*])(\s.*)$/)))              row.append(m[1], _span('tok-bullet', m[2]), m[3]);
  else if (/^\*.+\*$/.test(line))                              row.append(_span('tok-strong', line));
  else if (/^_.+_$/.test(line) || /^\(?\+ \d+ minor/.test(line)) row.append(_span('tok-comment', line));
  else if ((m = line.match(/^(Subject|Period):(.*)$/)))           row.append(_span('tok-key', m[1] + ':'), m[2]);
  else if (/^[A-Z][A-Z ]+(—|$)/.test(line))                       row.append(_span('tok-heading', line));
  else if (/^[^\s].{0,40}:$/.test(line))                          row.append(_span('tok-section', line));
  else if (/^[A-Z][\w .'-]{0,40}$/.test(line) && !/[.!?]$/.test(line)) row.append(_span('tok-name', line));
  else row.append(line);
}

// Tone toggle
document.querySelectorAll('.tone-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const tone = btn.dataset.tone;
    if (tone === currentTone) return;
    currentTone = tone;
    document.querySelectorAll('.tone-btn').forEach(b => b.classList.toggle('active', b === btn));
    _applyFormats(tone === 'client' ? currentFormatsClient : currentFormats);
  });
});

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
  });
});

function copyTab(format, btn) {
  const src   = currentTone === 'client' ? currentFormatsClient : currentFormats;
  const label = btn.querySelector('span');
  navigator.clipboard.writeText(src[format] || '').then(() => {
    label.textContent = 'Copied!';
    setTimeout(() => label.textContent = 'Copy', 1500);
    _toast('success', `${format[0].toUpperCase() + format.slice(1)} update copied to clipboard.`);
  }, () => _toast('error', 'Copy failed — your browser blocked clipboard access.'));
}

// ── Result rendering ───────────────────────────────────────────────────────────

function showResult(data) {
  currentFormats       = data.formats;
  currentFormatsClient = data.formats_client || {};
  currentTone          = 'dev';

  // Reset tone toggle to dev
  document.querySelectorAll('.tone-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.tone === 'dev');
  });

  renderDevStats(data.summary.author_stats);
  _renderRawLog(data.summary.raw_log);

  _applyFormats(currentFormats);
  document.getElementById('formats-skeleton').classList.add('hidden');
  document.getElementById('formats-section').classList.remove('hidden');
  document.getElementById('results').classList.remove('hidden');
  _setStatus(`Done — ${data.summary.raw_log.length} commit(s) analysed.`);
}

// ── Raw git log ────────────────────────────────────────────────────────────────

const RAW_LOG_PREVIEW = 12;
let _rawLogLines = [];
let _rawLogExpanded = false;

// Lines look like "abc1234 [branch] Author — message"; colour hash, branch and author
function _renderRawLog(lines) {
  _rawLogLines = lines;
  _rawLogExpanded = false;
  document.getElementById('rawlog-section').classList.remove('hidden');
  document.getElementById('rawlog-count').textContent = `· ${lines.length} commit${lines.length === 1 ? '' : 's'}`;
  _drawRawLog();
}

function _drawRawLog() {
  const pre   = document.getElementById('raw-log');
  const shown = _rawLogExpanded ? _rawLogLines : _rawLogLines.slice(0, RAW_LOG_PREVIEW);
  pre.replaceChildren();
  shown.forEach((line, i) => {
    const m = line.match(/^(\S+) (\[[^\]]+\] )?(.+?) — (.*)$/);
    if (m) {
      pre.append(_span('log-hash', m[1]), ' ');
      if (m[2]) pre.append(_span('log-branch', m[2]));
      pre.append(_span('log-author', m[3]), _span('log-sep', ' — '), m[4]);
    } else {
      pre.append(line);
    }
    if (i < shown.length - 1) pre.append('\n');
  });
  const toggle = document.getElementById('rawlog-toggle');
  const hiddenCount = _rawLogLines.length - RAW_LOG_PREVIEW;
  toggle.classList.toggle('hidden', hiddenCount <= 0);
  toggle.textContent = _rawLogExpanded ? 'Show fewer' : `Show all ${_rawLogLines.length} commits (+${hiddenCount})`;
}

document.getElementById('rawlog-toggle').addEventListener('click', () => {
  _rawLogExpanded = !_rawLogExpanded;
  _drawRawLog();
});

// ── Report title ───────────────────────────────────────────────────────────────

// "YYYY-MM-DD" -> local-time Date (new Date('YYYY-MM-DD') would parse as UTC and can land on the previous day)
function _parseLocalDate(value) {
  const [y, m, d] = value.split('-').map(Number);
  return new Date(y, m - 1, d);
}

function _formatDate(date) {
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// Title for the selected range, e.g. "Accomplishments between Sep 20, 2026 - Sep 27, 2026"
function _reportTitle(checkedRadio, sinceDate, untilDate) {
  let start, end;
  if (checkedRadio) {
    // Presets look like "24 hours ago" / "7 days ago", counted back from now
    const [amount, unit] = checkedRadio.value.split(' ');
    const hours = Number(amount) * (unit.startsWith('day') ? 24 : 1);
    end   = new Date();
    start = new Date(end.getTime() - hours * 3600 * 1000);
  } else {
    start = _parseLocalDate(sinceDate);
    end   = _parseLocalDate(untilDate);
  }
  const first = _formatDate(start);
  const last  = _formatDate(end);
  return first === last ? `Accomplishments on ${first}` : `Accomplishments between ${first} - ${last}`;
}

function _setReportTitle(text) {
  const el = document.getElementById('report-title');
  const m  = text.match(/^(Accomplishments (?:between|on)) (.+)$/);
  el.replaceChildren();
  if (m) el.append(m[1] + ' ', _span('period', m[2]));
  else el.textContent = text;
}

// ── Notifications: toasts, error banner, status bar problems ──────────────────

const TOAST_ICONS = { success: 'pass-filled', error: 'error', info: 'info' };

function _toast(kind, message) {
  const toast = document.createElement('div');
  toast.className = `notification toast ${kind}`;
  toast.setAttribute('role', kind === 'error' ? 'alert' : 'status');
  const icon = document.createElement('i');
  icon.className = `codicon codicon-${TOAST_ICONS[kind]}`;
  const msg = _span('notification-message', message);
  const close = document.createElement('button');
  close.className = 'toast-close';
  close.setAttribute('aria-label', 'Dismiss');
  close.innerHTML = '<i class="codicon codicon-close"></i>';
  const dismiss = () => { toast.classList.add('leaving'); setTimeout(() => toast.remove(), 250); };
  close.addEventListener('click', dismiss);
  toast.append(icon, msg, close);
  document.getElementById('toasts').appendChild(toast);
  setTimeout(dismiss, 6000);
}

function _setProblems(count) {
  const el = document.getElementById('sb-problems');
  el.classList.toggle('problems-error', count > 0);
  el.innerHTML = `<i class="codicon codicon-error"></i> ${count} <i class="codicon codicon-warning"></i> 0`;
}

function _showError(message, code) {
  const repoAccess = code === 'repo_access';
  document.getElementById('error-title').textContent =
    repoAccess ? 'Repository access denied' : "Couldn't generate the report";
  document.getElementById('error-message').textContent = message;
  document.getElementById('error-add-token').classList.toggle('hidden', !repoAccess);
  document.getElementById('error-banner').classList.remove('hidden');
  _toast('error', repoAccess ? 'Repository access denied — see details.' : message);
  _setProblems(1);
}

function _clearError() {
  document.getElementById('error-banner').classList.add('hidden');
  _setProblems(0);
}

document.getElementById('error-add-token').addEventListener('click', () => {
  const tokenEl = document.getElementById('token');
  tokenEl.classList.add('input-error');
  tokenEl.focus();
});
document.getElementById('error-retry').addEventListener('click', () => {
  const btn = document.getElementById('generate-btn');
  if (!btn.disabled) btn.click();
  else document.getElementById('repo').focus();
});

// ── Status line ────────────────────────────────────────────────────────────────

// Messages can contain repo URLs and git/server errors, so set them as text, never HTML
function _setStatus(message, { spinner = false, error = false } = {}) {
  const status = document.getElementById('status');
  status.className = error ? 'status-line error' : 'status-line';
  status.replaceChildren();
  if (spinner) {
    const spin = document.createElement('div');
    spin.className = 'spinner';
    status.appendChild(spin);
  }
  const text = document.createElement('span');
  text.textContent = message;
  status.appendChild(text);
}

// Best-effort message from a non-stream error response
async function _errorDetail(res) {
  const fallback = `The server returned an error (${res.status}). Please try again.`;
  try {
    const body = await res.json();
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail)) return body.detail.map(d => d.msg).join('; ');  // FastAPI 422
  } catch { /* not JSON */ }
  return fallback;
}

// ── Progress: stepper, OUTPUT log, elapsed timer ──────────────────────────────

function _setStepState(id, state) {
  const el = document.getElementById(id);
  el.dataset.state = state;
  if (state === 'active') el.setAttribute('aria-current', 'step');
  else el.removeAttribute('aria-current');
}

function _log(message, kind = '') {
  const body = document.getElementById('run-log');
  const line = document.createElement('div');
  line.className = `log-line ${kind}`;
  const time = new Date().toLocaleTimeString('en-GB', { hour12: false });
  line.append(_span('log-time', `[${time}]`), _span('log-msg', message));
  body.appendChild(line);
  body.scrollTop = body.scrollHeight;
}

function _startTimer() {
  const el = document.getElementById('run-elapsed');
  const start = Date.now();
  const tick = () => {
    const secs = Math.floor((Date.now() - start) / 1000);
    el.textContent = `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}`;
  };
  tick();
  const id = setInterval(tick, 1000);
  return () => { clearInterval(id); tick(); };
}

// ── Generate button ────────────────────────────────────────────────────────────

document.getElementById('generate-btn').addEventListener('click', async () => {
  const repo  = document.getElementById('repo').value.trim();
  const token = document.getElementById('token').value.trim() || null;

  // Derive since/until from whichever date control is active
  const checkedRadio = document.querySelector('input[name="quick-range"]:checked');
  const sinceDate    = document.getElementById('date-since').value;
  const untilDate    = document.getElementById('date-until').value;
  const since = checkedRadio ? checkedRadio.value : sinceDate;
  // Equal dates = one-day range: git receives same value for --since and --until
  const until = checkedRadio ? null : untilDate;

  const btn = document.getElementById('generate-btn');

  // Reset UI: button, error, progress panel, results (title + skeleton)
  isGenerating = true;
  btn.disabled = true;
  btn.classList.add('running');
  btn.querySelector('.btn-label').textContent = 'Syncing your standup…';
  _updateGenerateBtn();
  _setStatus('');
  _clearError();
  document.getElementById('empty-state').classList.add('hidden');
  document.getElementById('progress-panel').classList.remove('hidden');
  document.getElementById('run-log').replaceChildren();
  ALL_STEPS.forEach(id => _setStepState(id, 'pending'));
  _setReportTitle(_reportTitle(checkedRadio, sinceDate, untilDate));
  document.getElementById('results').classList.remove('hidden');
  document.getElementById('formats-skeleton').classList.remove('hidden');
  // Hide last run's outputs, stats and log until this run's arrive
  document.getElementById('formats-section').classList.add('hidden');
  document.getElementById('dev-stats-section').classList.add('hidden');
  document.getElementById('rawlog-section').classList.add('hidden');
  _log('Starting…');
  const stopTimer = _startTimer();
  // Stacked layout (tablet/phone): bring the progress tracker into view
  if (window.matchMedia('(max-width: 1000px)').matches) {
    document.getElementById('progress-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  let gotRawLog = false;

  let activeStep = null;

  function setStep(stepId) {
    if (activeStep && activeStep !== stepId) _setStepState(activeStep, 'done');
    _setStepState(stepId, 'active');
    activeStep = stepId;
  }

  function finishSteps(ok) {
    if (ok) ALL_STEPS.forEach(id => _setStepState(id, 'done'));
    else if (activeStep) _setStepState(activeStep, 'error');
    document.getElementById('formats-skeleton').classList.add('hidden');
    // Nothing to show if the run failed before the raw log arrived
    if (!ok && !gotRawLog) document.getElementById('results').classList.add('hidden');
  }

  function fail(message, code) {
    finishSteps(false);
    _log(message, 'err');
    _showError(message, code);
    document.getElementById('sb-run').textContent = '';
  }

  try {
    const res = await fetch('/api/generate', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ repo, since, until, token }),
    });

    // A non-stream response (422, 500, proxy error) has no events to read
    if (!res.ok || !res.body) throw new Error(await _errorDetail(res));

    // Read the SSE stream manually
    let finished  = false;  // set by a result or error event
    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by double newlines
      const frames = buffer.split('\n\n');
      buffer = frames.pop(); // keep incomplete frame in buffer

      for (const frame of frames) {
        if (!frame.trim()) continue;
        const eventMatch = frame.match(/^event: (\w+)/m);
        const dataMatch  = frame.match(/^data: (.+)/m);
        if (!eventMatch || !dataMatch) continue;

        const eventType = eventMatch[1];
        const payload   = JSON.parse(dataMatch[1]);

        if (eventType === 'progress') {
          const stepId = STEP_MAP[payload.step] || null;
          if (stepId) setStep(stepId);
          _log(payload.message);
          document.getElementById('sb-run').textContent = payload.message;

        } else if (eventType === 'raw_log') {
          // Show raw log immediately — before LLM finishes
          gotRawLog = true;
          _renderRawLog(payload.lines);
          setStep('step-extract');
          _log(`Found ${payload.lines.length} commit${payload.lines.length === 1 ? '' : 's'} across all branches`);

        } else if (eventType === 'result') {
          finished = true;
          finishSteps(true);
          showResult(payload);
          const n = payload.summary.raw_log.length;
          _log(`Done — ${n} commit${n === 1 ? '' : 's'} analysed`, 'ok');
          document.getElementById('sb-run').textContent = '✓ Synced';
          _toast('success', 'Standup synced — your updates are ready.');

        } else if (eventType === 'error') {
          finished = true;
          fail(payload.detail, payload.code);
          if (payload.code === 'repo_access') {
            const tokenEl = document.getElementById('token');
            tokenEl.classList.add('input-error');
            tokenEl.focus();
          }
        }
      }
    }
    if (!finished) throw new Error('The connection closed before the report finished. Please try again.');

  } catch (err) {
    fail(err.message);
  } finally {
    stopTimer();
    isGenerating = false;
    btn.classList.remove('running');
    btn.querySelector('.btn-label').textContent = 'Sync My Standup';
    _updateGenerateBtn();
  }
});

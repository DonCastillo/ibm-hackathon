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
  });

  lbl.addEventListener('click', () => {
    if (radio.dataset.wasChecked === 'true') {
      radio.checked = false;
      _setCustomRangeEnabled(true);
    }
  });
});

// Typing in the custom date pickers deselects any active radio and validates range
['date-since', 'date-until'].forEach(id => {
  document.getElementById(id).addEventListener('change', () => {
    document.querySelectorAll('input[name="quick-range"]').forEach(r => r.checked = false);
    _validateDateRange();
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
});

// On page load: no pill selected, so date pickers start enabled
_setCustomRangeEnabled(true);

// ── Developer stats table ──────────────────────────────────────────────────────

function renderDevStats(authorStats) {
  const section = document.getElementById('dev-stats-section');
  if (!authorStats || Object.keys(authorStats).length === 0) {
    section.classList.add('hidden');
    return;
  }
  section.classList.remove('hidden');
  window._devStatsData = Object.entries(authorStats);
  window._devStatsSortMode = 'commits';
  _renderDevRows(window._devStatsData, window._devStatsSortMode);
}

function _renderDevRows(entries, sortMode) {
  const sorted = [...entries].sort((a, b) => {
    if (sortMode === 'alpha') return a[0].localeCompare(b[0]);
    return b[1].commits - a[1].commits;
  });
  const tbody = document.getElementById('dev-stats-body');
  tbody.innerHTML = '';
  for (const [name, s] of sorted) {
    const tr = document.createElement('tr');
    tr.innerHTML =
      `<td>${name}</td>` +
      `<td>${s.commits}</td>` +
      `<td class="cell-added">${s.files_added}</td>` +
      `<td class="cell-deleted">${s.files_deleted}</td>` +
      `<td>${s.files_modified}</td>` +
      `<td class="cell-added">+${s.lines_added}</td>` +
      `<td class="cell-deleted">-${s.lines_deleted}</td>` +
      `<td class="cell-updated">${s.lines_updated}</td>`;
    tbody.appendChild(tr);
  }
}

document.getElementById('sort-toggle-btn').addEventListener('click', () => {
  const btn  = document.getElementById('sort-toggle-btn');
  const next = window._devStatsSortMode === 'commits' ? 'alpha' : 'commits';
  window._devStatsSortMode = next;
  btn.textContent = next === 'alpha' ? 'Sort by Commits' : 'Sort A→Z';
  _renderDevRows(window._devStatsData, next);
});

// ── Output formats ─────────────────────────────────────────────────────────────

function _applyFormats(formats) {
  document.getElementById('output-slack').textContent   = formats.slack   || '';
  document.getElementById('output-email').textContent   = formats.email   || '';
  document.getElementById('output-standup').textContent = formats.standup || '';
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

function copyTab(format) {
  const src = currentTone === 'client' ? currentFormatsClient : currentFormats;
  navigator.clipboard.writeText(src[format] || '').then(() => {
    const btn = event.target;
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy', 1500);
  });
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
  document.getElementById('raw-log').textContent      = data.summary.raw_log.join('\n');
  document.getElementById('summary-preview').textContent = data.formats.slack;

  const blockersSection = document.getElementById('blockers-section');
  const blockersList    = document.getElementById('blockers-list');
  blockersList.innerHTML = '';
  if (data.summary.blockers.length > 0) {
    blockersSection.classList.remove('hidden');
    data.summary.blockers.forEach(b => {
      const li = document.createElement('li');
      if (b.reason === 'repeated_changes') {
        li.textContent = `${b.target} was modified in 3+ commits — possible rework or ongoing issue.`;
      } else {
        li.textContent = `Commit ${b.target.slice(0, 7)} flagged: "${b.message}" — possible struggle.`;
      }
      blockersList.appendChild(li);
    });
  } else {
    blockersSection.classList.add('hidden');
  }

  _applyFormats(currentFormats);
  document.getElementById('results').classList.remove('hidden');
  document.getElementById('status').innerHTML =
    `Done — ${data.summary.raw_log.length} commit(s) analysed.`;
}

// ── Generate button ────────────────────────────────────────────────────────────

document.getElementById('generate-btn').addEventListener('click', async () => {
  const repo  = document.getElementById('repo').value.trim();
  const token = document.getElementById('token').value.trim() || null;

  // Derive since/until from whichever date control is active
  const checkedRadio = document.querySelector('input[name="quick-range"]:checked');
  const sinceDate    = document.getElementById('date-since').value;
  const untilDate    = document.getElementById('date-until').value;
  const since = checkedRadio ? checkedRadio.value : (sinceDate || '30 days ago');
  // Equal dates = one-day range: git receives same value for --since and --until
  const until = checkedRadio ? null : (untilDate || null);

  const btn     = document.getElementById('generate-btn');
  const status  = document.getElementById('status');
  const stepsEl = document.getElementById('progress-steps');

  if (!repo) {
    status.innerHTML = 'Please enter a repository path or URL.';
    status.className = 'error';
    return;
  }

  // Block submit if custom date range is invalid
  if (!checkedRadio && !_validateDateRange()) { return; }

  // Reset UI
  btn.disabled     = true;
  btn.textContent  = 'Generating…';
  status.className = '';
  status.innerHTML = '<div class="spinner"></div><span>Starting…</span>';
  document.getElementById('results').classList.add('hidden');
  stepsEl.classList.remove('hidden');
  ALL_STEPS.forEach(s => { document.getElementById(s).className = ''; });

  let activeStep = null;

  function setStep(stepId) {
    if (activeStep && activeStep !== stepId) {
      document.getElementById(activeStep).className = 'done';
    }
    document.getElementById(stepId).className = 'active';
    activeStep = stepId;
  }

  function finishSteps() {
    ALL_STEPS.forEach(s => { document.getElementById(s).className = 'done'; });
    stepsEl.classList.add('hidden');
  }

  try {
    const res = await fetch('/api/generate', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ repo, since, until, token }),
    });

    // Read the SSE stream manually
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
          status.innerHTML = `<div class="spinner"></div><span>${payload.message}</span>`;

        } else if (eventType === 'raw_log') {
          // Show raw log immediately — before LLM finishes
          document.getElementById('raw-log').textContent = payload.lines.join('\n');
          document.getElementById('results').classList.remove('hidden');
          setStep('step-extract');

        } else if (eventType === 'result') {
          finishSteps();
          showResult(payload);

        } else if (eventType === 'error') {
          finishSteps();
          status.innerHTML = `Error: ${payload.detail}`;
          status.className = 'error';
        }
      }
    }

  } catch (err) {
    finishSteps();
    status.innerHTML = `Error: ${err.message}`;
    status.className = 'error';
  } finally {
    btn.disabled    = false;
    btn.textContent = 'Generate';
  }
});

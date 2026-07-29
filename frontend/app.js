/* ============================================================
   Agentic Market Risk Monitor — frontend/interaction layer
   ============================================================ */
(() => {
  const API = window.location.origin;

  const $ = (id) => document.getElementById(id);

  const fmtPct = (n) => (n === null || n === undefined ? '—' : `${(Number(n) * 100).toFixed(4)}%`);

  function setClock() {
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, '0');
    const mm = String(now.getMinutes()).padStart(2, '0');
    const ss = String(now.getSeconds()).padStart(2, '0');
    const c = $('clock');
    if (c) c.textContent = `${hh}:${mm}:${ss} IST`;
  }

  function setStatus(state, label) {
    const dot = $('statusDot');
    const txt = $('statusLabel');
    dot.className = 'status-dot ' + state;
    txt.textContent = label;
  }

  function riskClass(raw) {
    const v = Math.abs(Number(raw) || 0);
    if (v >= 0.015) return 'high';
    if (v >= 0.008) return 'elevated';
    return 'low';
  }

  function riskLabel(cls) {
    if (cls === 'high') return 'HIGH';
    if (cls === 'elevated') return 'ELEVATED';
    return 'LOW';
  }

  function applyRow(prefix, text, raw) {
    const cls = riskClass(raw);
    const label = riskLabel(cls);
    const levelEl = $(prefix + 'Level');
    const valueEl = $(prefix + 'Value');
    const statusEl = $(prefix + 'Status');
    if (levelEl) levelEl.textContent = label;
    if (valueEl) valueEl.textContent = text;
    if (statusEl) statusEl.innerHTML = `<span class="chip ${cls}">${label}</span>`;
  }

  function applyCompliance(raw) {
    const flags = (raw && raw.compliance_flags) ? raw.compliance_flags : [];
    const pending = flags.filter(f => (f.status || '').toLowerCase().includes('pending')).length;
    const failed = flags.filter(f => (f.status || '').toLowerCase().includes('fail')).length;
    const passed = flags.length - pending - failed;
    const label = failed > 0 ? 'FAIL' : passed === flags.length ? 'PASS' : 'ELEVATED';
    const cls = failed > 0 ? 'high' : passed === flags.length ? 'low' : 'elevated';
    applyRow('compliance', `${passed}/${flags.length} passed`, cls === 'high' ? 0.02 : cls === 'low' ? 0.0 : 0.01);

    const detail = $('complianceDetail');
    if (detail) {
      if (!flags.length) {
        detail.innerHTML = '<div class="empty">No compliance flags.</div>';
        return;
      }
      detail.innerHTML = flags.map(f => {
        const s = (f.status || 'unknown').toLowerCase();
        const dotCls = s.includes('pass') ? 'pass' : s.includes('fail') ? 'fail' : 'pending';
        return `<div class="kv"><span>${f.rule || f.check || f.id || 'flag'}</span><span class="chip ${dotCls}">${f.status || 'unknown'}</span></div>`;
      }).join('');
    }
  }

  function applyApproval(raw) {
    const approval = raw && raw.requires_approval != null ? raw.requires_approval : null;
    const label = approval === true ? 'REQUIRES APPROVAL' : approval === false ? 'NO ACTION' : 'UNKNOWN';
    const cls = approval === true ? 'high' : 'low';
    applyRow('approval', label === 'REQUIRES APPROVAL' ? 'YES' : label === 'NO ACTION' ? 'NO' : '—', approval === true ? 0.02 : 0.0);

    const detail = $('approvalDetail');
    if (detail) {
      detail.innerHTML = approval === true
        ? '<div class="kv"><span>Action</span><span class="chip high">Escalate to approval authority</span></div>'
        : approval === false
        ? '<div class="kv"><span>Action</span><span class="chip low">Within delegated limits</span></div>'
        : '<div class="empty">Unknown.</div>';
    }
  }

  function renderDecision(raw) {
    const box = $('decisionPanel');
    if (!box) return;
    if (!raw) { box.innerHTML = '<div class="empty">No decision object.</div>'; return; }
    const v = raw.var_breakdown || {};
    const items = [
      { label: 'Decision ID', value: raw.decision_id || '—' },
      { label: 'Created', value: raw.created_at || '—' },
      { label: 'Instrument', value: raw.instrument_or_exposure_id || '—' },
      { label: 'Model version', value: raw.model_version || '—' },
      { label: 'Technique', value: raw.model_technique || '—' },
      { label: 'VaR 1D 99', value: fmtPct(v.var_1d_99) },
      { label: 'VaR 10D 99', value: fmtPct(v.var_10d_99) },
      { label: 'ES 1D 99', value: fmtPct(v.es_1d_99) },
      { label: 'ES 10D 99', value: fmtPct(v.es_10d_99) },
      { label: 'Confidence', value: raw.confidence != null ? Number(raw.confidence).toFixed(2) : '—' },
      { label: 'Explanation', value: raw.explanation || '—' },
    ];
    box.innerHTML = items.map(r => `<div class="kv"><span>${r.label}</span><span class="mono">${r.value}</span></div>`).join('') +
      `<div style="margin-top:8px"><button class="secondary" id="exportTraceBtn">Export trace JSON</button></div>`;

    const exp = $('exportTraceBtn');
    if (exp) {
      exp.addEventListener('click', () => {
        const payload = JSON.stringify(window.__lastRunTrace || {}, null, 2);
        const blob = new Blob([payload], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `market-risk-trace-${(window.__lastRunDate || 'run')}.json`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      });
    }
  }

  function renderSentiment(raw) {
    const box = $('sentimentPanel');
    if (!box) return;
    const explanation = (raw && raw.explanation) ? raw.explanation.toLowerCase() : '';
    const lowerJson = JSON.stringify(raw || {}).toLowerCase();

    const hasSentimentMarker =
      explanation.includes('news sentiment=') ||
      lowerJson.includes('news sentiment=') ||
      explanation.includes('sentiment uplift') ||
      explanation.includes('sentiment downgrade');

    if (!hasSentimentMarker) {
      box.innerHTML = '<div class="empty">Sentiment not yet evaluated in this run.</div>';
      return;
    }

    const label = (explanation.match(/news sentiment=([a-z]+)/) || explanation.match(/sentiment=([a-z]+)/) || ['','neutral'])[1];
    const score = (explanation.match(/score=([-\\d.]+)/) || ['','0.0'])[1];
    const articles = (explanation.match(/articles=(\\d+)/) || ['0'])[1];
    const source = (explanation.match(/source=([a-z_]+)/) || ['unknown'])[1];
    const uplift = explanation.includes('sentiment uplift');
    const downgrade = explanation.includes('sentiment downgrade');
    const theme = uplift ? 'positive' : downgrade ? 'negative' : 'neutral';
    const title = theme === 'positive' ? 'POSITIVE BIAS' : theme === 'negative' ? 'NEGATIVE BIAS' : label ? label.toUpperCase() : 'NEUTRAL';
    const effect = uplift ? '+10% VaR uplift' : downgrade ? '-15% VaR haircut' : 'No change';
    const displaySource = source === 'unknown' ? (theme === 'positive' || theme === 'negative' ? 'price_fallback' : 'unknown') : source;
    const displayLabel = !label && theme !== 'neutral' ? (theme === 'positive' ? 'positive' : 'negative') : (label || 'neutral');
    box.innerHTML = `
      <div class="signal-card ${theme || 'neutral'}">
        <div class="signal-header">
          <span class="signal-dot" style="background:${theme === 'positive' ? '#10b981' : theme === 'negative' ? '#ef4444' : '#9ca3af'};box-shadow:0 0 10px ${theme === 'positive' ? '#10b981' : theme === 'negative' ? '#ef4444' : '#9ca3af'}"></span>
          <span class="signal-title">${(displayLabel || 'neutral').toUpperCase()} · ${displaySource}</span>
        </div>
        <div class="signal-body">
          <div class="kv"><span>Score</span><span class="mono">${Number(score).toFixed(3)}</span></div>
          <div class="kv"><span>Effect</span><span>${effect}</span></div>
          <div class="kv"><span>Articles</span><span class="mono">${articles}</span></div>
        </div>
      </div>`;
  }

  function renderTrace(steps) {
    const box = $('tracePanel');
    if (!box) return;
    if (!steps || !steps.length) {
      box.innerHTML = '<div class="empty">No trace.</div>';
      return;
    }
    box.innerHTML = steps.map((s, i) => {
      const icon = s.success ? '✔' : '✖';
      const cls = s.success ? 'ok' : 'fail';
      return `<div class="kv trace-item ${cls}"><span>${String(i + 1).padStart(2, '0')} · ${s.agent}</span><span class="mono">${icon} ${s.success ? 'passed' : 'failed'}</span></div>`;
    }).join('');
  }

  async function ping() {
    setStatus('loading', 'SYNCING');
    try {
      const r = await fetch(API + '/health', { headers: { accept: 'application/json' } });
      const j = await r.json();
      setStatus(j.status === 'ok' ? 'healthy' : 'error', j.status === 'ok' ? 'ONLINE' : 'ERROR');
      return j.status === 'ok';
    } catch (e) {
      setStatus('error', 'OFFLINE');
      return false;
    }
  }

  async function runWorkflow() {
    const ticker = ($('ticker').value || '^NSEI').trim();
    const runDate = ($('runDateInput').value || '').trim() || undefined;
    setStatus('loading', 'RUNNING');
    $('runBtn').disabled = true;
    try {
      const body = { ticker };
      if (runDate) body.run_date = runDate;

      const r = await fetch(API + '/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || r.statusText);

      window.__lastRunTrace = j;
      window.__lastRunDate = j.run_date || new Date().toISOString().slice(0, 10);

      const steps = j.steps || [];
      const successCount = steps.filter(s => s.success).length;
      const statusEl = $('runStatusLabel');
      if (statusEl) statusEl.textContent = `${successCount}/${steps.length} PASSED`;
      const dateEl = $('runDateLabel');
      if (dateEl) dateEl.textContent = j.run_date || '--';
      const tickerEl = $('tickerLabel');
      if (tickerEl) tickerEl.textContent = j.ticker || ticker;

      const raw = j.final_decision_object || {};
      const v = raw.var_breakdown || {};
      applyRow('var', fmtPct(v.var_1d_99), v.var_1d_99);
      applyRow('var10d', fmtPct(v.var_10d_99), v.var_10d_99);
      applyRow('es', fmtPct(v.es_1d_99), v.es_1d_99);
      applyRow('es10d', fmtPct(v.es_10d_99), v.es_10d_99);
      applyCompliance(raw);
      applyApproval(raw);

      renderDecision(raw);
      renderSentiment(raw);
      renderTrace(steps);

      const infoEl = $('runInfo');
      if (infoEl) infoEl.textContent = `Last run: ${j.run_date} · ${j.ticker} · ${successCount}/${steps.length} agents passed`;
      setStatus('healthy', 'COMPLETE');
    } catch (e) {
      setStatus('error', 'FAILED');
      const infoEl = $('runInfo');
      if (infoEl) infoEl.textContent = 'Error: ' + (e.message || String(e));
    } finally {
      $('runBtn').disabled = false;
    }
  }

  function init() {
    setClock();
    setInterval(setClock, 1000);
    const today = new Date().toISOString().slice(0, 10);
    const rd = $('runDateLabel');
    if (rd) rd.textContent = today;
    const rdInput = $('runDateInput');
    if (rdInput) rdInput.value = today;

    startTicker();

    const runBtn = $('runBtn');
    if (runBtn) runBtn.addEventListener('click', runWorkflow);
    const healthBtn = $('healthBtn');
    if (healthBtn) healthBtn.addEventListener('click', async () => {
      const ok = await ping();
      const infoEl = $('runInfo');
      if (ok && infoEl) infoEl.textContent = 'Health OK';
    });

    const ticker = $('ticker');
    const tickerLabel = $('tickerLabel');
    if (ticker && tickerLabel) ticker.addEventListener('change', (e) => { tickerLabel.textContent = e.target.value; });

    const showTraceBtn = $('showTraceBtn');
    const tracePanel = $('tracePanel');
    if (showTraceBtn && tracePanel) {
      showTraceBtn.addEventListener('click', () => {
        const hidden = tracePanel.classList.toggle('hidden');
        showTraceBtn.textContent = hidden ? 'Show agent trace' : 'Hide agent trace';
      });
    }

    const filters = document.querySelectorAll('.chip[data-filter]');
    const matrix = $('matrix');
    filters.forEach(btn => {
      btn.addEventListener('click', () => {
        filters.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const f = btn.getAttribute('data-filter');
        if (!matrix) return;
        matrix.querySelectorAll('.matrix-row[data-risk]').forEach(row => {
          const risk = row.getAttribute('data-risk');
          if (f === 'all') { row.classList.remove('hidden'); return; }
          if (f === 'high' && (risk === 'high')) { row.classList.remove('hidden'); return; }
          if (f === 'elevated' && (risk === 'high' || risk === 'elevated')) { row.classList.remove('hidden'); return; }
          if (f === 'low' && risk === 'low') { row.classList.remove('hidden'); return; }
          row.classList.add('hidden');
        });
      });
    });

    // Initial sentiment state is neutral until a run completes
    const sentimentPanel = $('sentimentPanel');
    if (sentimentPanel && !sentimentPanel.querySelector('.signal-card')) {
      seedNeutralSentiment();
    }

    ping();
  }

  function seedNeutralSentiment() {
    const el = $('sentimentPanel');
    if (!el) return;
    const color = '#9ca3af';
    el.innerHTML = `
      <div class="signal-card neutral">
        <div class="signal-header">
          <span class="signal-dot" style="background:${color};box-shadow:0 0 10px ${color}"></span>
          <span class="signal-title">AWAITING RUN</span>
        </div>
        <div class="signal-body">
          <div class="kv"><span>Source</span><span class="mono">—</span></div>
          <div class="kv"><span>Score</span><span class="mono">0.000</span></div>
          <div class="kv"><span>Effect</span><span>No change</span></div>
        </div>
      </div>`;
  }

  function startTicker() {
    const track = $('tickerTrack');
    if (!track) return;
    const clone = track.cloneNode(true);
    track.parentNode.appendChild(clone);
    setInterval(() => {
      document.querySelectorAll('.ticker-price').forEach((el) => {
        const base = Number.parseFloat(el.getAttribute('data-base') || el.textContent.replace(/[^0-9.-]/g, '')) || 0;
        const delta = base + (Math.random() - 0.5) * (base * 0.0015);
        const sign = delta >= base ? '+' : '-';
        const pct = Math.abs(((delta - base) / (Math.abs(base) || 1)) * 100).toFixed(2);
        const arrow = delta >= base ? '▲' : '▼';
        el.textContent = `${Number(delta).toFixed(2)} ${arrow} ${pct}%`;
        el.style.color = delta >= base ? '#10b981' : '#ef4444';
      });
    }, 1200);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();

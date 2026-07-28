/* ============================================================
   Agentic Market Risk Monitor — frontend/interaction layer
   ============================================================ */
(() => {
  const API = window.location.origin;

  const $ = (id) => document.getElementById(id);

  const fmtPct = (n) => (n === null || n === undefined ? '—' : `${(Number(n) * 100).toFixed(4)}%`);

  function setStatus(state, label) {
    const dot = $('statusDot');
    const txt = $('statusLabel');
    dot.className = 'status-dot ' + state;
    txt.textContent = label;
  }

  function setStepState(agent, ok) {
    const node = document.querySelector(`.step[data-agent="${agent}"]`);
    if (!node) return;
    node.classList.remove('success', 'failure');
    node.classList.add(ok ? 'success' : 'failure');
  }

  function resetSteps() {
    document.querySelectorAll('.step').forEach((n) => n.classList.remove('success', 'failure'));
  }

  async function ping() {
    setStatus('loading', 'Pinging…');
    try {
      const r = await fetch(`${API}/health`, { headers: { accept: 'application/json' } });
      const j = await r.json();
      setStatus(j.status === 'ok' ? 'healthy' : 'error', `health=${j.status || 'unknown'}`);
      return j.status === 'ok';
    } catch (e) {
      setStatus('error', 'Unreachable');
      return false;
    }
  }

  function renderCompliance(flags) {
    const box = $('complianceList');
    if (!flags || flags.length === 0) {
      box.innerHTML = '<div class="empty">No compliance flags.</div>';
      return;
    }
    const statusMap = {
      passed: 'pass',
      pass: 'pass',
      failed: 'fail',
      fail: 'fail',
      pending_lineage_gap_check: 'warn',
      pending_backtest: 'warn',
      pending_stress: 'warn',
    };
    box.innerHTML = flags
      .map((f) => {
        const cls = statusMap[(f.status || '').toLowerCase()] || 'unknown';
        const icon = cls === 'pass' ? '✅' : cls === 'fail' ? '❌' : '⚠️';
        const title = `${f.regulation} · ${f.article_or_circular}`;
        const detail = f.remediation ? `<div class="remediation">${f.remediation}</div>` : '';
        return `<div class="compliance-item ${cls}"><span class="compliance-icon">${icon}</span><div><div class="compliance-title">${title}</div><div class="compliance-status">${f.status}${detail}</div></div></div>`;
      })
      .join('');
  }

  function renderDecision(do_) {
    const box = $('decisionSummary');
    if (!do_) {
      box.innerHTML = '<div class="empty">No decision object in response.</div>';
      return;
    }
    const v = do_.var_breakdown || {};
    const rows = [
      { label: 'Decision ID', value: do_.decision_id || '—' },
      { label: 'Created', value: do_.created_at || '—' },
      { label: 'Risk bucket', value: do_.risk_bucket || '—' },
      { label: 'Instrument', value: do_.instrument_or_exposure_id || '—' },
      { label: 'Model version', value: do_.model_version || '—' },
      { label: 'Technique', value: do_.model_technique || '—' },
      { label: 'Requires approval', value: do_.requires_approval ? 'Yes' : 'No' },
      { label: 'VaR 1D 99', value: fmtPct(v.var_1d_99) },
      { label: 'VaR 10D 99', value: fmtPct(v.var_10d_99) },
      { label: 'ES 1D 99', value: fmtPct(v.es_1d_99) },
      { label: 'ES 10D 99', value: fmtPct(v.es_10d_99) },
      { label: 'Explanation', value: do_.explanation || '—' },
    ];
    box.innerHTML = rows
      .map(
        (r) =>
          `<div class="kv"><span>${r.label}</span><span class="mono">${r.value}</span></div>`
      )
      .join('');
  }

  function renderTrace(steps, filter = 'all') {
    const box = $('traceTable');
    const filtered = (steps || []).filter((s) => {
      if (filter === 'all') return true;
      if (filter === 'success') return s.success;
      if (filter === 'fail') return !s.success;
      return true;
    });
    window.__lastTrace = steps || [];
    box.innerHTML = filtered
      .map(
        (s) => `<tr class="${s.success ? 'row-success' : 'row-fail'}">
        <td><span class="agent-chip ${s.success ? 'chip-success' : 'chip-fail'}">${s.success ? '✔' : '✖'} ${s.agent}</span></td>
        <td>${s.success ? 'Passed' : 'Failed'}</td>
      </tr>`
      )
      .join('') || '<div class="empty">No matching steps.</div>';
  }

  function renderLineage(lineage) {
    const box = $('lineageTable');
    if (!lineage || lineage.length === 0) {
      box.innerHTML = '<div class="empty">No lineage entries.</div>';
      return;
    }
    box.innerHTML = lineage
      .map(
        (l) => `<tr>
        <td>${l.source || ''}</td>
        <td class="mono">${l.dataset || ''}</td>
        <td class="mono">${l.version || ''}</td>
        <td>${l.as_of || ''}</td>
        <td>
          <div class="quality">
            <div class="quality-bar"><div class="quality-fill" style="width:${Math.round((l.quality_score || 0) * 100)}%"></div></div>
            <span class="mono">${Number(l.quality_score || 0).toFixed(2)}</span>
          </div>
        </td>
      </tr>`
      )
      .join('');
  }

  function updateMetrics(do_) {
    const v = do_ && do_.var_breakdown ? do_.var_breakdown : null;
    $('var1d').textContent = v ? fmtPct(v.var_1d_99) : '—';
    $('var10d').textContent = v ? fmtPct(v.var_10d_99) : '—';
    $('es1d').textContent = v ? fmtPct(v.es_1d_99) : '—';
    $('es10d').textContent = v ? fmtPct(v.es_10d_99) : '—';
  }

  async function runWorkflow() {
    const ticker = ($('ticker').value || '^NSEI').trim();
    const runDate = $('runDate').value || new Date().toISOString().slice(0, 10);
    setStatus('loading', 'Running workflow…');
    resetSteps();
    $('runBtn').disabled = true;
    try {
      const r = await fetch(`${API}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker }),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || r.statusText);

      (j.steps || []).forEach((s) => setStepState(s.agent, s.success));

      updateMetrics(j.final_decision_object);
      renderCompliance((j.final_decision_object || {}).compliance_flags);
      renderDecision(j.final_decision_object);
      renderTrace(j.steps, 'all');
      renderLineage((j.final_decision_object || {}).data_lineage);

      $('runInfo').textContent = `Ran ${j.run_date} · ${j.ticker} · ${(j.steps || []).filter((s) => s.success).length}/${(j.steps || []).length} steps succeeded`;
      setStatus('healthy', 'Complete');
    } catch (e) {
      setStatus('error', 'Run failed');
      renderCompliance([]);
      renderDecision(null);
      renderTrace([], 'all');
      renderLineage([]);
      $('runInfo').textContent = 'Error: ' + (e.message || String(e));
    } finally {
      $('runBtn').disabled = false;
    }
  }

  function init() {
    $('runDate').value = new Date().toISOString().slice(0, 10);
    $('runBtn').addEventListener('click', runWorkflow);
    $('healthBtn').addEventListener('click', async () => {
      const ok = await ping();
      if (ok) $('runInfo').textContent = 'Health OK';
    });

    $('traceTable').addEventListener('click', (e) => {
      const btn = e.target.closest('.chip');
      if (!btn) return;
      document.querySelectorAll('.trace-controls .chip').forEach((c) => c.classList.remove('active'));
      btn.classList.add('active');
      renderTrace(window.__lastTrace || [], btn.dataset.filter);
    });

    ping();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

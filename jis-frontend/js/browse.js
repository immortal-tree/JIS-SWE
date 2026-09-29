(function () {
  const { $, $$, esc, date, money, toast, onSubmit, table, api, icon } = JIS;
  const me = JIS.guard(['JUDGE', 'LAWYER']);
  if (!me) return;
  const lawyer = me.role === 'LAWYER';
  let fee = null;

  if (lawyer) {
    $$('[data-lawyer]').forEach((n) => (n.hidden = false));
    api.getFee().then((f) => {
      fee = f.feePerView;
      $('#fee-note').innerHTML = `${icon('rupee')}<span>Searching is free. Opening a case's full record costs <b>${money(fee)}</b>, added to your balance.</span>`;
    }).catch(() => {});
  }

  // ---------- search ----------
  const searchForm = $('#search-form');
  onSubmit(searchForm, async ({ q }) => {
    const rows = await api.search(q);
    const out = $('#results');
    if (!rows.length) {
      out.innerHTML = `<p class="empty">No closed cases match “${esc(q)}”. Try fewer or different keywords.</p>`;
      return;
    }
    out.innerHTML = `
      <p class="small muted">${rows.length} closed case${rows.length === 1 ? '' : 's'} match “${esc(q)}”</p>
      <div class="results">${rows.map((r, i) => `
        <div class="result" style="--i:${Math.min(i, 20)}">
          <span class="ti">${icon('fileText')}</span>
          <div>
            <b>${esc(r.crimeType)}</b>
            <div class="sub"><span class="mono">${esc(r.cin)}</span><span>Judgment ${date(r.judgmentDate)}</span></div>
          </div>
          <button type="button" class="${lawyer ? '' : 'ghost'}" data-open="${esc(r.cin)}">${icon(lawyer ? 'lock' : 'eye')}${lawyer ? `View · ${money(fee)}` : 'View record'}</button>
        </div>`).join('')}
      </div>`;
  });
  $$('[data-q]').forEach((b) => b.addEventListener('click', () => {
    searchForm.elements.q.value = b.dataset.q;
    searchForm.requestSubmit();
  }));

  // ---------- case dialog ----------
  const dlg = $('#case-dialog');
  const body = $('#dlg-body');

  async function show(cin) {
    body.innerHTML = '<p class="muted">Loading the record…</p>';
    const c = await api.getCase(cin);
    $('#dlg-title').innerHTML = `Case <span class="mono small muted">${esc(c.cin)}</span>`;
    body.innerHTML =
      (c.chargedFee != null ? `<div class="notice">${icon('receipt')}<div>${money(c.chargedFee)} added to your balance. Balance due: <b>${money(c.balanceDue)}</b>.</div></div>` : '') +
      JIS.caseHead(c) + JIS.caseRecord(c);
  }

  $('#results').addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-open]');
    if (!b) return;
    const cin = b.dataset.open;
    $('#dlg-title').innerHTML = `Case <span class="mono small muted">${esc(cin)}</span>`;
    if (lawyer) {
      body.innerHTML = `
        <div class="confirm">
          <span class="ti">${icon('rupee')}</span>
          <h2>View the full record?</h2>
          <p class="muted">Opening case <span class="mono">${esc(cin)}</span> adds <b>${money(fee)}</b> to your balance.</p>
          <div class="actions">
            <form method="dialog"><button class="ghost">Cancel</button></form>
            <button type="button" id="confirm-view">${icon('eye')}View for ${money(fee)}</button>
          </div>
        </div>`;
      $('#confirm-view').addEventListener('click', async (e) => {
        e.currentTarget.disabled = true;
        try { await show(cin); } catch (err) { toast(err.message, true); dlg.close(); }
      });
    } else {
      show(cin).catch((err) => { toast(err.message, true); dlg.close(); });
    }
    dlg.showModal();
  });
  dlg.addEventListener('click', (e) => { if (e.target === dlg) dlg.close(); }); // click backdrop to close

  // ---------- lawyer billing ----------
  async function loadBilling() {
    const [bal, views, f] = await Promise.all([api.myBalance(), api.myViews(), api.getFee()]);
    $('#bal').textContent = money(bal.balanceDue);
    $('#count').textContent = bal.viewCount;
    $('#fee-now').textContent = money(f.feePerView);
    table($('#views'), [
      ['Viewed', (r) => new Date(r.viewedAt).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })],
      ['CIN', (r) => `<span class="mono">${esc(r.cin)}</span>`],
      ['Fee', (r) => money(r.fee), 'num']
    ], views, 'You have not viewed any cases yet.');
  }

  JIS.pages((id) => {
    if (id === 'billing' && lawyer) loadBilling().catch((err) => toast(err.message, true));
  });
})();

// Small shared helpers. No framework.
(function () {
  const JIS = window.JIS;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const date = (v) => v ? new Date(v.length === 10 ? v + 'T00:00' : v).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';
  const money = (n) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: window.JIS_CONFIG.CURRENCY || 'INR' }).format(n || 0);
  const LABEL = { PENDING: 'Pending', CLOSED: 'Closed', SCHEDULED: 'Scheduled', ADJOURNED: 'Adjourned', HELD: 'Held' };
  const tag = (s) => `<span class="tag ${esc(s)}">${esc(LABEL[s] || s)}</span>`;
  const todayISO = () => new Date().toLocaleDateString('en-CA'); // YYYY-MM-DD, local time

  // ---------- icons (Lucide, ISC licence) ----------
  const ICONS = {
    scale: '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
    dashboard: '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
    filePlus: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M9 15h6"/><path d="M12 18v-6"/>',
    fileText: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    fileCheck: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="m9 15 2 2 4-4"/>',
    gavel: '<path d="m14.5 12.5-8 8a2.119 2.119 0 1 1-3-3l8-8"/><path d="m16 16 6-6"/><path d="m8 8 6-6"/><path d="m9 7 8 8"/><path d="m21 11-8-8"/>',
    chart: '<path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    calendar: '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
    search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    receipt: '<path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/><path d="M12 17.5v-11"/>',
    logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/>',
    moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
    menu: '<line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/>',
    check: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/>',
    alert: '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
    clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    folder: '<path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"/>',
    rupee: '<path d="M6 3h12"/><path d="M6 8h12"/><path d="m6 13 8.5 8"/><path d="M6 13h3"/><path d="M9 13c6.667 0 6.667-10 0-10"/>',
    pin: '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    arrow: '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    lock: '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    eye: '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
    shield: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>'
  };
  const icon = (name, cls = '') => `<svg class="icon ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ''}</svg>`;
  // <span data-icon="gavel"></span> -> inline SVG
  const hydrate = (root = document) => $$('[data-icon]', root).forEach((n) => {
    if (!n.querySelector(':scope > svg.icon')) n.insertAdjacentHTML('afterbegin', icon(n.dataset.icon));
  });

  // ---------- theme ----------
  function setTheme(t) {
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem('jis.theme', t); } catch (_) { /* private mode */ }
    $$('[data-theme-toggle]').forEach((b) => {
      b.innerHTML = icon(t === 'dark' ? 'sun' : 'moon') + `<span>${t === 'dark' ? 'Light' : 'Dark'}</span>`;
      b.setAttribute('aria-label', `Switch to ${t === 'dark' ? 'light' : 'dark'} theme`);
    });
  }

  function toast(msg, err) {
    $('.toast')?.remove();
    const t = document.createElement('div');
    t.className = 'toast' + (err ? ' err' : '');
    t.setAttribute('role', err ? 'alert' : 'status');
    t.innerHTML = icon(err ? 'alert' : 'check') + `<span>${esc(msg)}</span>`;
    document.body.append(t);
    setTimeout(() => t.remove(), err ? 5000 : 3200);
  }

  // Form values as a plain object (trimmed strings).
  const values = (form) => Object.fromEntries([...new FormData(form)].map(([k, v]) => [k, typeof v === 'string' ? v.trim() : v]));

  // Wire a form: disables its button while working, shows errors inline.
  function onSubmit(form, fn) {
    form.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const btn = $('button[type=submit], button:not([type])', form);
      const out = $('.error', form);
      if (out) out.textContent = '';
      if (btn) { btn.disabled = true; btn.classList.add('busy'); }
      try { await fn(values(form), form); }
      catch (err) { out ? (out.textContent = err.message) : toast(err.message, true); }
      finally { if (btn) { btn.disabled = false; btn.classList.remove('busy'); } }
    });
  }

  // cols: [label, row => html, className?]
  function table(el, cols, rows, emptyText = 'Nothing to show.') {
    if (!rows || !rows.length) { el.innerHTML = `<p class="empty">${esc(emptyText)}</p>`; return; }
    el.innerHTML = `<div class="table-wrap"><table>
      <thead><tr>${cols.map((c) => `<th class="${c[2] === 'num' ? 'num' : ''}">${esc(c[0])}</th>`).join('')}</tr></thead>
      <tbody>${rows.map((r, i) => `<tr style="--i:${Math.min(i, 20)}">${cols.map((c) => `<td class="${c[2] || ''}">${c[1](r)}</td>`).join('')}</tr>`).join('')}</tbody>
    </table></div>`;
  }

  // ---------- session + shell ----------
  const user = () => JSON.parse(sessionStorage.getItem('jis.user') || 'null');
  const initials = (name) => String(name || '?').replace(/^(Justice|Adv\.?|Mr\.?|Ms\.?|Dr\.?)\s+/i, '').split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase();

  function guard(roles) {
    const u = user();
    if (!u || !roles.includes(u.role)) { location.replace('index.html'); return null; }
    $$('[data-user-name]').forEach((n) => (n.textContent = u.name));
    $$('[data-user-role]').forEach((n) => (n.textContent = u.role.toLowerCase()));
    $$('[data-user-initials]').forEach((n) => (n.textContent = initials(u.name)));
    $$('[data-today]').forEach((n) => (n.innerHTML = icon('calendar') + new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })));
    $('[data-logout]')?.addEventListener('click', async () => {
      try { await JIS.api.logout(); } catch (_) { /* ignore */ }
      const mock = sessionStorage.getItem('jis.mock'), db = sessionStorage.getItem('jis.mockdb');
      sessionStorage.clear();
      if (mock) sessionStorage.setItem('jis.mock', mock);
      if (db) sessionStorage.setItem('jis.mockdb', db);
      location.href = 'index.html';
    });
    $('[data-menu]')?.addEventListener('click', () => document.body.classList.toggle('nav-open'));
    document.addEventListener('click', (e) => {
      if (document.body.classList.contains('nav-open') && !e.target.closest('.side, [data-menu]')) document.body.classList.remove('nav-open');
    });
    return u;
  }

  // Hash-based sections: <section class="page" id="x"> + <nav><a href="#x">
  function pages(onShow) {
    const all = $$('main > section.page');
    // "#hearings:2026-000002" shows #hearings and passes the CIN along
    function show() {
      const [id, arg] = decodeURIComponent(location.hash.slice(1)).split(':');
      const target = all.find((s) => s.id === id) || all[0];
      const changed = target.hidden;
      all.forEach((s) => (s.hidden = s !== target));
      $$('.side nav a').forEach((a) => {
        if (a.getAttribute('href') === '#' + target.id) {
          a.setAttribute('aria-current', 'page');
          $$('[data-crumb]').forEach((n) => (n.textContent = a.textContent.trim()));
          document.title = `${a.textContent.trim()} · JIS`;
        } else a.removeAttribute('aria-current');
      });
      document.body.classList.remove('nav-open');
      if (changed) window.scrollTo({ top: 0 });
      onShow && onShow(target.id, arg);
    }
    window.addEventListener('hashchange', show);
    show();
  }

  const cinLink = (cin) => `<a class="cin-link" href="#hearings:${esc(cin)}">${esc(cin)}</a>`;

  // Read-only case record (used by registrar and browse views)
  function caseRecord(c) {
    const f = (label, v) => `<div><dt>${label}</dt><dd>${v}</dd></div>`;
    const hs = c.hearings || [];
    return `
      ${c.status === 'CLOSED' ? `<div class="notice ok">${icon('gavel')}<div><b>Judgment delivered ${date(c.judgmentDate)}.</b><br>${esc(c.judgmentSummary)}</div></div>` : ''}
      <div class="section-title">Defendant &amp; offence</div>
      <dl class="record">
        ${f('Defendant', esc(c.defendantName))}
        ${f('Address', esc(c.defendantAddress))}
        ${f('Crime', esc(c.crimeType))}
        ${f('Committed', `${date(c.crimeDate)} · ${esc(c.crimeLocation)}`)}
        ${f('Arrested by', esc(c.arrestingOfficer))}
        ${f('Date of arrest', date(c.arrestDate))}
      </dl>
      <div class="section-title">Trial</div>
      <dl class="record">
        ${f('Presiding judge', esc(c.presidingJudge))}
        ${f('Public prosecutor', esc(c.publicProsecutor))}
        ${f('Defence lawyer', esc(c.defenseLawyer))}
        ${f('Trial started', date(c.startDate))}
        ${f('Expected completion', date(c.expectedCompletionDate))}
        ${f('Status', tag(c.status))}
      </dl>
      <div class="section-title">Hearings (${hs.length})</div>
      ${hs.length ? `<ol class="timeline">${hs.map((h) => `
        <li class="${esc(h.status)}">
          <div class="when">${date(h.date)} <span class="mono small muted">${esc(h.slot)}</span> ${tag(h.status)}</div>
          ${h.adjournmentReason ? `<div class="what"><b>Adjourned:</b> ${esc(h.adjournmentReason)}</div>` : ''}
          ${h.proceedingSummary ? `<div class="what">${esc(h.proceedingSummary)}</div>` : ''}
        </li>`).join('')}</ol>` : '<p class="empty">No hearings yet.</p>'}`;
  }

  // Case title block: name, CIN, status and key facts
  const caseHead = (c) => `
    <div class="case-head">
      <div>
        <h2>${esc(c.defendantName)}</h2>
        <div class="case-meta">
          <span class="mono">${esc(c.cin)}</span>
          <span>${icon('gavel')}${esc(c.crimeType)}</span>
          <span>${icon('pin')}${esc(c.crimeLocation)}</span>
          <span>${icon('user')}${esc(c.presidingJudge)}</span>
        </div>
      </div>
      ${tag(c.status)}
    </div>`;

  // Theme: the <head> script already set data-theme; wire the toggle buttons.
  setTheme(document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light');
  document.addEventListener('click', (e) => {
    if (e.target.closest('[data-theme-toggle]')) setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
  });
  hydrate();

  Object.assign(JIS, { $, $$, esc, date, money, tag, toast, values, onSubmit, table, user, guard, pages, caseRecord, caseHead, cinLink, icon, hydrate, todayISO });
})();

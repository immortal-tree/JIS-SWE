(function () {
  const { $, $$, esc, date, money, tag, toast, onSubmit, table, api, icon, cinLink } = JIS;
  const me = JIS.guard(['REGISTRAR']);
  if (!me) return;

  const todayISO = JIS.todayISO();
  const monthStart = todayISO.slice(0, 8) + '01';

  // ---------- scheduler: pick a working day, pick a vacant slot, book ----------
  function scheduler(host, cin, onBooked) {
    host.replaceChildren($('#sched-tpl').content.cloneNode(true));
    const form = $('form', host);
    const dateIn = form.elements.date;
    const slotsEl = $('.slots', form);
    const hint = $('[data-hint]', form);
    const submit = $('button[type=submit]', form);
    dateIn.min = todayISO;
    const say = (name, text) => (hint.innerHTML = icon(name) + esc(text));

    dateIn.addEventListener('change', async () => {
      slotsEl.innerHTML = '';
      submit.disabled = true;
      $('.error', form).textContent = '';
      if (!dateIn.value) return;
      say('clock', 'Checking the calendar…');
      try {
        const res = await api.vacantSlots(dateIn.value);
        if (!res.workingDay) { say('alert', 'Not a working day (weekend or holiday). Choose another date.'); return; }
        if (!res.slots.length) { say('alert', 'No vacant slots on this day. Choose another date.'); return; }
        say('check', `${res.slots.length} vacant slot${res.slots.length > 1 ? 's' : ''} on ${date(dateIn.value)}. Pick one:`);
        slotsEl.innerHTML = res.slots.map((s) =>
          `<label><input type="radio" name="slot" value="${esc(s)}" required>${icon('clock')}${esc(s)}</label>`).join('');
      } catch (err) { hint.textContent = ''; $('.error', form).textContent = err.message; }
    });
    slotsEl.addEventListener('change', () => (submit.disabled = false));

    onSubmit(form, async (v) => {
      const h = await api.scheduleHearing(cin, v.date, v.slot);
      toast(`Hearing set for ${date(h.date)}, ${h.slot}`);
      onBooked && onBooked(h);
    });
  }

  // ---------- dashboard ----------
  const hour = new Date().getHours();
  $('#greeting').textContent = `Good ${hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : 'evening'}, ${me.name}`;

  async function loadDashboard() {
    const [pending, docket, resolved, fee] = await Promise.all([
      api.pendingCases(), api.hearingsOn(todayISO), api.resolvedCases(monthStart, todayISO), api.getFee()
    ]);
    $('#t-pending').textContent = pending.length;
    $('#t-today').textContent = docket.length;
    $('#t-resolved').textContent = resolved.length;
    $('#t-fee').textContent = money(fee.feePerView);
    $$('.tile.skeleton').forEach((t) => t.classList.remove('skeleton'));

    $('#dash-today-note').textContent = docket.length ? `${docket.length} hearing${docket.length > 1 ? 's' : ''}` : '';
    table($('#dash-today'), [
      ['Slot', (r) => `<span class="mono">${esc(r.slot)}</span>`],
      ['Case', (r) => `${cinLink(r.cin)}<div class="small muted">${esc(r.defendantName)} · ${esc(r.crimeType)}</div>`],
      ['Judge', (r) => esc(r.presidingJudge)],
      ['', (r) => `<a class="btn ghost sm" href="#hearings:${esc(r.cin)}">Record outcome</a>`, 'num']
    ], docket, 'No hearings are scheduled for today.');

    const recent = [...pending].sort((a, b) => b.cin.localeCompare(a.cin)).slice(0, 6);
    table($('#dash-pending'), [
      ['CIN', (r) => cinLink(r.cin)],
      ['Defendant', (r) => esc(r.defendantName)],
      ['Crime', (r) => esc(r.crimeType)],
      ['Judge', (r) => esc(r.presidingJudge)],
      ['Started', (r) => date(r.startDate)]
    ], recent, 'No pending cases. Register one to get started.');
  }

  // Tiles and links with data-run jump to Reports and run that query.
  document.addEventListener('click', (ev) => {
    const a = ev.target.closest('[data-run]');
    if (!a) return;
    const form = $('#' + a.dataset.run);
    if (form.id === 'q-date') form.elements.date.value = todayISO;
    if (form.id === 'q-resolved') { form.elements.from.value = monthStart; form.elements.to.value = todayISO; }
    setTimeout(() => form.requestSubmit(), 0);
  });

  // ---------- register case ----------
  const caseForm = $('#case-form');
  onSubmit(caseForm, async (v) => {
    if (v.arrestDate < v.crimeDate) throw new Error('Arrest date cannot be before the date of the crime.');
    if (v.expectedCompletionDate < v.startDate) throw new Error('Expected completion cannot be before the start date.');
    const { cin } = await api.registerCase(v);
    caseForm.hidden = true;
    $('#new-cin').textContent = cin;
    $('#open-new').href = '#hearings:' + cin;
    $('#registered').hidden = false;
    loaded.dashboard = false;
    scheduler($('#first-sched'), cin, (h) => {
      $('#first-sched').innerHTML = `<div class="notice ok">${icon('check')}<div>First hearing booked for <b>${date(h.date)}</b> at <span class="mono">${esc(h.slot)}</span>.</div></div>`;
    });
  });
  $('#another').addEventListener('click', () => {
    caseForm.reset();
    caseForm.hidden = false;
    $('#registered').hidden = true;
    $('input', caseForm).focus();
  });

  // ---------- hearings ----------
  const area = $('#hearing-area');
  const openForm = $('#open-case');

  async function openCase(cin) {
    const c = await api.getCase(cin);
    const next = (c.hearings || []).find((h) => h.status === 'SCHEDULED');
    area.innerHTML = `
      <div class="panel">
        ${JIS.caseHead(c)}
        <details style="margin-top:1rem"><summary class="small" style="cursor:pointer;color:var(--primary);font-weight:600">Full record and hearing history</summary>${JIS.caseRecord(c)}</details>
      </div>
      <div id="step"></div>`;
    const step = $('#step', area);

    if (c.status === 'CLOSED') {
      step.innerHTML = `<div class="notice ok">${icon('shield')}<div>This case is closed. Judgment was delivered on <b>${date(c.judgmentDate)}</b>; the record is kept for reference.</div></div>`;
    } else if (next) {
      step.innerHTML = outcomeForm(next);
      wireOutcome($('form', step), c, next);
    } else {
      step.innerHTML = `<div class="panel"><div class="card-head"><h3>${icon('calendar')}Assign the next hearing</h3></div><div id="next-sched"></div></div>`;
      scheduler($('#next-sched', step), c.cin, () => openCase(c.cin));
    }
  }

  function outcomeForm(h) {
    const future = h.date > todayISO;
    return `
      <form class="panel">
        <div class="card-head">
          <h3>${icon('gavel')}Outcome of the hearing on ${date(h.date)} <span class="mono small muted">${esc(h.slot)}</span></h3>
          ${tag(h.status)}
        </div>
        ${future ? `<div class="notice warn">${icon('clock')}<div>This hearing hasn't happened yet. Its outcome can be recorded on or after ${date(h.date)}.</div></div>` : ''}
        <div class="choice" role="radiogroup" aria-label="Outcome">
          <label><input type="radio" name="outcome" value="adjourned" required>Adjourned<small>Record the reason, then set a new date</small></label>
          <label><input type="radio" name="outcome" value="held">Held, no judgment<small>Record the proceedings, then set a new date</small></label>
          <label><input type="radio" name="outcome" value="judgment">Judgment delivered<small>Record proceedings and judgment; closes the case</small></label>
        </div>
        <div class="reveal adjourned">
          <label>Reason for adjournment <textarea name="reason" placeholder="e.g. Prosecution witness unavailable"></textarea></label>
        </div>
        <div class="reveal held">
          <label>Summary of proceedings <textarea name="summary" placeholder="What happened at this hearing"></textarea></label>
        </div>
        <div class="reveal judgment">
          <div class="fields">
            <label>Judgment date <input type="date" name="judgmentDate" value="${esc(h.date)}" min="${esc(h.date)}" max="${todayISO}"></label>
            <label class="wide">Judgment summary <textarea name="judgmentSummary" placeholder="Verdict and sentence"></textarea></label>
          </div>
        </div>
        <p class="error" aria-live="polite"></p>
        <div class="actions"><button type="submit" data-icon="check">Record outcome</button></div>
      </form>`;
  }

  function wireOutcome(form, c, h) {
    JIS.hydrate(form);
    onSubmit(form, async (v) => {
      const need = (k, msg) => { if (!v[k]) { form.elements[k].focus(); throw new Error(msg); } };
      if (v.outcome === 'adjourned') {
        need('reason', 'Enter the reason for adjournment.');
        await api.adjourn(h.hearingID, v.reason);
        toast('Adjournment recorded. Assign the next hearing.');
      } else if (v.outcome === 'held') {
        need('summary', 'Enter a summary of the proceedings.');
        await api.proceedings(h.hearingID, v.summary);
        toast('Proceedings recorded. Assign the next hearing.');
      } else {
        need('summary', 'Enter a summary of the proceedings.');
        need('judgmentDate', 'Enter the judgment date.');
        need('judgmentSummary', 'Enter the judgment summary.');
        await api.recordJudgment(h.hearingID, v.summary, v.judgmentSummary, v.judgmentDate);
        toast('Judgment recorded. Case closed.');
      }
      loaded.dashboard = false;
      await openCase(c.cin);
    });
  }

  onSubmit(openForm, async ({ cin }) => {
    history.replaceState(null, '', '#hearings:' + cin);
    await openCase(cin);
  });

  // ---------- queries ----------
  const out = $('#q-result');
  const heading = (ic, t, n) => `<h2>${icon(ic)}${esc(t)}${n !== undefined ? ` <span class="muted small">(${n})</span>` : ''}</h2><div></div>`;

  onSubmit($('#q-pending'), async () => {
    const rows = await api.pendingCases();
    out.innerHTML = heading('folder', 'Pending cases', rows.length);
    table(out.lastElementChild, [
      ['CIN', (r) => cinLink(r.cin)],
      ['Started', (r) => date(r.startDate)],
      ['Defendant', (r) => `${esc(r.defendantName)}<div class="small muted">${esc(r.defendantAddress)}</div>`, 'clip'],
      ['Crime', (r) => `${esc(r.crimeType)}<div class="small muted">${date(r.crimeDate)}, ${esc(r.crimeLocation)}</div>`],
      ['Lawyer', (r) => esc(r.defenseLawyer)],
      ['Prosecutor', (r) => esc(r.publicProsecutor)],
      ['Judge', (r) => esc(r.presidingJudge)]
    ], rows, 'No pending cases.');
  });

  onSubmit($('#q-resolved'), async ({ from, to }) => {
    if (to < from) throw new Error('"To" must be on or after "From".');
    const rows = await api.resolvedCases(from, to);
    out.innerHTML = heading('fileCheck', `Resolved ${date(from)} – ${date(to)}`, rows.length);
    table(out.lastElementChild, [
      ['Started', (r) => date(r.startDate)],
      ['CIN', (r) => cinLink(r.cin)],
      ['Judgment', (r) => date(r.judgmentDate)],
      ['Judge', (r) => esc(r.presidingJudge)],
      ['Summary', (r) => esc(r.judgmentSummary), 'clip']
    ], rows, 'No cases resolved in this period.');
  });

  onSubmit($('#q-date'), async ({ date: d }) => {
    const rows = await api.hearingsOn(d);
    out.innerHTML = heading('clock', `Hearings on ${date(d)}`, rows.length);
    table(out.lastElementChild, [
      ['Slot', (r) => `<span class="mono">${esc(r.slot)}</span>`],
      ['CIN', (r) => cinLink(r.cin)],
      ['Defendant', (r) => esc(r.defendantName)],
      ['Crime', (r) => esc(r.crimeType)],
      ['Judge', (r) => esc(r.presidingJudge)],
      ['', (r) => `<a class="btn ghost sm" href="#hearings:${esc(r.cin)}">Record outcome</a>`, 'num']
    ], rows, 'No hearings scheduled on this date.');
  });

  onSubmit($('#q-status'), async ({ cin }) => {
    const s = await api.caseStatus(cin);
    const lh = s.lastHearing, nh = s.nextHearing;
    const last = lh
      ? `${date(lh.date)} ${tag(lh.status)}${lh.adjournmentReason ? `<div class="small muted">${esc(lh.adjournmentReason)}</div>` : ''}${lh.proceedingSummary ? `<div class="small muted">${esc(lh.proceedingSummary)}</div>` : ''}`
      : '—';
    out.innerHTML = `
      <h2>${icon('search')}Status of <span class="mono">${esc(s.cin)}</span></h2>
      <dl class="record">
        <div><dt>Status</dt><dd>${tag(s.status)}</dd></div>
        <div><dt>Last hearing</dt><dd>${last}</dd></div>
        <div><dt>Next hearing</dt><dd>${nh ? `${date(nh.date)} <span class="mono small">${esc(nh.slot)}</span>` : (s.status === 'CLOSED' ? '—' : '<span class="tag off">Not assigned</span>')}</dd></div>
        ${s.judgmentDate ? `<div><dt>Judgment</dt><dd>${date(s.judgmentDate)}</dd></div>` : ''}
      </dl>
      <div class="actions"><a class="btn ghost" href="#hearings:${esc(s.cin)}">${icon('arrow')}Open in Hearings</a></div>`;
  });

  // ---------- accounts ----------
  async function loadUsers() {
    const rows = await api.users();
    const active = rows.filter((r) => r.active).length;
    $('#user-count').textContent = `${active} active · ${rows.length - active} deleted`;
    table($('#users'), [
      ['Name', (r) => `<b>${esc(r.name)}</b><div class="small muted mono">${esc(r.username)}</div>`],
      ['Role', (r) => `<span class="tag ${esc(r.role)}">${esc(r.role.toLowerCase())}</span>`],
      ['Balance due', (r) => r.role === 'LAWYER' ? `${money(r.balanceDue)}<div class="small muted">${r.viewsCount ?? 0} views</div>` : '<span class="muted">—</span>', 'num'],
      ['Status', (r) => r.active ? '<span class="tag on">Active</span>' : '<span class="tag off">Deleted</span>'],
      ['', (r) => r.active && r.userID !== JIS.user().userID
        ? `<button class="danger" data-delete="${esc(r.userID)}" data-name="${esc(r.name)}">Delete</button>` : '', 'num']
    ], rows, 'No users.');
  }
  $('#users').addEventListener('click', async (ev) => {
    const b = ev.target.closest('[data-delete]');
    if (!b || !confirm(`Delete the account of ${b.dataset.name}? They will no longer be able to sign in.`)) return;
    b.disabled = true;
    try { await api.deleteUser(b.dataset.delete); toast('Account deleted'); await loadUsers(); }
    catch (err) { toast(err.message, true); b.disabled = false; }
  });
  onSubmit($('#user-form'), async (v, form) => {
    await api.createUser(v);
    form.reset();
    toast(`Account created for ${v.name}`);
    await loadUsers();
  });

  // ---------- calendar & fee ----------
  const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  function renderCalendar(cal) {
    $('#weekday-checks').innerHTML = DAYS.map((d) =>
      `<label><input type="checkbox" name="days" value="${d}" ${cal.workingWeekdays.includes(d) ? 'checked' : ''}> ${d}</label>`).join('');
    $('#slots-form').elements.slots.value = cal.dailySlots.join('\n');
    const upcoming = cal.holidays.filter((d) => d >= todayISO);
    $('#holidays').innerHTML = upcoming.length
      ? `<div class="section-title" style="margin-top:.5rem">Upcoming holidays</div><div class="checks">${upcoming.map((d) => `<span class="tag off">${date(d)}</span>`).join('')}</div>`
      : '<p class="empty">No upcoming holidays.</p>';
  }
  async function loadCalendar() {
    const [cal, fee] = await Promise.all([api.calendar(), api.getFee()]);
    renderCalendar(cal);
    $('#fee-now').textContent = `Current fee: ${money(fee.feePerView)} per case viewed`;
    $('#fee-form').elements.amount.value = fee.feePerView;
  }
  onSubmit($('#weekdays-form'), async (_, form) => {
    const days = [...form.querySelectorAll('input:checked')].map((i) => i.value);
    if (!days.length) throw new Error('Choose at least one working weekday.');
    renderCalendar(await api.setWeekdays(days));
    toast('Working weekdays saved');
  });
  onSubmit($('#slots-form'), async ({ slots }) => {
    const list = slots.split('\n').map((s) => s.trim()).filter(Boolean);
    const bad = list.find((s) => !/^([01]\d|2[0-3]):[0-5]\d$/.test(s));
    if (bad) throw new Error(`"${bad}" is not a start time in HH:MM form.`);
    renderCalendar(await api.setSlots(list));
    toast('Daily slots saved');
  });
  onSubmit($('#holiday-form'), async ({ date: d }, form) => {
    $('#holiday-clash').innerHTML = '';
    try {
      renderCalendar(await api.addHoliday(d));
      form.reset();
      toast(`${date(d)} marked as a holiday`);
    } catch (err) {
      const hs = err.data && err.data.hearings;
      if (!hs) throw err;
      $('#holiday-clash').innerHTML = `<div class="notice warn">${icon('alert')}<div>${esc(err.message)}<ul>${hs.map((h) =>
        `<li><span class="mono">${esc(h.slot)}</span> · ${cinLink(h.cin)}</li>`).join('')}</ul></div></div>`;
    }
  });
  onSubmit($('#fee-form'), async ({ amount }) => {
    const fee = await api.setFee(Number(amount));
    $('#fee-now').textContent = `Current fee: ${money(fee.feePerView)} per case viewed`;
    $('#t-fee').textContent = money(fee.feePerView);
    toast('Viewing fee updated');
  });

  // ---------- routing ----------
  const loaded = {};
  JIS.pages(async (id, arg) => {
    try {
      if (id === 'dashboard' && !loaded.dashboard) { loaded.dashboard = true; await loadDashboard(); }
      if (id === 'accounts' && !loaded.accounts) { loaded.accounts = true; await loadUsers(); }
      if (id === 'calendar' && !loaded.calendar) { loaded.calendar = true; await loadCalendar(); }
      if (id === 'hearings' && arg) { openForm.elements.cin.value = arg; await openCase(arg); }
    } catch (err) {
      if (id === 'dashboard') loaded.dashboard = false;
      toast(err.message, true);
    }
  });
})();

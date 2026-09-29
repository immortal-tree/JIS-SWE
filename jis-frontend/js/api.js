// Every backend route the UI calls lives in this one file.
// The pages use camelCase fields; the backend (jis-backend, FastAPI) uses
// snake_case and its own paths. This file translates both ways, so the
// pages never build URLs or see backend field names. API.md has the mapping.
(function () {
  const JIS = (window.JIS = window.JIS || {});
  const base = () => window.JIS_CONFIG.API_BASE.replace(/\/$/, '');
  const e = encodeURIComponent;
  const qs = (o) => '?' + new URLSearchParams(o).toString();

  // ---------- field names ----------
  // snake_case -> camelCase, plus the names the pages use for ids and dates.
  const RENAME = { hearingId: 'hearingID', userId: 'userID', recordId: 'recordID', hearingDate: 'date' };
  const camelKey = (k) => { const c = k.replace(/_([a-z])/g, (_, x) => x.toUpperCase()); return RENAME[c] || c; };
  const snakeKey = (k) => k.replace(/[A-Z]/g, (x) => '_' + x.toLowerCase());
  // Money arrives as decimal strings ("100.00"), slots as "10:00:00".
  const NUMBERS = new Set(['balanceDue', 'fee', 'feePerView', 'feeCharged']);
  const hhmm = (t) => (typeof t === 'string' ? t.slice(0, 5) : t);

  function camel(v) {
    if (Array.isArray(v)) return v.map(camel);
    if (!v || typeof v !== 'object') return v;
    return Object.fromEntries(Object.entries(v).map(([k, x]) => {
      const key = camelKey(k);
      if (NUMBERS.has(key) && x != null) return [key, Number(x)];
      if (key === 'slot') return [key, hhmm(x)];
      return [key, camel(x)];
    }));
  }
  const snake = (o) => Object.fromEntries(Object.entries(o).map(([k, v]) => [snakeKey(k), v === '' ? null : v]));

  // FastAPI validation errors are a list; turn them into one readable line.
  function message(data, fallback) {
    if (!data) return fallback;
    const d = data.detail;
    if (Array.isArray(d)) return d.map((x) => `${x.loc ? x.loc.filter((p) => p !== 'body').join('.') + ': ' : ''}${x.msg}`).join('; ');
    return d || data.error || data.message || fallback;
  }

  async function req(method, path, body) {
    const token = sessionStorage.getItem('jis.token');
    let res;
    try {
      res = await fetch(base() + path, {
        method,
        headers: {
          ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
          ...(token ? { Authorization: 'Bearer ' + token } : {})
        },
        body: body === undefined ? undefined : JSON.stringify(body)
      });
    } catch (_) {
      throw new Error(`Cannot reach the JIS server at ${base()}. Is it running?`);
    }
    if (res.status === 401 && path !== '/auth/login') {
      sessionStorage.clear();
      location.href = 'index.html';
      throw new Error('Session expired');
    }
    const data = res.status === 204 ? null : await res.json().catch(() => null);
    if (!res.ok) {
      const err = new Error(message(data, res.statusText));
      err.status = res.status;
      err.data = data && data.conflicts ? { hearings: camel(data.conflicts) } : data;
      throw err;
    }
    return camel(data);
  }

  // ---------- calendar shapes ----------
  const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];   // ISO weekday 1..7
  const calendarOut = (c) => ({
    workingWeekdays: c.workingWeekdays.map((n) => DAYS[n - 1]),
    dailySlots: c.dailySlots.map(hhmm),
    holidays: c.holidays.map((h) => h.holidayDate)
  });

  JIS.api = {
    // auth + current user
    async login(username, password) {
      const r = await req('POST', '/auth/login', { username, password });
      return { token: r.accessToken, user: { userID: r.userID, name: r.name, role: r.role } };
    },
    // Tokens are stateless; signing out just forgets the token (ui.js clears the session).
    logout:       async () => null,
    async myBalance() {
      const [me, views] = await Promise.all([req('GET', '/users/me'), req('GET', '/users/me/views')]);
      return { balanceDue: me.balanceDue, viewCount: views.length };
    },
    myViews:      ()                   => req('GET',  '/users/me/views'),

    // cases
    registerCase: (details)            => req('POST', '/cases', snake(details)),
    pendingCases: ()                   => req('GET',  '/reports/pending'),
    resolvedCases:(from, to)           => req('GET',  '/reports/resolved' + qs({ from, to })),
    async getCase(cin) {
      const r = await req('GET', '/cases/' + e(cin));
      return { ...r.case, hearings: r.hearings, chargedFee: r.feeCharged ?? null, balanceDue: r.balanceDue ?? null };
    },
    caseStatus:   (cin)                => req('GET',  '/cases/' + e(cin) + '/status'),
    search:       (q)                  => req('GET',  '/search' + qs({ q })),

    // hearings: every outcome is recorded against the hearing
    scheduleHearing: (cin, date, slot) => req('POST', '/cases/' + e(cin) + '/hearings', { hearing_date: date, slot }),
    hearingsOn:   (date)               => req('GET',  '/reports/hearings' + qs({ on: date })),
    adjourn:      (id, reason)         => req('POST', '/hearings/' + e(id) + '/adjourn', { reason }),
    proceedings:  (id, summary)        => req('POST', '/hearings/' + e(id) + '/proceedings', { summary }),
    // Held with judgment: proceedings + judgment + close, in one transaction.
    recordJudgment: (id, summary, judgmentSummary, judgmentDate) =>
                                          req('POST', '/hearings/' + e(id) + '/judgment',
                                              { proceedings_summary: summary, judgment_summary: judgmentSummary,
                                                judgment_date: judgmentDate || null }),

    // court calendar
    async vacantSlots(date) {
      const r = await req('GET', '/slots' + qs({ on: date }));
      return { date: r.date, workingDay: r.workingDay, slots: r.vacantSlots.map(hhmm) };
    },
    calendar:     async ()             => calendarOut(await req('GET', '/calendar')),
    setWeekdays:  async (days)         => calendarOut(await req('PUT', '/calendar/weekdays', { weekdays: days.map((d) => DAYS.indexOf(d) + 1) })),
    setSlots:     async (slots)        => calendarOut(await req('PUT', '/calendar/slots', { slots })),
    async addHoliday(date) {
      await req('POST', '/calendar/holidays', { holiday_date: date });
      return calendarOut(await req('GET', '/calendar'));
    },

    // viewing fee
    getFee:       ()                   => req('GET',  '/fee'),
    setFee:       (amount)             => req('PUT',  '/fee', { fee_per_view: amount }),

    // accounts
    users:        ()                   => req('GET',  '/users'),
    createUser:   (u)                  => req('POST', '/users', u),
    deleteUser:   (id)                 => req('DELETE', '/users/' + e(id))
  };
})();

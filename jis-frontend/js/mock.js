// In-browser stand-in for the backend. Same method names as api.js.
// Only active in mock mode; data lives in sessionStorage for this tab.
(function () {
  const params = new URLSearchParams(location.search);
  if (params.has('mock')) sessionStorage.setItem('jis.mock', params.get('mock') === '0' ? '0' : '1');
  const flag = sessionStorage.getItem('jis.mock');
  const on = flag ? flag === '1' : window.JIS_CONFIG.MOCK;
  window.JIS.mock = on;
  if (!on) return;

  const KEY = 'jis.mockdb';
  const today = new Date();
  const iso = (d) => d.toISOString().slice(0, 10);
  const addDays = (n) => { const d = new Date(today); d.setDate(d.getDate() + n); return iso(d); };

  function seed() {
    const y = today.getFullYear();
    const h = (id, cin, date, slot, status, extra = {}) =>
      ({ hearingID: 'H' + id, cin, date, slot, status, adjournmentReason: null, proceedingSummary: null, ...extra });
    return {
      seq: { [y]: 4 },
      fee: { feePerView: 50, updatedAt: new Date().toISOString() },
      calendar: {
        workingWeekdays: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
        dailySlots: ['10:00', '11:30', '14:00', '15:30'],
        holidays: []
      },
      users: [
        { userID: 'U1', name: 'A. Mehta',   username: 'registrar', password: 'registrar', role: 'REGISTRAR', active: true },
        { userID: 'U2', name: 'Justice R. Iyer', username: 'judge', password: 'judge', role: 'JUDGE', active: true },
        { userID: 'U3', name: 'S. Banerjee', username: 'lawyer', password: 'lawyer', role: 'LAWYER', active: true, balanceDue: 0 }
      ],
      views: [],
      cases: [
        { cin: `${y}-000001`, defendantName: 'Ravi Kumar', defendantAddress: '14 Station Road, Dhanbad', crimeType: 'Theft',
          crimeDate: `${y}-01-12`, crimeLocation: 'Bank More market', arrestingOfficer: 'SI P. Singh', arrestDate: `${y}-01-14`,
          presidingJudge: 'Justice R. Iyer', publicProsecutor: 'M. Das', defenseLawyer: 'S. Banerjee',
          startDate: `${y}-02-01`, expectedCompletionDate: `${y}-06-30`, status: 'CLOSED',
          judgmentDate: `${y}-05-20`, judgmentSummary: 'Convicted of theft of a two-wheeler. Six months simple imprisonment, fine of Rs 5,000. Prior record considered.' },
        { cin: `${y}-000002`, defendantName: 'Nitin Sharma', defendantAddress: '3 Hirapur Lane, Dhanbad', crimeType: 'Arson',
          crimeDate: `${y}-03-02`, crimeLocation: 'Godown, Jharia', arrestingOfficer: 'Insp. K. Oraon', arrestDate: `${y}-03-05`,
          presidingJudge: 'Justice R. Iyer', publicProsecutor: 'M. Das', defenseLawyer: 'A. Roy',
          startDate: `${y}-04-10`, expectedCompletionDate: `${y + 1}-01-31`, status: 'PENDING', judgmentDate: null, judgmentSummary: null },
        { cin: `${y}-000003`, defendantName: 'Farhan Ali', defendantAddress: '22 Saraidhela, Dhanbad', crimeType: 'Fraud',
          crimeDate: `${y}-04-18`, crimeLocation: 'Online, Dhanbad', arrestingOfficer: 'SI L. Tudu', arrestDate: `${y}-05-01`,
          presidingJudge: 'Justice P. Nair', publicProsecutor: 'V. Jha', defenseLawyer: 'S. Banerjee',
          startDate: `${y}-06-02`, expectedCompletionDate: `${y}-12-15`, status: 'PENDING', judgmentDate: null, judgmentSummary: null },
        { cin: `${y}-000004`, defendantName: 'Mohan Lal', defendantAddress: '7 Katras Road, Dhanbad', crimeType: 'Theft',
          crimeDate: `${y}-02-20`, crimeLocation: 'Railway colony', arrestingOfficer: 'SI P. Singh', arrestDate: `${y}-02-21`,
          presidingJudge: 'Justice P. Nair', publicProsecutor: 'V. Jha', defenseLawyer: 'K. Paul',
          startDate: `${y}-03-15`, expectedCompletionDate: `${y}-08-30`, status: 'CLOSED',
          judgmentDate: `${y}-08-11`, judgmentSummary: 'Acquitted. Recovery of stolen goods not proved; witness testimony inconsistent.' }
      ],
      hearings: [
        h(1, `${y}-000001`, `${y}-03-04`, '10:00', 'ADJOURNED', { adjournmentReason: 'Prosecution witness unavailable' }),
        h(2, `${y}-000001`, `${y}-04-08`, '11:30', 'HELD', { proceedingSummary: 'Witness examined; defence cross-examination.' }),
        h(3, `${y}-000001`, `${y}-05-20`, '10:00', 'HELD', { proceedingSummary: 'Final arguments heard; judgment pronounced.' }),
        h(4, `${y}-000002`, `${y}-05-06`, '14:00', 'HELD', { proceedingSummary: 'Charges framed.' }),
        h(5, `${y}-000002`, nextWorkday(1), '10:00', 'SCHEDULED'),
        h(6, `${y}-000003`, nextWorkday(1), '11:30', 'SCHEDULED'),
        h(7, `${y}-000004`, `${y}-08-11`, '15:30', 'HELD', { proceedingSummary: 'Arguments concluded; judgment delivered.' })
      ],
      nextHearing: 8,
      nextUser: 4,
      nextView: 1
    };
  }
  function nextWorkday(n) {
    const d = new Date(today);
    let k = 0;
    while (k < n) { d.setDate(d.getDate() + 1); if (d.getDay() % 6 !== 0) k++; }
    return iso(d);
  }

  const load = () => JSON.parse(sessionStorage.getItem(KEY) || 'null') || seed();
  let db = load();
  const save = () => sessionStorage.setItem(KEY, JSON.stringify(db));
  const me = () => JSON.parse(sessionStorage.getItem('jis.user') || 'null');
  const wait = (v) => new Promise((r) => setTimeout(() => r(structuredClone(v)), 160));
  const fail = (msg, status = 400, data) => { const e = new Error(msg); e.status = status; e.data = data; return Promise.reject(e); };
  const find = (cin) => db.cases.find((c) => c.cin === cin);
  const dayName = (date) => ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][new Date(date + 'T00:00').getDay()];
  const isWorking = (date) => db.calendar.workingWeekdays.includes(dayName(date)) && !db.calendar.holidays.includes(date);
  const withHearings = (c) => ({ ...c, hearings: db.hearings.filter((h) => h.cin === c.cin).sort((a, b) => a.date.localeCompare(b.date)) });
  const hearing = (id) => db.hearings.find((h) => h.hearingID === id);

  window.JIS.api = {
    login(username, password) {
      const u = db.users.find((x) => x.username === username && x.password === password);
      if (!u) return fail('Invalid username or password', 401);
      if (!u.active) return fail('This account has been deleted', 403);
      return wait({ token: 'mock-' + u.userID, user: { userID: u.userID, name: u.name, role: u.role } });
    },
    logout: () => wait(null),
    myBalance() {
      const u = db.users.find((x) => x.userID === me()?.userID);
      return wait({ balanceDue: u?.balanceDue || 0, viewCount: db.views.filter((v) => v.lawyerID === u?.userID).length });
    },
    myViews: () => wait(db.views.filter((v) => v.lawyerID === me()?.userID).reverse()),

    registerCase(d) {
      const y = new Date().getFullYear();
      db.seq[y] = (db.seq[y] || 0) + 1;
      const cin = `${y}-${String(db.seq[y]).padStart(6, '0')}`;
      db.cases.push({ ...d, cin, status: 'PENDING', judgmentDate: null, judgmentSummary: null });
      save();
      return wait({ cin });
    },
    pendingCases: () => wait(db.cases.filter((c) => c.status === 'PENDING').sort((a, b) => a.cin.localeCompare(b.cin))),
    resolvedCases: (from, to) => wait(db.cases
      .filter((c) => c.status === 'CLOSED' && c.judgmentDate >= from && c.judgmentDate <= to)
      .sort((a, b) => a.startDate.localeCompare(b.startDate))),
    getCase(cin) {
      const c = find(cin);
      if (!c) return fail('No case with CIN ' + cin, 404);
      const u = me();
      if (u?.role !== 'REGISTRAR' && c.status !== 'CLOSED') return fail(`Case ${cin} is still pending; only closed cases can be viewed`, 403);
      let chargedFee = null, balanceDue = null;
      if (u?.role === 'LAWYER') {
        chargedFee = db.fee.feePerView;
        db.views.push({ recordID: 'V' + db.nextView++, lawyerID: u.userID, cin, viewedAt: new Date().toISOString(), fee: chargedFee });
        const lu = db.users.find((x) => x.userID === u.userID);
        lu.balanceDue = (lu.balanceDue || 0) + chargedFee;
        balanceDue = lu.balanceDue;
        save();
      }
      return wait({ ...withHearings(c), chargedFee, balanceDue });
    },
    caseStatus(cin) {
      const c = find(cin);
      if (!c) return fail('No case with CIN ' + cin, 404);
      const hs = withHearings(c).hearings;
      const past = hs.filter((h) => h.status !== 'SCHEDULED');
      return wait({ cin, status: c.status, lastHearing: past[past.length - 1] || null,
        nextHearing: hs.find((h) => h.status === 'SCHEDULED') || null, judgmentDate: c.judgmentDate });
    },

    search(q) {
      const words = q.toLowerCase().split(/\s+/).filter(Boolean);
      return wait(db.cases.filter((c) => c.status === 'CLOSED').filter((c) => {
        const text = Object.values(withHearings(c)).flat().map((v) => typeof v === 'object' && v ? Object.values(v).join(' ') : v).join(' ').toLowerCase();
        return words.every((w) => text.includes(w));
      }).map(({ cin, crimeType, judgmentDate }) => ({ cin, crimeType, judgmentDate })));
    },

    scheduleHearing(cin, date, slot) {
      if (!isWorking(date)) return fail('Not a working day', 409);
      if (db.hearings.some((h) => h.date === date && h.slot === slot && h.status === 'SCHEDULED')) return fail('Slot already booked', 409);
      const hh = { hearingID: 'H' + db.nextHearing++, cin, date, slot, status: 'SCHEDULED', adjournmentReason: null, proceedingSummary: null };
      db.hearings.push(hh);
      save();
      return wait(hh);
    },
    hearingsOn: (date) => wait(db.hearings.filter((h) => h.date === date && h.status === 'SCHEDULED')
      .sort((a, b) => a.slot.localeCompare(b.slot))
      .map((h) => { const c = find(h.cin); return { ...h, defendantName: c.defendantName, crimeType: c.crimeType, presidingJudge: c.presidingJudge }; })),
    adjourn(id, reason) { Object.assign(hearing(id), { status: 'ADJOURNED', adjournmentReason: reason }); save(); return wait(null); },
    proceedings(id, summary) { Object.assign(hearing(id), { status: 'HELD', proceedingSummary: summary }); save(); return wait(null); },
    recordJudgment(id, summary, judgmentSummary, judgmentDate) {
      const h = hearing(id);
      Object.assign(h, { status: 'HELD', proceedingSummary: summary });
      Object.assign(find(h.cin), { status: 'CLOSED', judgmentSummary, judgmentDate: judgmentDate || h.date });
      save();
      return wait(null);
    },

    vacantSlots(date) {
      if (!isWorking(date)) return wait({ date, workingDay: false, slots: [] });
      const taken = db.hearings.filter((h) => h.date === date && h.status === 'SCHEDULED').map((h) => h.slot);
      return wait({ date, workingDay: true, slots: db.calendar.dailySlots.filter((s) => !taken.includes(s)) });
    },
    calendar: () => wait(db.calendar),
    setWeekdays(days) { db.calendar.workingWeekdays = days; save(); return wait(db.calendar); },
    setSlots(slots) { db.calendar.dailySlots = slots; save(); return wait(db.calendar); },
    addHoliday(date) {
      const clash = db.hearings.filter((h) => h.date === date && h.status === 'SCHEDULED');
      if (clash.length) return fail('Hearings are scheduled on this date. Reschedule them first.', 409, { hearings: clash });
      if (!db.calendar.holidays.includes(date)) db.calendar.holidays.push(date);
      db.calendar.holidays.sort();
      save();
      return wait(db.calendar);
    },

    getFee: () => wait(db.fee),
    setFee(amount) { db.fee = { feePerView: amount, updatedAt: new Date().toISOString() }; save(); return wait(db.fee); },

    users: () => wait(db.users.map(({ password, ...u }) => u)),
    createUser(u) {
      if (db.users.some((x) => x.username === u.username)) return fail('Username already taken', 409);
      const nu = { ...u, userID: 'U' + db.nextUser++, active: true, balanceDue: 0 };
      db.users.push(nu);
      save();
      const { password, ...out } = nu;
      return wait(out);
    },
    deleteUser(id) { db.users.find((x) => x.userID === id).active = false; save(); return wait(null); }
  };
})();

# JIS API: what the pages call, and where it goes

The pages call `JIS.api.*` (in `js/api.js`) and use camelCase fields. `api.js` sends each call to
the jis-backend route below and converts field names both ways (`defendant_name` ↔ `defendantName`,
`hearing_id` → `hearingID`, `user_id` → `userID`, `record_id` → `recordID`, `hearing_date` → `date`).
Money arrives as numbers and slots as `HH:MM`.

Base URL: `API_BASE` in `js/config.js` (default `http://localhost:8000`). After login every request
sends `Authorization: Bearer <token>`. Errors are shown from the backend's `detail` (validation errors
are joined into one line). A `401` sends the user back to the sign-in page.

Dates are `YYYY-MM-DD`. CIN is `YYYY-NNNNNN`.

## Auth and current user
| `JIS.api` | Backend | Returns to the page |
|---|---|---|
| `login(username, password)` | `POST /auth/login` | `{token, user: {userID, name, role}}`. Deleted account → 403 |
| `logout()` | none (tokens are stateless) | `null`; the page clears the session |
| `myBalance()` | `GET /users/me` + `GET /users/me/views` | `{balanceDue, viewCount}` (lawyer) |
| `myViews()` | `GET /users/me/views` | `[{recordID, cin, viewedAt, fee}]`, newest first (lawyer) |

## Cases and queries (registrar unless noted)
| `JIS.api` | Backend | Returns |
|---|---|---|
| `registerCase(details)` | `POST /cases` | `Case` with its new `cin` |
| `pendingCases()` | `GET /reports/pending` | query (a), sorted by CIN |
| `resolvedCases(from, to)` | `GET /reports/resolved?from=&to=` | query (b), sorted by start date |
| `hearingsOn(date)` | `GET /reports/hearings?on=` | query (c): SCHEDULED hearings with case details |
| `caseStatus(cin)` | `GET /cases/:cin/status` | query (d): `{cin, status, judgmentDate, lastHearing, nextHearing}` |
| `getCase(cin)` | `GET /cases/:cin` | `Case` + `hearings[]` + `chargedFee` (lawyers only). All users; judges and lawyers get **closed cases only** |
| `search(q)` | `GET /search?q=` | `[{cin, crimeType, judgmentDate}]`, closed cases only, free (judge, lawyer) |

`Case` = `cin, defendantName, defendantAddress, crimeType, crimeDate, crimeLocation, arrestingOfficer, arrestDate, presidingJudge, publicProsecutor, defenseLawyer, startDate, expectedCompletionDate, status (PENDING|CLOSED), judgmentDate, judgmentSummary`

## Hearings (registrar)
| `JIS.api` | Backend | Notes |
|---|---|---|
| `scheduleHearing(cin, date, slot)` | `POST /cases/:cin/hearings` | Returns `Hearing`. 400 if not a working day, 409 if the slot is taken |
| `adjourn(id, reason)` | `POST /hearings/:id/adjourn` | Hearing → ADJOURNED |
| `proceedings(id, summary)` | `POST /hearings/:id/proceedings` | Hearing → HELD, case stays PENDING |
| `recordJudgment(id, summary, judgmentSummary, judgmentDate)` | `POST /hearings/:id/judgment` | Hearing → HELD and case → CLOSED in one transaction. Empty date = hearing date |

`Hearing` = `hearingID, cin, date, slot, status (SCHEDULED|ADJOURNED|HELD), adjournmentReason, proceedingSummary`

An outcome can be recorded only on or after the hearing's date.

## Court calendar and fee
| `JIS.api` | Backend | Returns |
|---|---|---|
| `vacantSlots(date)` | `GET /slots?on=` | `{date, workingDay, slots: ["10:00", …]}` |
| `calendar()` | `GET /calendar` | `{workingWeekdays: ["Mon", …], dailySlots: ["10:00", …], holidays: ["YYYY-MM-DD", …]}` |
| `setWeekdays(days)` | `PUT /calendar/weekdays` | calendar |
| `setSlots(slots)` | `PUT /calendar/slots` | calendar. Slots are start times `HH:MM` |
| `addHoliday(date)` | `POST /calendar/holidays` | calendar. If hearings are booked that day → 409 with `err.data.hearings` |
| `getFee()` | `GET /fee` | `{feePerView, updatedAt}` (all users) |
| `setFee(amount)` | `PUT /fee` | `{feePerView, updatedAt}` |

## Accounts (registrar)
| `JIS.api` | Backend | Returns |
|---|---|---|
| `users()` | `GET /users` | `[{userID, name, username, role, active, balanceDue, viewsCount}]` |
| `createUser(u)` | `POST /users` | user. 409 if the username is taken; password 8+ characters |
| `deleteUser(id)` | `DELETE /users/:id` | user. Soft delete: sign-in stops, history and balance are kept |

# JIS frontend

Plain HTML + CSS + a little vanilla JS. No build step, no framework.

```
index.html       sign in
registrar.html   register case, hearings, queries (a)-(d), accounts, calendar & fee
browse.html      judges and lawyers: keyword search, case record, lawyer charges
css/style.css
js/config.js     API base URL, mock switch
js/api.js        every backend route, in one place (translates to jis-backend)
js/mock.js       in-browser fake backend (only used in mock mode)
js/ui.js         shared helpers
js/registrar.js
js/browse.js
API.md           the request/response contract
```

## Run

Serve the folder with anything static:

```
python -m http.server 5500
```

- Try it without a backend: open `http://localhost:5500/?mock`
  (logins: `registrar`/`registrar`, `judge`/`judge`, `lawyer`/`lawyer`). `?mock=0` turns it off.
- Against the real backend: start jis-backend (`uvicorn jis.main:app --reload`, port 8000), then
  open `http://localhost:5500/`. `API_BASE` in `js/config.js` already points at
  `http://localhost:8000`, and the backend's `.env` allows this origin through `CORS_ORIGINS`.
  If you serve the frontend on another port, add that address to `CORS_ORIGINS`.

## How it talks to the backend

The pages call `JIS.api.*` and never build URLs themselves. `js/api.js` maps each call to a
jis-backend route and converts snake_case ↔ camelCase. `API.md` lists every mapping.

Browser support: current Chrome, Edge, Firefox, Safari (uses `:has()` and `<dialog>`).

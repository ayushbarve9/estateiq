# GrihaValue: rules for contributors and AI agents

## Non-negotiable
- **Data provenance is stated, never inferred.** Every dataset, market benchmark and constant carries a source line. Anything not verified says so. Never write "authenticated", "official" or "retrieved" unless a primary source was actually read.
- **Constants live in `backend/config.py` only.** Market benchmarks live in `backend/data/markets.json`. Nothing financial appears in route handlers, the model code or the frontend.
- **No secrets in the browser.** `ANTHROPIC_API_KEY` is read from the environment on the server only.
- **Typed errors.** 400 for business-rule violations, 422 for schema errors, 503 when the model or chat is unavailable. The frontend renders loading, error and empty states.
- **Prove it.** Run `python -m pytest backend/tests -q` and report the result before saying something works. Browser behaviour is checked with a headless browser against a running server.
- **Retrain after changing inputs.** Editing `markets.json`, the feature list or scikit-learn requires `python -m backend.train`. The bundle records a SHA-256 of `markets.json` and warns when it is stale.

## Layout
```
backend/
  config.py      constants with source and verification status
  markets.py     market reference loader (cities, states, localities)
  features.py    feature layout shared by training and inference
  train.py       synthetic generation or CSV ingestion, fit, evaluate, save
  model.py       bundle loader with schema and version checks, inference
  finance.py     LTV cap, EMI, stamp duty, GST, acquisition cost
  advisor.py     grounded chat prompt
  schemas.py     request and response models with domain validation
  main.py        routes, typed errors, security headers, static frontend
  data/markets.json
  tests/         finance, endpoints, training, bundle quality
frontend/        vanilla HTML, CSS and ES modules; no build step
models/          trained bundle (regenerate with backend.train)
```

## Frontend rules
- No framework, no bundler, no CDN. Everything is served from `/`.
- CSP is strict (`script-src 'self'`). No inline scripts, no `onclick` attributes.
- Charts are hand-built SVG or DOM. They must respect `prefers-reduced-motion`.
- Every figure shown to a user must come from the API or from a documented constant.

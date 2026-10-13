# GrihaValue

Residential valuation and acquisition-cost estimator for India. Give it a city, a micro-market and the unit details, and it returns:

- a model-based market value with a price range (P10 to P90),
- the RBI loan-to-value cap, loan amount, down payment and monthly EMI,
- indicative stamp duty and registration, and GST where it applies,
- an EMI grid across rates and tenures,
- nearby comparables from the training data,
- a grounded question-and-answer panel that only uses those figures.

It is a FastAPI service with a vanilla HTML, CSS and JavaScript frontend. There is no framework and no build step.

## Read this first: what the numbers mean

**The shipped model is trained on generated data.** `python -m backend.train` with no arguments builds listings from the market benchmarks in `backend/data/markets.json`, adds noise, and fits to that. Its accuracy figures therefore show how well it recovers the generator, not how well it predicts the real market. The reported holdout error is 8.9% against a noise floor of 8.0%. A locality-median baseline gets 13.2%. Those numbers are useful for checking that the pipeline works. They are not evidence of real-world accuracy.

**Market benchmarks are mixed in quality.**
- Seven metros (Bengaluru, Mumbai MMR, Delhi NCR, Hyderabad, Pune, Chennai, Kolkata) take their base rates and locality premiums from a listings file in the previous project. Its origin could not be verified.
- Sixteen other cities are planning estimates. They are not transaction data.
- Every city in `markets.json` is labelled with its source.

**Stamp duty rates are approximate.** Only some states were carried over from the previous project, and none were checked against a current gazette. Women-buyer rebates, metro surcharges and cess are not modelled. The API marks every stamp duty figure as `APPROXIMATE`, and the UI says so.

**GST is an upper bound.** It applies the full rate to property value. Land-value abatement on under-construction homes is not modelled.

**The price range is not calibrated well yet.** The 80% target interval covered 75% of holdout prices on the shipped model and 60% on a 2,000-row example. Treat it as indicative.

The software can use real transactions. Supply a CSV and it trains on that instead. It does not check where the data came from.

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Optional: retrain. The shipped bundle in models/ is already trained.
python -m backend.train

uvicorn backend.main:app --reload    # http://127.0.0.1:8000
```

Open http://127.0.0.1:8000 for the app and http://127.0.0.1:8000/docs for the API reference.

### Train on real data

```bash
python -m backend.train --csv path/to/transactions.csv --out models/grihavalue.joblib
```

Required columns: `City`, `Locality`, `BHK`, `Area_SqFt`, `Price_INR`, `Construction_Status`, `Property_Type`.

Optional columns, with defaults when missing: `Bathrooms` (= BHK), `Furnishing` (Semi-Furnished), `Age_Years` (0), `Parking` (1), `Latitude` and `Longitude` (from `markets.json`).

Each City and Locality pair must exist in `backend/data/markets.json`. Rows with non-positive area or price, or with a price per sq.ft. outside 500 to 500,000, are dropped and counted in the bundle's metadata. At least 500 usable rows are needed. Use several thousand. Interval coverage was poor on small samples.

An example in the right format, filled with synthetic values, is at `data/synthetic/example_transactions_SYNTHETIC.csv`.

### Chat (optional)

Set `ANTHROPIC_API_KEY` in `.env` to enable the streaming assistant at `/api/chat`. Without a key, the in-page advisor answers from the estimate figures alone. It does not call any external service.

## How the estimate works

1. **Model.** A voting ensemble of random forest and histogram gradient boosting predicts log price per square foot. The predicted price is that rate times the area. Two quantile gradient-boosting models give the P10 and P90 bounds.
2. **Loan.** The requested down payment sets the loan. If the loan falls in a higher bracket, the RBI cap applies: 90% of value up to ₹30 L, 80% from ₹30 L to ₹75 L, 75% above ₹75 L. The buyer must then put in more equity.
3. **Costs.** EMI uses reducing-balance amortisation. Stamp duty is the state rate times value. GST applies only to under-construction homes, at 5% or 1% for homes under ₹45 L.
4. **Market context.** Every city and locality is also scored on one reference unit (3 BHK, 1,500 sq.ft., ready, 2 years old, semi-furnished), so the market views compare like with like.

All financial constants are in `backend/config.py`, each with its source and verification status.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Process and model status |
| GET | `/api/meta` | Cities, localities, options, bounds, model metrics, provenance |
| GET | `/api/market-overview` | Model rate per sq.ft. by city and locality, for one reference unit |
| POST | `/api/estimate` | Full estimate for one unit |
| POST | `/api/finance/sensitivity` | EMI grid across rates and tenures, using the same loan cap as the estimate |
| POST | `/api/chat` | Streaming reply grounded in an estimate (needs `ANTHROPIC_API_KEY`) |

Errors: `400` for business-rule violations (for example an unknown locality), `422` for schema violations, `503` when the model bundle is missing or chat is not configured.

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/estimate -H "Content-Type: application/json" -d '{
  "city": "Bengaluru", "locality": "Whitefield", "bhk": 3, "area_sqft": 1500,
  "bathrooms": 3, "property_type": "Apartment", "furnishing": "Semi-Furnished",
  "construction_status": "Ready to Move", "age_years": 2, "parking": 1,
  "down_payment_pct": 20, "annual_rate_pct": 8.5, "tenure_years": 20
}'
```

## Tests

```bash
python -m pytest backend/tests -q
```

The suite covers the finance formulas (including amortisation to zero and the LTV tier boundaries), the API contract and its error paths, training reproducibility and CSV validation, and quality gates on the shipped bundle. The gates fail if the model stops beating the baseline or drifts far from the noise floor.

Browser behaviour was checked with a headless Chromium against a running server: loading, estimate, validation, theme switching, the advisor, and a 390 px mobile layout. That check is not part of the test suite.

## Docker

```bash
docker build -t grihavalue .
docker run -p 8000:8000 --env-file .env grihavalue
```

The image runs as a non-root user and includes a health check on `/api/health`. The Docker build has not been run in this environment.

## Project layout

```
backend/            API, finance, model, training, tests
backend/data/       markets.json (cities, states, localities, benchmarks)
frontend/           index.html, css/styles.css, js/*.js, assets/
models/             trained bundle
data/synthetic/     example CSV in the ingestion format (synthetic)
AGENTS.md           rules for contributors and automated agents
```

## Security

- Strict Content-Security-Policy: scripts and styles from the same origin only, no inline scripts, no third-party requests.
- `X-Frame-Options: DENY`, `nosniff`, no referrer.
- Request bodies reject unknown fields and implausible values (for example, too little area for the stated BHK).
- The Anthropic key is read from the environment on the server and is never returned to the browser.

Not yet done: rate limiting, authentication, and request logging beyond the defaults.

## Licence

No licence has been chosen. Add one before publishing.

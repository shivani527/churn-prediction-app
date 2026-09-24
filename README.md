# Dispatch Desk — Food Delivery Churn Prediction

A full-stack app built around the churn model trained in `Churn_Prediction.ipynb`:
a **FastAPI backend** that serves predictions from the trained
scikit-learn model, and a **plain HTML/CSS/JS frontend** styled as a
courier "dispatch desk" — fill in a customer's survey answers on a
clipboard, run the check, and a printed risk ticket comes out the other
side.

```
churn-prediction-app/
├── backend/
│   ├── app/
│   │   ├── main.py        FastAPI app + routes
│   │   ├── model.py       Loads the trained model, builds features, predicts
│   │   └── schemas.py     Pydantic request/response contracts
│   ├── model/              <- put churn_model.pkl + selected_cols.pkl here
│   ├── tests/
│   │   └── test_api.py    pytest suite (passes with or without a real model)
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── style.css
    └── script.js           No build step, no framework
```

## Quickstart

**1. Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** — that's a free interactive API
explorer (Swagger UI), generated automatically from the Pydantic schemas.

**2. Frontend**

In a second terminal:

```bash
cd frontend
python -m http.server 5500
```

Open **http://localhost:5500** in a browser.

**3. (Optional) Wire up your real trained model**

The app runs immediately with no model files — every prediction is
served by a transparent, rule-based fallback and the UI clearly labels
it `demo_mode: true`. To use the actual trained model from the notebook,
add this cell at the end of the notebook (it's the same two lines
already in the notebook, just confirming the target path):

```python
import joblib
joblib.dump(best_model_obj, "churn_model.pkl")
joblib.dump(list(X_train.columns), "selected_cols.pkl")
```

Then copy both files into `backend/model/` and restart the backend. No
code changes needed — `app/model.py` detects the files and switches over
automatically.

**4. Run the tests**

```bash
cd backend
pytest -v
```

---

## Deploying it (so you have a live link, not just a zip)

Free tier, no credit card needed for either piece. Rough total time: ~15 minutes.

### Step 0 — push this folder to GitHub

Deploying from GitHub is far less fiddly than uploading files by hand,
and both platforms below auto-redeploy on every future `git push`.

```bash
cd churn-prediction-app
git init
git add .
git commit -m "Initial commit"
# create an empty repo on github.com first, then:
git remote add origin https://github.com/<your-username>/churn-prediction-app.git
git branch -M main
git push -u origin main
```

If you already put your real `churn_model.pkl` / `selected_cols.pkl` in
`backend/model/`, `.gitignore` currently excludes them (`backend/model/*.pkl`)
so they *won't* get pushed. Either remove that line from `.gitignore` so
your real model deploys too, or upload the files directly through the
Render dashboard's shell/disk — see Render's docs if you want to keep
them out of git.

### Step 1 — deploy the backend on Render

1. Go to **render.com** → sign up (GitHub login is fastest) → **New +** → **Blueprint**.
2. Point it at your GitHub repo. Render reads `render.yaml` at the repo
   root automatically and configures everything (build command, start
   command, health check) for you.
3. Click **Apply**. First deploy takes a couple of minutes.
4. Once live, copy the URL Render gives you — something like
   `https://churn-prediction-api-xxxx.onrender.com`.
5. Confirm it's actually working: visit `<that-url>/health` in a browser
   — you should see `{"status":"ok", ...}`.

*(No `render.yaml`, or prefer doing it by hand? New + → Web Service →
pick the repo → set **Root Directory** to `backend`, **Build Command**
to `pip install -r requirements.txt`, **Start Command** to
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`.)*

> Free-tier Render web services spin down after 15 minutes of no
> traffic and take ~30–60 seconds to wake back up on the next request.
> That's normal — worth knowing so you're not confused the first time
> your demo link is briefly slow, and honestly a fine thing to mention
> if it comes up ("first request after idle is slower — the tradeoff of
> a free-tier host").

### Step 2 — point the frontend at it

Open `frontend/index.html` and replace the placeholder with the URL
from Step 1:

```js
window.CHURN_API_BASE =
  location.hostname === "localhost" || location.hostname === "127.0.0.1"
    ? "http://localhost:8000"
    : "https://churn-prediction-api-xxxx.onrender.com";   // <- your real URL
```

Commit and push that one-line change.

### Step 3 — deploy the frontend on Netlify

1. Go to **netlify.com** → sign up → **Add new site** → **Import an existing project** → GitHub → pick your repo.
2. Set **Base directory** to `frontend`, leave **Build command** blank
   (there isn't one — it's static files), set **Publish directory** to `frontend`.
3. Deploy. Netlify gives you a URL like `https://your-site-name.netlify.app`.

*(Even faster, no git required: drag the `frontend` folder straight onto*
*netlify.com/drop*.)*

### Step 4 — lock down CORS

Back on Render, open your backend service → **Environment** → set:

```
ALLOWED_ORIGINS = https://your-site-name.netlify.app
```

Save, let it redeploy, and refresh the frontend. The status dot in the
top-left of the UI is your confirmation signal — mint/amber means it
reached the backend, coral means something's still misconfigured
(usually a typo in one of the two URLs above).

You now have: a live link for your resume/portfolio, a repo showing
real commit history, and a backend that's actually configured the way
a small production service would be — all good material for "walk me
through how you'd deploy this" in an interview.

---

## Architecture decisions (and why — useful for interviews)

**Why FastAPI over Flask?**
Free request validation and OpenAPI docs from the same Pydantic models
used elsewhere in the code — no separate schema to maintain, and invalid
input (e.g. an occupation the model was never trained on) is rejected
with a `422` *before* it reaches the model, rather than causing a
confusing 500 or a silently wrong prediction.

**Why does `/predict` reject unknown categories automatically?**
`ChurnRequest` uses `Literal[...]` types instead of `str` for every
categorical field. Pydantic enforces those exact values, and the same
list of valid values is exposed at `GET /options` so the frontend (or
any other client) never has to hardcode — and risk drifting from — the
categories the model actually saw during training.

**Why a demo-mode fallback instead of just failing without a model?**
A portfolio project that only works after a multi-step model-training
setup is a portfolio project nobody actually runs. `ChurnModel` checks
for the two `.pkl` files on startup; if they're missing, it falls back
to a small, clearly-labeled heuristic instead of crashing, so the
whole stack — API, tests, UI — is demoable in under a minute. Swapping
in the real model afterwards changes zero application code.

**Why no React/build step on the frontend?**
This is a single form and a result view — a framework would add a build
pipeline and dependency surface with no real benefit here. It also means
every line of the frontend is something you can point to and explain
line-by-line in an interview, with no generated code hiding behind it.
(Swapping in React/Vue later is straightforward: `/options` and
`/predict` are just JSON endpoints, agnostic to what calls them.)

**Why is CORS configured via an environment variable?**
Locally, `ALLOWED_ORIGINS` is unset so it defaults to `"*"` — any port on
your machine can call the API, which is what you want while developing.
In production, setting `ALLOWED_ORIGINS=https://your-frontend-url` locks
the API down to just that origin, with zero code changes between
environments. Small detail, but "config over hardcoding" is exactly the
kind of thing worth calling out when someone asks about production
readiness.

---

## Ideas for extending this (good "what would you do next" answers)

- **Dockerize** both services with a `docker-compose.yml` so the whole
  stack starts with one command.
- **Model explainability**: add a `/predict/explain` endpoint using SHAP
  on the logistic regression coefficients, and surface the top 2–3
  factors driving each prediction on the receipt itself.
- **Model versioning**: store a small metadata file alongside the
  `.pkl`s (training date, ROC-AUC, feature count) and expose it via
  `/health`, so the UI can show which model version is live.
- **Batch scoring**: a `/predict/batch` endpoint that accepts a CSV of
  customers and returns a scored CSV — useful for a retention team
  running this weekly rather than one customer at a time.
- **Auth**: this is currently a fully open API; adding an API key or
  JWT check on `/predict` would be the natural next step before any
  real deployment.
- **CI**: a GitHub Actions workflow running `pytest` on every push is a
  five-minute addition that's an easy interview talking point.

## Notes

- The full feature set the model was trained on (age, gender, family
  size, meal preferences, etc.) isn't collected in this UI — matching
  the same 12-field "quick predict" shortcut the notebook's own
  `predict_customer()` function used, with sensible defaults for
  everything else. If you want every field exposed, extend
  `ChurnRequest` in `schemas.py` and the corresponding form fields in
  `frontend/script.js` — the mapping in `RATING_FIELD_MAP` /
  `DEFAULTS` in `backend/app/model.py` shows exactly where those extra
  fields plug in.

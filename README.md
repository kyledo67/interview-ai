# InterviewAI

AI mock interviews with a React frontend, FastAPI backend, and PostgreSQL database.

Live app: [InterviewAI on Vercel](https://interview-ai-ashy-eight.vercel.app)

## Vercel deployment

Import this repository into Vercel with the repository root (`./`) and the **Other** framework preset. `vercel.json` builds React and deploys `api/index.py` as a Python 3.12 function. Static assets use Vercel's CDN; browser routes fall back to React; API routes retain their original paths.

Copy the existing Render environment variables into Vercel before deploying: `DATABASE_URL`, `SECRET_KEY`, `GEMINI_API_KEY`, `VOGENT_API_KEY`, `JUDGE0_API_KEY`, `JUDGE0_URL`, `ALGORITHM`, and `ACCESS_TOKEN_EXPIRE_MINUTES`. Preserve the database URL and signing key to retain users and interview history. `API_KEY`, if present, can also be copied for compatibility.

For Supabase, use a connection URL reachable from Vercel (the transaction pooler on port 6543 is suitable). `NullPool` prevents warm functions from retaining idle database connections. Existing table initialization creates the new `resumes` table; the database role needs permission to create it.

Uploaded PDFs (up to 4 MB) are stored privately in PostgreSQL instead of local disk. Candidate context is reconstructed per request, and the resume is deleted when its interview ends. Existing resumes on Render's ephemeral disk must be uploaded again after migration.

The frontend uses same-origin API requests in production and previews. Function duration is configured to 300 seconds for AI operations. Existing frontend lint warnings remain warnings during deployment builds.

Verify the landing page, browser routes, `/health`, and `/openapi.json`, then test login, PDF upload, interview messages, speech, and code execution. Once production works, suspend the Render web service. Keep the PostgreSQL database running.

## Local development

Copy `backend/.env.example` to `backend/.env` and fill in the values. From `backend`, install `imports.txt` and run `uvicorn app.main:app --host 0.0.0.0 --port 8001`. In another terminal, run `npm ci --prefix frontend` and `npm start --prefix frontend`; the React proxy forwards API calls to port 8001.

## Migration tests

Install `requirements.txt` plus `pytest`, then run `python -m pytest -q`. Tests use isolated SQLite data and do not call production AI services. Build the frontend with `npm run build --prefix frontend`.


## Interview progression and code checks

Behavioral interviews switch after five replies or 15 minutes. The browser checks the server clock every ten seconds, including when the candidate is silent. Interview JSON state and transcript changes persist across requests. Technical interviews end after a verified solution or 45 minutes.

Run Code uses the authenticated `/code/execute` API and the problem stored on the server. Python and JavaScript submissions implement the named function and are wrapped in a multi-case test harness. Java and C++ standalone programs receive a JSON array of argument lists on stdin and must print a JSON array of return values. Only matching all server-owned expected values marks a solution correct; execution success alone does not. Judge0 failures are shown to the candidate.

## AI context and transcript safeguards

Technical prompts include the server-assigned problem and constraints, selected language, latest editor snapshot, and server-verified grading summary. Editor context syncs after 1.5 seconds of inactivity and is also sent with every candidate answer/run. A code hash identifies whether prior results apply to the current editor contents.

Candidate text, code/comments, PDFs, printed output, and history remain untrusted model input, separate from Gemini system instructions. Execution output cannot override the authoritative pass counts. Evaluation uses the stored server transcript rather than accepting fabricated browser AI/System turns.

Candidate messages are limited to 2,000 characters, code to 60,000, and AI replies to 4,000. Stored transcripts are capped at 120 entries or 80,000 characters; model history is bounded to 24,000 characters and at most 32 recent turns. Explicit instruction-override attempts are redirected before generation. A context-aware relevance classifier also redirects off-topic requests without storing them or advancing interview counters. If classification is unavailable, the request fails closed with a retry message. These measures reduce prompt-injection risk; model-based filtering is not a guarantee against every adversarial prompt.

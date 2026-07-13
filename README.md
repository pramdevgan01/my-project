# FEMAS Backend — Forensic Evidence Multi-Agent System

Backend for an enterprise multi-agent forensic evidence management system for Indian law
enforcement (BNSS/BSA 2023/DPDPA-oriented): FastAPI REST API, OpenAI Agents SDK
orchestration (Triage → Digital Forensics → Legal Compliance → Reporting, with handoffs
and guardrails), and MCP tool servers exposed over SSE and mounted into the same FastAPI
app. React/shadcn frontend is a separate, later piece of work.

## What's real vs. simulated

- **Real**: JWT auth + RBAC, SQLite persistence, SHA-256/MD5 file hashing, Section 63 BSA
  2023 certificate PDF generation, chain-of-custody logging, DPDPA-style audit logging,
  the MCP protocol/transport itself, and the full OpenAI Agents SDK orchestration
  (agents, handoffs, guardrails, tool-visibility Gateway).
- **Simulated** (clearly labeled `SIMULATED_*` in every response): CCTNS/ICJS/NDSO data
  (`app/mcp_servers/gov_systems_tools.py`) and device forensics — EXIF, malware scan,
  mobile filesystem parsing (`app/mcp_servers/forensics_tools.py`) — since this project
  has no real access to Indian government infrastructure or forensic tooling. The tool
  *interfaces* are built so a real backend can be swapped in later without changing the
  agents that call them.
- **Adapted**: human-in-the-loop certificate approval is a DB status flag
  (`pending_approval` → `approved`/`rejected`) plus a REST endpoint restricted to
  `nodal_officer`/`admin`, rather than a literal blocking mid-run pause. Workflow tracing
  is stored as `WorkflowRun`/`WorkflowStep` rows instead of an external tracing SaaS.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then set OPENROUTER_API_KEY (free at https://openrouter.ai/keys) and a real SECRET_KEY
```

## Run

```bash
source .venv/bin/activate
fastapi dev main.py --host 0.0.0.0 --port 8000
# or: uvicorn main:app --host 0.0.0.0 --port 8000
```

On first boot, if no users exist yet, an admin account is seeded automatically:
`admin` / `ChangeMe123!` — log in and change/rotate this immediately, and use
`POST /auth/register` (admin-only) to create real `officer`, `forensic_scientist`, and
`nodal_officer` accounts.

Swagger UI: `http://localhost:8000/docs`

## Typical flow

1. `POST /auth/login` (officer) → `POST /cases` → `POST /evidence` (multipart file upload;
   SHA-256/MD5 computed and a chain-of-custody event logged automatically).
2. `POST /workflows/run` with `case_id`/`evidence_id` runs the agent pipeline: Triage looks
   up FIR metadata, hands off to Digital Forensics (parses/scans the evidence), hands off
   to Legal Compliance (verifies integrity, drafts the Section 63(4) BSA certificate as
   `pending_approval`), hands off to Reporting (produces the final structured report).
   Requires `OPENROUTER_API_KEY` to be set — without it the run fails gracefully and the
   failure reason is recorded on the `WorkflowRun`.
3. `GET /workflows/{id}` returns the full step-by-step trace.
4. A `nodal_officer`/`admin` reviews `GET /certificates/{id}` and calls
   `POST /certificates/{id}/approve` (or `/reject`) — this is the human sign-off gate.
5. `GET /certificates/{id}/download` returns the rendered PDF.
6. Admins can review `GET /audit-logs` for the full DPDPA-style access trail.

## MCP tool servers

Mounted at `/mcp/legal`, `/mcp/forensics`, `/mcp/gov-systems` (SSE transport). Every
connection requires a valid FEMAS JWT bearer token (enforced by
`app/mcp_servers/gateway.py`); per-role tool visibility is enforced separately on the
Agents SDK client side via `MCPServerSse(tool_filter=...)` in
`app/agents_system/orchestrator.py`, using the shared policy in
`app/mcp_servers/access_policy.py`.

## Tests

```bash
source .venv/bin/activate
pytest
```

## FAQs & Debugging

### I do not see browser in my workspace

Studio will automatically open the app in a new browser tab. If not, you can use the
following steps to open the simple browser:

1. From VS Code command palette (`Ctrl/Cmd + Shift + P`), run **Studio Manager:
   SimpleBrowser Default URL** command. This will open the app in a new browser tab.
2. Your app runs on a hosted environment which can be accessed using the host id and port
   provided in the file **.vscode/.studio/studio-env.json**. Use these values to create
   the URL as follows: `https://<STUDIO_HOST_ID>-8000.<STUDIO_DOMAIN>`

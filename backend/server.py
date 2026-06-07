"""Publication Repo — shared third-party publication store for the AI Societies.

Created 2026-05-20. Sits beside the two polities (claude on :8769, codex on
:8768) as a third workspace member at :9100.

Concept
-------

Both polities author research papers locally (via their own
PaperPublisherService). The "publication" step is now bilateral: a polity
SUBMITS a finalized paper to this repo, which holds it for the world to see.
Cross-society research now travels through THREE connector channels:

    diplomatic   — government-to-government messages, treaties, knowledge
    commerce     — business-to-business offers, transfers, ledger
    publication  — research papers (this repo)

Auth: each polity has a `PUBLICATION_KEY_<polity_id>` bearer token. Repo
accepts submissions only from registered polities. Read paths are auth-less
because publications are public-facing by design.

Storage: SQLite at data/publications.sqlite. Idempotent on
(origin_polity_id, origin_paper_id) — re-submitting the same paper updates
in place rather than duplicating.

API
---

  POST /publications/v1/submit     — polity submits a paper (auth required)
  GET  /publications/v1/manifest   — JSON index of all papers
  GET  /publications/v1/papers/<id> — fetch one paper (markdown + metadata)
  GET  /publications/v1/recent?limit= — recent submissions, newest first
  GET  /publications/v1/search?q=  — naive LIKE search
  GET  /health                     — liveness probe
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parent.parent
# DB path can be overridden via PUBLICATION_REPO_DB so tests can point at an
# isolated temp file. Default keeps the original on-disk location.
DB_PATH = Path(os.environ.get("PUBLICATION_REPO_DB", str(ROOT / "data" / "publications.sqlite")))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Storage ─────────────────────────────────────────────────────────────────


SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    paper_id TEXT PRIMARY KEY,                  -- society://papers/<polity>/<origin_paper_id>
    origin_polity_id TEXT NOT NULL,             -- claude | codex | ...
    origin_paper_id TEXT NOT NULL,              -- the polity's own paper_id
    title TEXT NOT NULL,
    abstract TEXT NOT NULL DEFAULT '',
    body_md TEXT NOT NULL DEFAULT '',
    domain TEXT NOT NULL DEFAULT '',
    claims_json TEXT NOT NULL DEFAULT '[]',
    citations_json TEXT NOT NULL DEFAULT '[]',
    author_agent_id TEXT NOT NULL DEFAULT '',
    author_branch_id TEXT NOT NULL DEFAULT '',
    doi_stub TEXT NOT NULL DEFAULT '',
    origin_published_at TEXT,
    submitted_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    retracted_at TEXT,
    UNIQUE (origin_polity_id, origin_paper_id)
);

CREATE INDEX IF NOT EXISTS idx_papers_polity ON papers (origin_polity_id);
CREATE INDEX IF NOT EXISTS idx_papers_domain ON papers (domain);
CREATE INDEX IF NOT EXISTS idx_papers_submitted ON papers (submitted_at DESC);
"""


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


# ─── Auth ────────────────────────────────────────────────────────────────────


def _polity_tokens() -> dict[str, str]:
    """Map polity_id -> expected bearer token from env.

    Env vars: PUBLICATION_KEY_<POLITY_ID>. Matches the DIPLOMATIC_KEY_*
    pattern the polities already use.
    """
    out: dict[str, str] = {}
    for key, value in os.environ.items():
        if key.startswith("PUBLICATION_KEY_") and value:
            polity_id = key[len("PUBLICATION_KEY_"):].lower()
            out[polity_id] = value
    return out


def require_polity_token(
    x_polity: Optional[str] = Header(default=None, alias="X-Polity"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> str:
    """Validate that the request comes from a registered polity."""
    if not x_polity:
        raise HTTPException(status_code=401, detail="X-Polity header required")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    token = authorization.split(" ", 1)[1].strip()
    tokens = _polity_tokens()
    expected = tokens.get(x_polity.lower())
    if not expected:
        raise HTTPException(status_code=403, detail=f"Polity '{x_polity}' not registered for publication")
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid publication key")
    return x_polity.lower()


# ─── Reader auth (added 2026-05-23, audit Q6) ────────────────────────────────
# Read endpoints (manifest, papers, recent, search) are public by default for
# backwards compat. To enable private-reads, set
# `PUBLICATION_REPO_REQUIRE_AUTH_ON_READS=1` in the daemon env. With it on,
# every read needs Authorization: Bearer <token> where <token> is any value
# from the `PUBLICATION_KEY_*` polity allowlist OR a value from the read-only
# allowlist `PUBLICATION_READER_KEY` (single value, comma-separated multi
# allowed).
#
# The public surface that survives auth-on-reads is `/health` plus the new
# `/publications/v1/manifest-summary` (counts only, no titles/abstracts/bodies).
# These let Overseer + the NEDs render liveness cards without holding a key.


def _reader_tokens() -> set[str]:
    """Set of bearer tokens valid for read endpoints.

    Includes every polity write key (a polity can read what it submits) plus
    any tokens in PUBLICATION_READER_KEY (comma-separated). Empty set means
    no reader-only keys are configured.
    """
    tokens: set[str] = set(_polity_tokens().values())
    raw = os.environ.get("PUBLICATION_READER_KEY", "")
    for t in raw.split(","):
        t = t.strip()
        if t:
            tokens.add(t)
    return tokens


def _read_auth_required() -> bool:
    return os.environ.get("PUBLICATION_REPO_REQUIRE_AUTH_ON_READS") in {"1", "true", "TRUE", "yes"}


def require_reader_token(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> Optional[str]:
    """If auth-on-reads is enabled, require a valid Bearer token; else no-op.

    Returns the token (or None when auth is disabled) so handlers can audit.
    """
    if not _read_auth_required():
        return None
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required (reads are private)")
    token = authorization.split(" ", 1)[1].strip()
    if token not in _reader_tokens():
        raise HTTPException(status_code=403, detail="Invalid reader token")
    return token


# ─── Models ──────────────────────────────────────────────────────────────────


class PaperSubmission(BaseModel):
    """Shape of a paper submitted by a polity. Mirrors the polity's
    research_papers schema, plus the polity claim."""
    origin_paper_id: str
    title: str
    abstract: str = ""
    body_md: str = ""
    domain: str = ""
    claims: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    author_agent_id: str = ""
    author_branch_id: str = ""
    doi_stub: str = ""
    origin_published_at: Optional[str] = None


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _row_to_paper(row) -> dict[str, Any]:
    d = dict(row)
    d["claims"] = json.loads(d.pop("claims_json") or "[]")
    d["citations"] = json.loads(d.pop("citations_json") or "[]")
    return d


def _build_paper_id(polity_id: str, origin_paper_id: str) -> str:
    return f"society://papers/{polity_id}/{origin_paper_id}"


# ─── App ─────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.conn = get_conn()
    try:
        yield
    finally:
        app.state.conn.close()


app = FastAPI(title="AI Society Publication Repo", version="0.1.0", lifespan=lifespan)


def db(request: Request) -> sqlite3.Connection:
    return request.app.state.conn


# ─── Endpoints ───────────────────────────────────────────────────────────────


@app.get("/health")
def health(conn: sqlite3.Connection = Depends(db)):
    count = conn.execute("SELECT COUNT(*) AS c FROM papers").fetchone()["c"]
    registered = list(_polity_tokens().keys())
    return {
        "ok": True,
        "papers_total": int(count),
        "polities_registered": registered,
        "as_of": _now(),
    }


@app.post("/publications/v1/submit")
def submit(
    sub: PaperSubmission,
    polity_id: str = Depends(require_polity_token),
    conn: sqlite3.Connection = Depends(db),
):
    """Polity submits a paper. Idempotent on (origin_polity_id, origin_paper_id):
    re-submitting updates the existing row rather than duplicating."""
    paper_id = _build_paper_id(polity_id, sub.origin_paper_id)
    now = _now()
    existing = conn.execute(
        "SELECT paper_id FROM papers WHERE origin_polity_id = ? AND origin_paper_id = ?",
        (polity_id, sub.origin_paper_id),
    ).fetchone()
    if existing is not None:
        with conn:
            conn.execute(
                """
                UPDATE papers
                   SET title = ?, abstract = ?, body_md = ?, domain = ?,
                       claims_json = ?, citations_json = ?,
                       author_agent_id = ?, author_branch_id = ?,
                       doi_stub = ?, origin_published_at = ?,
                       updated_at = ?
                 WHERE paper_id = ?
                """,
                (
                    sub.title, sub.abstract, sub.body_md, sub.domain,
                    json.dumps(sub.claims), json.dumps(sub.citations),
                    sub.author_agent_id, sub.author_branch_id,
                    sub.doi_stub, sub.origin_published_at,
                    now, paper_id,
                ),
            )
        action = "updated"
    else:
        with conn:
            conn.execute(
                """
                INSERT INTO papers
                    (paper_id, origin_polity_id, origin_paper_id,
                     title, abstract, body_md, domain,
                     claims_json, citations_json,
                     author_agent_id, author_branch_id, doi_stub,
                     origin_published_at, submitted_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    paper_id, polity_id, sub.origin_paper_id,
                    sub.title, sub.abstract, sub.body_md, sub.domain,
                    json.dumps(sub.claims), json.dumps(sub.citations),
                    sub.author_agent_id, sub.author_branch_id, sub.doi_stub,
                    sub.origin_published_at, now, now,
                ),
            )
        action = "created"
    row = conn.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,)).fetchone()
    return {"action": action, "paper": _row_to_paper(row)}


@app.get("/publications/v1/manifest-summary")
def manifest_summary(conn: sqlite3.Connection = Depends(db)):
    """Public counts-only manifest. Survives auth-on-reads so consumers
    can render liveness (publication-repo card, audit-tick) without holding
    a reader key. Added 2026-05-23 (audit Q6)."""
    rows = conn.execute(
        "SELECT origin_polity_id, domain FROM papers"
    ).fetchall()
    by_polity: dict[str, int] = {}
    by_domain: dict[str, int] = {}
    for r in rows:
        by_polity[r["origin_polity_id"]] = by_polity.get(r["origin_polity_id"], 0) + 1
        if r["domain"]:
            by_domain[r["domain"]] = by_domain.get(r["domain"], 0) + 1
    return {
        "repo": "ai-society-publication-repo",
        "version": "0.1.0",
        "as_of": _now(),
        "papers_total": len(rows),
        "by_polity": by_polity,
        "by_domain": by_domain,
        "auth_on_reads": _read_auth_required(),
    }


@app.get("/publications/v1/manifest")
def manifest(
    conn: sqlite3.Connection = Depends(db),
    _reader: Optional[str] = Depends(require_reader_token),
):
    """Machine-readable index of every paper. Use this to bootstrap an
    external consumer (search engine, MCP server, web crawler)."""
    rows = conn.execute(
        "SELECT paper_id, origin_polity_id, origin_paper_id, title, domain, "
        "       author_branch_id, doi_stub, submitted_at, retracted_at "
        "  FROM papers ORDER BY submitted_at DESC"
    ).fetchall()
    by_polity: dict[str, int] = {}
    by_domain: dict[str, int] = {}
    for r in rows:
        by_polity[r["origin_polity_id"]] = by_polity.get(r["origin_polity_id"], 0) + 1
        if r["domain"]:
            by_domain[r["domain"]] = by_domain.get(r["domain"], 0) + 1
    return {
        "repo": "ai-society-publication-repo",
        "version": "0.1.0",
        "as_of": _now(),
        "papers_total": len(rows),
        "by_polity": by_polity,
        "by_domain": by_domain,
        "papers": [dict(r) for r in rows],
    }


@app.get("/publications/v1/papers/{paper_id:path}")
def get_paper(
    paper_id: str,
    conn: sqlite3.Connection = Depends(db),
    _reader: Optional[str] = Depends(require_reader_token),
):
    """Fetch a single paper (markdown + metadata).

    paper_id can be either the full canonical form
    (society://papers/<polity>/<id>) or just the polity's origin_paper_id
    (we'll resolve by uniqueness)."""
    row = conn.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,)).fetchone()
    if row is None:
        # Try as origin_paper_id (most-recent wins; should be unique anyway).
        row = conn.execute(
            "SELECT * FROM papers WHERE origin_paper_id = ? ORDER BY submitted_at DESC LIMIT 1",
            (paper_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"paper {paper_id!r} not found")
    return _row_to_paper(row)


@app.get("/publications/v1/recent")
def recent(
    limit: int = Query(default=50, ge=1, le=500),
    polity: Optional[str] = None,
    conn: sqlite3.Connection = Depends(db),
    _reader: Optional[str] = Depends(require_reader_token),
):
    if polity:
        rows = conn.execute(
            "SELECT * FROM papers WHERE origin_polity_id = ? "
            "ORDER BY submitted_at DESC LIMIT ?",
            (polity, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM papers ORDER BY submitted_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return {"papers": [_row_to_paper(r) for r in rows]}


@app.get("/publications/v1/search")
def search(
    q: str,
    conn: sqlite3.Connection = Depends(db),
    _reader: Optional[str] = Depends(require_reader_token),
):
    """Naive LIKE search across title + abstract + body. Replace with FTS
    when corpus grows."""
    if not q.strip():
        return {"papers": [], "query": q, "matched": 0}
    needle = f"%{q.strip()}%"
    rows = conn.execute(
        "SELECT * FROM papers "
        "WHERE title LIKE ? OR abstract LIKE ? OR body_md LIKE ? "
        "ORDER BY submitted_at DESC LIMIT 200",
        (needle, needle, needle),
    ).fetchall()
    return {"query": q, "matched": len(rows), "papers": [_row_to_paper(r) for r in rows]}


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("PUBLICATION_REPO_HOST", "127.0.0.1")
    port = int(os.environ.get("PUBLICATION_REPO_PORT", "9100"))
    uvicorn.run(app, host=host, port=port)

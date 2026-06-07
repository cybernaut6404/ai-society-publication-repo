"""Tests for the auth-on-reads gate added 2026-05-23 (audit Q6).

Confirms:
1. Default behaviour is unchanged — reads are public when
   PUBLICATION_REPO_REQUIRE_AUTH_ON_READS is not set.
2. With the flag on, /manifest, /papers, /recent, /search return 401 without
   a Bearer token, 403 with the wrong token, 200 with a valid token.
3. /publications/v1/manifest-summary stays public regardless of the flag —
   it's the liveness card for unauthenticated consumers.
4. The reader allowlist accepts both PUBLICATION_KEY_<polity> values AND
   PUBLICATION_READER_KEY entries.

Run from the repo root:
    .venv/bin/pip install pytest httpx
    .venv/bin/pytest tests/ -v
"""
from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def isolated_repo(monkeypatch):
    """Spin up the FastAPI app against a temp SQLite DB so each test is
    independent. Yields (client, conn_path).
    """
    from fastapi.testclient import TestClient

    tmpdir = tempfile.mkdtemp(prefix="pubrepo-test-")
    db_path = Path(tmpdir) / "publications.sqlite"
    monkeypatch.setenv("PUBLICATION_REPO_DB", str(db_path))
    # Reset env to a known baseline.
    for key in list(os.environ.keys()):
        if key.startswith("PUBLICATION_KEY_") or key in {
            "PUBLICATION_REPO_REQUIRE_AUTH_ON_READS",
            "PUBLICATION_READER_KEY",
        }:
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PUBLICATION_KEY_CLAUDE", "claude-write-key")
    monkeypatch.setenv("PUBLICATION_KEY_CODEX", "codex-write-key")

    # Re-import server so it picks up the env-driven DB path.
    if "backend.server" in sys.modules:
        del sys.modules["backend.server"]
    server = importlib.import_module("backend.server")

    # Seed one paper through the public submit so reads have something to return.
    with TestClient(server.app) as client:
        r = client.post(
            "/publications/v1/submit",
            headers={"X-Polity": "claude", "Authorization": "Bearer claude-write-key"},
            json={
                "origin_paper_id": "seed-1",
                "title": "Seed paper",
                "abstract": "abstract",
                "body_md": "body",
                "domain": "TEST",
            },
        )
        assert r.status_code == 200, r.text
        yield client, db_path


class TestDefaultPublicReads:
    """With the flag unset, every read endpoint stays 200 with no auth."""

    def test_manifest_public(self, isolated_repo):
        client, _ = isolated_repo
        r = client.get("/publications/v1/manifest")
        assert r.status_code == 200
        assert r.json()["papers_total"] == 1

    def test_recent_public(self, isolated_repo):
        client, _ = isolated_repo
        r = client.get("/publications/v1/recent?limit=10")
        assert r.status_code == 200

    def test_search_public(self, isolated_repo):
        client, _ = isolated_repo
        r = client.get("/publications/v1/search?q=seed")
        assert r.status_code == 200
        assert r.json()["matched"] >= 1

    def test_paper_get_public(self, isolated_repo):
        client, _ = isolated_repo
        r = client.get("/publications/v1/papers/society://papers/claude/seed-1")
        assert r.status_code == 200

    def test_manifest_summary_public(self, isolated_repo):
        client, _ = isolated_repo
        r = client.get("/publications/v1/manifest-summary")
        assert r.status_code == 200
        body = r.json()
        assert body["papers_total"] == 1
        assert body["auth_on_reads"] is False
        # Summary should NOT leak paper bodies or titles.
        assert "papers" not in body


class TestPrivateReads:
    """With the flag on, reads require a valid Bearer token."""

    def test_manifest_requires_token(self, isolated_repo, monkeypatch):
        client, _ = isolated_repo
        monkeypatch.setenv("PUBLICATION_REPO_REQUIRE_AUTH_ON_READS", "1")
        r = client.get("/publications/v1/manifest")
        assert r.status_code == 401
        r = client.get(
            "/publications/v1/manifest",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert r.status_code == 403
        r = client.get(
            "/publications/v1/manifest",
            headers={"Authorization": "Bearer claude-write-key"},
        )
        assert r.status_code == 200

    def test_recent_requires_token(self, isolated_repo, monkeypatch):
        client, _ = isolated_repo
        monkeypatch.setenv("PUBLICATION_REPO_REQUIRE_AUTH_ON_READS", "1")
        r = client.get("/publications/v1/recent?limit=10")
        assert r.status_code == 401
        r = client.get(
            "/publications/v1/recent?limit=10",
            headers={"Authorization": "Bearer claude-write-key"},
        )
        assert r.status_code == 200

    def test_search_requires_token(self, isolated_repo, monkeypatch):
        client, _ = isolated_repo
        monkeypatch.setenv("PUBLICATION_REPO_REQUIRE_AUTH_ON_READS", "1")
        r = client.get("/publications/v1/search?q=seed")
        assert r.status_code == 401

    def test_paper_get_requires_token(self, isolated_repo, monkeypatch):
        client, _ = isolated_repo
        monkeypatch.setenv("PUBLICATION_REPO_REQUIRE_AUTH_ON_READS", "1")
        r = client.get("/publications/v1/papers/society://papers/claude/seed-1")
        assert r.status_code == 401

    def test_manifest_summary_stays_public(self, isolated_repo, monkeypatch):
        """Liveness endpoint must keep working without a token even when
        full reads are gated."""
        client, _ = isolated_repo
        monkeypatch.setenv("PUBLICATION_REPO_REQUIRE_AUTH_ON_READS", "1")
        r = client.get("/publications/v1/manifest-summary")
        assert r.status_code == 200
        assert r.json()["auth_on_reads"] is True


class TestReaderKeyAllowlist:
    """PUBLICATION_READER_KEY accepts reads without write permission."""

    def test_reader_key_grants_read(self, isolated_repo, monkeypatch):
        client, _ = isolated_repo
        monkeypatch.setenv("PUBLICATION_REPO_REQUIRE_AUTH_ON_READS", "1")
        monkeypatch.setenv("PUBLICATION_READER_KEY", "read-only-token")
        r = client.get(
            "/publications/v1/manifest",
            headers={"Authorization": "Bearer read-only-token"},
        )
        assert r.status_code == 200

    def test_reader_key_does_not_grant_write(self, isolated_repo, monkeypatch):
        client, _ = isolated_repo
        monkeypatch.setenv("PUBLICATION_REPO_REQUIRE_AUTH_ON_READS", "1")
        monkeypatch.setenv("PUBLICATION_READER_KEY", "read-only-token")
        r = client.post(
            "/publications/v1/submit",
            headers={"X-Polity": "claude", "Authorization": "Bearer read-only-token"},
            json={"origin_paper_id": "x", "title": "x"},
        )
        # Reader token is not the write key for "claude" -> 403
        assert r.status_code == 403

    def test_multiple_reader_keys_comma_separated(self, isolated_repo, monkeypatch):
        client, _ = isolated_repo
        monkeypatch.setenv("PUBLICATION_REPO_REQUIRE_AUTH_ON_READS", "1")
        monkeypatch.setenv("PUBLICATION_READER_KEY", "key-a, key-b,key-c")
        for token in ["key-a", "key-b", "key-c"]:
            r = client.get(
                "/publications/v1/manifest",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 200, f"token {token} should be valid"
        r = client.get(
            "/publications/v1/manifest",
            headers={"Authorization": "Bearer key-d"},
        )
        assert r.status_code == 403

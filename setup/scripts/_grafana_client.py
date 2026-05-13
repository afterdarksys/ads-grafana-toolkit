"""
_grafana_client.py — Shared Grafana HTTP API client.

Used internally by backup, multi_push, annotations, dashboard_diff, and
provision_dashboards scripts. Not intended as a public-facing module.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class GrafanaError(Exception):
    """Raised when the Grafana API returns an error."""
    def __init__(self, status: int, message: str, url: str = ""):
        super().__init__(f"HTTP {status} — {message} ({url})")
        self.status = status
        self.message = message
        self.url = url


class GrafanaClient:
    """Thin wrapper around the Grafana HTTP API.

    Usage:
        client = GrafanaClient("http://localhost:3000", "admin", "admin")
        dashboards = client.get("/dashboards/home")
        client.post("/dashboards/db", {"dashboard": {...}, "overwrite": True})
    """

    def __init__(
        self,
        url: str | None = None,
        user: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
        timeout: int = 30,
        retries: int = 3,
    ):
        self.url = (url or os.environ.get("GRAFANA_URL", "http://localhost:3000")).rstrip("/")
        self.timeout = timeout
        self.retries = retries

        if api_key or os.environ.get("GRAFANA_API_KEY"):
            token = api_key or os.environ["GRAFANA_API_KEY"]
            self._auth_header = f"Bearer {token}"
        else:
            u = user or os.environ.get("GRAFANA_USER", "admin")
            p = password or os.environ.get("GRAFANA_PASSWORD", "admin")
            creds = base64.b64encode(f"{u}:{p}".encode()).decode()
            self._auth_header = f"Basic {creds}"

    # ── Core request ─────────────────────────────────────────────────────

    def request(self, method: str, path: str, body: Any = None,
                params: dict | None = None) -> Any:
        path = path if path.startswith("/api/") else f"/api{path}"
        url = self.url + path
        if params:
            url += "?" + urllib.parse.urlencode(params)

        data = json.dumps(body).encode() if body is not None else None
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self._auth_header,
        }
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        for attempt in range(self.retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read()
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                body_text = e.read().decode(errors="replace")
                try:
                    msg = json.loads(body_text).get("message", body_text)
                except Exception:
                    msg = body_text
                if e.code in (429, 502, 503, 504) and attempt < self.retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise GrafanaError(e.code, msg, url) from e
            except urllib.error.URLError as e:
                if attempt < self.retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                print(f"ERROR: Cannot reach Grafana at {self.url}: {e.reason}", file=sys.stderr)
                print("  Set GRAFANA_URL / GRAFANA_USER / GRAFANA_PASSWORD env vars.", file=sys.stderr)
                sys.exit(1)

    def get(self, path: str, params: dict | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, body: Any = None) -> Any:
        return self.request("POST", path, body=body)

    def put(self, path: str, body: Any = None) -> Any:
        return self.request("PUT", path, body=body)

    def delete(self, path: str) -> Any:
        return self.request("DELETE", path)

    # ── Convenience methods ───────────────────────────────────────────────

    def health(self) -> dict:
        return self.get("/health")

    def version(self) -> str:
        info = self.get("/frontend/settings")
        return info.get("buildInfo", {}).get("version", "unknown")

    # Dashboards

    def search_dashboards(self, query: str = "", folder_id: int | None = None,
                          limit: int = 5000) -> list[dict]:
        params: dict = {"type": "dash-db", "limit": limit}
        if query:
            params["query"] = query
        if folder_id is not None:
            params["folderIds"] = folder_id
        return self.get("/search", params=params)

    def get_dashboard(self, uid: str) -> dict:
        return self.get(f"/dashboards/uid/{uid}")

    def push_dashboard(self, dashboard: dict, folder_id: int | None = None,
                       overwrite: bool = True, message: str = "") -> dict:
        dashboard.pop("id", None)
        dashboard.pop("version", None)
        payload: dict = {
            "dashboard": dashboard,
            "overwrite": overwrite,
            "message": message or "ads-grafana-toolkit",
        }
        if folder_id is not None:
            payload["folderId"] = folder_id
        return self.post("/dashboards/db", payload)

    def delete_dashboard(self, uid: str) -> dict:
        return self.delete(f"/dashboards/uid/{uid}")

    # Folders

    def list_folders(self) -> list[dict]:
        return self.get("/folders")

    def get_or_create_folder(self, title: str) -> int | None:
        if not title or title.lower() == "general":
            return None
        for f in self.list_folders():
            if f["title"] == title:
                return f["id"]
        result = self.post("/folders", {"title": title})
        return result["id"]

    # Datasources

    def list_datasources(self) -> list[dict]:
        return self.get("/datasources")

    def get_datasource(self, name: str) -> dict | None:
        for ds in self.list_datasources():
            if ds["name"] == name:
                return ds
        return None

    def upsert_datasource(self, payload: dict) -> dict:
        existing = self.get_datasource(payload["name"])
        if existing:
            return self.put(f"/datasources/{existing['id']}", payload)
        return self.post("/datasources", payload)

    # Alert rules (Grafana unified alerting)

    def list_alert_rules(self) -> list[dict]:
        return self.get("/ruler/grafana/api/v1/rules") or []

    # Annotations

    def list_annotations(self, from_ts: int | None = None, to_ts: int | None = None,
                          limit: int = 100, tags: list[str] | None = None) -> list[dict]:
        params: dict = {"limit": limit}
        if from_ts:
            params["from"] = from_ts
        if to_ts:
            params["to"] = to_ts
        if tags:
            params["tags"] = ",".join(tags)
        return self.get("/annotations", params=params)

    def create_annotation(self, text: str, tags: list[str] | None = None,
                           time_ms: int | None = None,
                           time_end_ms: int | None = None,
                           dashboard_uid: str | None = None) -> dict:
        payload: dict = {"text": text, "tags": tags or []}
        if time_ms:
            payload["time"] = time_ms
        if time_end_ms:
            payload["timeEnd"] = time_end_ms
        if dashboard_uid:
            payload["dashboardUID"] = dashboard_uid
        return self.post("/annotations", payload)

    def delete_annotation(self, annotation_id: int) -> dict:
        return self.delete(f"/annotations/{annotation_id}")

    def update_annotation(self, annotation_id: int, text: str,
                           tags: list[str] | None = None) -> dict:
        return self.put(f"/annotations/{annotation_id}", {
            "text": text, "tags": tags or []
        })

    # Plugins

    def list_plugins(self) -> list[dict]:
        return self.get("/plugins")

    def install_plugin(self, plugin_id: str, version: str = "") -> dict:
        payload = {"pluginId": plugin_id}
        if version:
            payload["version"] = version
        return self.post("/plugins", payload)


def client_from_env() -> GrafanaClient:
    """Create a GrafanaClient from environment variables."""
    return GrafanaClient(
        url=os.environ.get("GRAFANA_URL"),
        user=os.environ.get("GRAFANA_USER"),
        password=os.environ.get("GRAFANA_PASSWORD"),
        api_key=os.environ.get("GRAFANA_API_KEY"),
    )


def client_from_instance(instance: dict) -> GrafanaClient:
    """Create a GrafanaClient from a fleet instance dict."""
    return GrafanaClient(
        url=instance.get("url"),
        user=instance.get("user"),
        password=instance.get("password"),
        api_key=instance.get("api_key"),
    )

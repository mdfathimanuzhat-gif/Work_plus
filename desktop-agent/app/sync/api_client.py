"""HTTP client for WorkPulse agent APIs. No detector logic lives here."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import AgentSettings
from app.models import AgentEvent, format_utc

logger = logging.getLogger("workpulse.agent.sync.client")


class AgentApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, body: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.body = body or {}


class AgentApiClient:
    def __init__(self, settings: AgentSettings, *, client: httpx.Client | None = None) -> None:
        if not settings.api_base_url:
            raise ValueError("API_BASE_URL is required for synchronization")
        url = settings.api_base_url
        if url.startswith("http://") and not settings.ALLOW_INSECURE_HTTP:
            raise ValueError("HTTP is only allowed when ALLOW_INSECURE_HTTP=true")
        self._settings = settings
        self._owns_client = client is None
        timeout = httpx.Timeout(settings.SYNC_REQUEST_TIMEOUT_SECONDS)
        self._client = client or httpx.Client(base_url=url, timeout=timeout)
        self._token: str | None = None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def ping(self) -> bool:
        try:
            response = self._client.get("/api/health")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def enroll(self, *, employee_access_token: str, device_identifier: str, device_name: str, operating_system: str) -> str:
        response = self._request(
            "POST",
            "/api/agent/devices/enroll",
            json={
                "device_identifier": device_identifier,
                "device_name": device_name,
                "operating_system": operating_system,
            },
            token=employee_access_token,
        )
        secret = response.get("device_secret")
        if not isinstance(secret, str) or not secret:
            raise AgentApiError(500, "invalid_response", "Enrollment did not return a device secret")
        return secret

    def login_employee(self, email: str, password: str) -> str:
        response = self._request("POST", "/api/auth/login", json={"email": email, "password": password})
        token = response.get("access_token")
        if not isinstance(token, str):
            raise AgentApiError(500, "invalid_response", "Login did not return an access token")
        return token

    def issue_device_token(self, device_identifier: str, device_secret: str) -> str:
        response = self._request(
            "POST",
            "/api/agent/auth/token",
            json={"device_identifier": device_identifier, "device_secret": device_secret},
        )
        token = response.get("access_token")
        if not isinstance(token, str):
            raise AgentApiError(500, "invalid_response", "Device auth did not return an access token")
        self._token = token
        return token

    def upload_batch(self, device_identifier: str, events: list[AgentEvent]) -> dict[str, Any]:
        if self._token is None:
            raise AgentApiError(401, "not_authenticated", "Device token is missing")
        payload = {
            "device_id": device_identifier,
            "events": [
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "event_timestamp": format_utc(event.event_timestamp),
                    "device_identifier": event.device_identifier,
                    "device_name": event.device_name,
                    "username": event.username,
                    "metadata": event.metadata,
                }
                for event in events
            ],
        }
        return self._request("POST", "/api/agent/events/batch", json=payload, token=self._token)

    def _request(self, method: str, path: str, *, json: dict | None = None, token: str | None = None) -> dict[str, Any]:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = self._client.request(method, path, json=json, headers=headers)
        except httpx.TimeoutException as exc:
            raise AgentApiError(0, "timeout", "Network timeout") from exc
        except httpx.HTTPError as exc:
            raise AgentApiError(0, "network_error", "Network error") from exc
        if response.status_code == 409:
            body = self._json_body(response)
            if isinstance(body.get("results"), list):
                return body
            raise AgentApiError(409, "duplicate", "Event already processed", body)
        if response.status_code >= 400:
            body = self._json_body(response)
            error = body.get("error") if isinstance(body, dict) else None
            code = error.get("code") if isinstance(error, dict) else "http_error"
            message = error.get("message") if isinstance(error, dict) else response.reason_phrase
            raise AgentApiError(response.status_code, str(code), str(message), body)
        if response.status_code == 204 or not response.content:
            return {}
        data = response.json()
        return data if isinstance(data, dict) else {"value": data}

    @staticmethod
    def _json_body(response: httpx.Response) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError:
            return {}
        return body if isinstance(body, dict) else {}

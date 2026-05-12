#!/usr/bin/env python3
"""Runtime quality gate for Smart Scraper.

Covers:
- ports readiness
- API config/auth behavior
- pagination enforcement and list pagination
- crash resilience (run reaches terminal state)
- core function flow (job/run/logs)

Usage:
  python3 scripts/quality_runtime_test.py
  python3 scripts/quality_runtime_test.py --base-url http://127.0.0.1:8001 --ports 8001,43102,6379
"""

from __future__ import annotations

import argparse
import asyncio
import os
import socket
import sys
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx


DEFAULT_BASE_URL = os.getenv("QUALITY_API_BASE_URL", "http://127.0.0.1:8001")
DEFAULT_API_PREFIX = os.getenv("QUALITY_API_PREFIX", "/api/v1")
DEFAULT_API_KEY = os.getenv("QUALITY_API_KEY", "dev-api-key-change-me")


@dataclass(slots=True)
class CheckResult:
    name: str
    passed: bool
    details: str


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run runtime quality tests against Smart Scraper API.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL, e.g. http://127.0.0.1:8001")
    parser.add_argument("--api-prefix", default=DEFAULT_API_PREFIX, help="API prefix, default /api/v1")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="Global API key sent in X-API-Key")
    parser.add_argument("--email", default=f"quality-{uuid.uuid4().hex[:10]}@example.com", help="Temp test user email")
    parser.add_argument("--password", default="Super-secret-123", help="Temp test user password")
    parser.add_argument("--ports", default="", help="Comma-separated ports to verify as open. Example: 8001,43102,6379")
    parser.add_argument("--run-timeout", type=int, default=120, help="Max seconds to wait for run terminal state")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Run status poll interval (seconds)")
    return parser.parse_args()


def _normalize_ports(args_ports: str, base_url: str) -> list[int]:
    ports: list[int] = []
    if args_ports.strip():
        for raw in args_ports.split(","):
            value = raw.strip()
            if not value:
                continue
            ports.append(int(value))
    else:
        parsed = urlparse(base_url)
        if parsed.port:
            ports.append(parsed.port)
    # Keep stable order and uniqueness.
    seen: set[int] = set()
    unique: list[int] = []
    for port in ports:
        if port not in seen:
            seen.add(port)
            unique.append(port)
    return unique


def _is_port_open(host: str, port: int, timeout_seconds: float = 1.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout_seconds)
        return sock.connect_ex((host, port)) == 0


async def _register_and_login(
    client: httpx.AsyncClient,
    *,
    api_prefix: str,
    email: str,
    password: str,
) -> str:
    register_resp = await client.post(
        f"{api_prefix}/auth/register",
        json={"email": email, "password": password},
    )
    if register_resp.status_code not in {201, 409}:
        raise RuntimeError(
            f"Register failed: HTTP {register_resp.status_code} -> {register_resp.text}"
        )

    login_resp = await client.post(
        f"{api_prefix}/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if login_resp.status_code != 200:
        raise RuntimeError(
            f"Login failed: HTTP {login_resp.status_code} -> {login_resp.text}"
        )
    return login_resp.json()["access_token"]


async def _create_job(
    client: httpx.AsyncClient,
    *,
    api_prefix: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    expected_status: int = 201,
) -> dict[str, Any]:
    response = await client.post(f"{api_prefix}/jobs", headers=headers, json=payload)
    if response.status_code != expected_status:
        raise RuntimeError(
            f"Create job failed: HTTP {response.status_code} -> {response.text}"
        )
    return response.json()


async def _create_run(
    client: httpx.AsyncClient,
    *,
    api_prefix: str,
    headers: dict[str, str],
    job_id: str,
) -> str:
    response = await client.post(f"{api_prefix}/jobs/{job_id}/runs", headers=headers)
    if response.status_code != 201:
        raise RuntimeError(
            f"Create run failed for job {job_id}: HTTP {response.status_code} -> {response.text}"
        )
    return response.json()["id"]


async def _poll_run_terminal(
    client: httpx.AsyncClient,
    *,
    api_prefix: str,
    headers: dict[str, str],
    run_id: str,
    timeout_seconds: int,
    poll_interval: float,
) -> dict[str, Any]:
    started = asyncio.get_running_loop().time()
    while True:
        response = await client.get(f"{api_prefix}/runs/{run_id}", headers=headers)
        if response.status_code != 200:
            raise RuntimeError(
                f"Run status check failed for {run_id}: HTTP {response.status_code} -> {response.text}"
            )
        payload = response.json()
        status_value = str(payload.get("status", "")).lower()
        if status_value in {"completed", "failed", "cancelled"}:
            return payload

        elapsed = asyncio.get_running_loop().time() - started
        if elapsed > timeout_seconds:
            raise RuntimeError(
                f"Run {run_id} did not reach terminal state within {timeout_seconds}s; last status={status_value}"
            )

        await asyncio.sleep(poll_interval)


async def _check_ports(base_url: str, ports: list[int]) -> CheckResult:
    if not ports:
        return CheckResult("ports", True, "No explicit ports requested; backend port check skipped.")

    host = urlparse(base_url).hostname or "127.0.0.1"
    closed = [str(port) for port in ports if not _is_port_open(host, port)]
    if closed:
        return CheckResult("ports", False, f"Closed/unreachable ports on {host}: {', '.join(closed)}")
    return CheckResult("ports", True, f"All requested ports are open on {host}: {', '.join(map(str, ports))}")


async def _check_api_config(client: httpx.AsyncClient, api_prefix: str, api_key: str) -> CheckResult:
    health_resp = await client.get("/health")
    if health_resp.status_code != 200:
        return CheckResult("api_config", False, f"/health returned HTTP {health_resp.status_code}")
    health_json = health_resp.json()
    if "services" not in health_json:
        return CheckResult("api_config", False, "Health payload missing services key")

    scrape_payload = {
        "query": "hospitals",
        "location": "Saudi Arabia",
        "limit": 10,
        "fields": ["name", "contact"],
    }

    missing_key_resp = await client.post(f"{api_prefix}/scrape", json=scrape_payload)
    if missing_key_resp.status_code != 401:
        return CheckResult(
            "api_config",
            False,
            f"Expected scrape without API key to return 401; got {missing_key_resp.status_code}",
        )

    invalid_key_resp = await client.post(
        f"{api_prefix}/scrape",
        headers={"X-API-Key": "invalid-quality-key"},
        json=scrape_payload,
    )
    if invalid_key_resp.status_code != 403:
        return CheckResult(
            "api_config",
            False,
            f"Expected scrape with invalid key to return 403; got {invalid_key_resp.status_code}",
        )

    valid_key_resp = await client.post(
        f"{api_prefix}/scrape",
        headers={"X-API-Key": api_key},
        json=scrape_payload,
    )
    if valid_key_resp.status_code != 200:
        return CheckResult(
            "api_config",
            False,
            f"Expected scrape with valid key to return 200; got {valid_key_resp.status_code}",
        )

    return CheckResult("api_config", True, "Health + API key protection behavior verified.")


async def _check_pagination(
    client: httpx.AsyncClient,
    *,
    api_prefix: str,
    auth_headers: dict[str, str],
) -> CheckResult:
    reject_resp = await client.post(
        f"{api_prefix}/jobs",
        headers=auth_headers,
        json={
            "url": "https://example.com/patients",
            "scrape_type": "general",
            "prompt": "Collect all pages and all records",
            "max_pages": 10,
            "follow_pagination": False,
        },
    )
    if reject_resp.status_code != 422:
        return CheckResult(
            "pagination",
            False,
            f"Expected full-coverage + pagination=false to fail with 422; got {reject_resp.status_code}",
        )

    force_resp = await client.post(
        f"{api_prefix}/jobs",
        headers=auth_headers,
        json={
            "url": "https://example.com/patients",
            "scrape_type": "general",
            "prompt": "Collect patient names",
            "max_pages": 10,
            "follow_pagination": False,
            "config": {"max_records": 200},
        },
    )
    if force_resp.status_code != 201:
        return CheckResult("pagination", False, f"Forced-pagination job create failed: HTTP {force_resp.status_code}")

    forced_job = force_resp.json()
    if forced_job.get("follow_pagination") is not True:
        return CheckResult("pagination", False, "Expected follow_pagination=true for high max_records request")
    if int(forced_job.get("max_pages", 0)) < 11:
        return CheckResult("pagination", False, "Expected auto-increased max_pages for high max_records request")

    created_ids: list[str] = []
    for idx in range(3):
        body = await _create_job(
            client,
            api_prefix=api_prefix,
            headers=auth_headers,
            payload={
                "url": f"https://example.com/list-{idx}",
                "scrape_type": "general",
                "prompt": "List extraction",
                "max_pages": 2,
                "follow_pagination": True,
            },
        )
        created_ids.append(body["id"])

    list_one = await client.get(f"{api_prefix}/jobs", headers=auth_headers, params={"skip": 0, "limit": 2})
    list_two = await client.get(f"{api_prefix}/jobs", headers=auth_headers, params={"skip": 2, "limit": 2})
    if list_one.status_code != 200 or list_two.status_code != 200:
        return CheckResult("pagination", False, "Failed to list jobs with skip/limit pagination")

    jobs_one = list_one.json().get("jobs", [])
    jobs_two = list_two.json().get("jobs", [])
    if len(jobs_one) == 0:
        return CheckResult("pagination", False, "First jobs page is empty unexpectedly")

    ids_one = {item.get("id") for item in jobs_one}
    ids_two = {item.get("id") for item in jobs_two}
    overlap = ids_one & ids_two
    if overlap:
        return CheckResult("pagination", False, f"Pagination overlap detected across pages: {sorted(overlap)}")

    return CheckResult("pagination", True, "Prompt enforcement + auto-pagination + skip/limit paging verified.")


async def _check_crash_resilience(
    client: httpx.AsyncClient,
    *,
    api_prefix: str,
    auth_headers: dict[str, str],
    run_timeout: int,
    poll_interval: float,
) -> CheckResult:
    try:
        job = await _create_job(
            client,
            api_prefix=api_prefix,
            headers=auth_headers,
            payload={
                "url": "https://example.com",
                "scrape_type": "general",
                "prompt": "Extract title and links if available.",
                "max_pages": 1,
                "follow_pagination": False,
                "config": {
                    "timeout_ms": 8_000,
                    "wait_for_selector": "table.nonexistent-quality-selector",
                    "wait_for_selector_timeout_ms": 1_000,
                    "wait_until": "domcontentloaded",
                },
            },
        )
        run_id = await _create_run(client, api_prefix=api_prefix, headers=auth_headers, job_id=job["id"])
        terminal = await _poll_run_terminal(
            client,
            api_prefix=api_prefix,
            headers=auth_headers,
            run_id=run_id,
            timeout_seconds=run_timeout,
            poll_interval=poll_interval,
        )
    except Exception as exc:
        return CheckResult("crashing", False, str(exc))

    return CheckResult(
        "crashing",
        True,
        f"Run reached terminal status={terminal.get('status')} without hanging.",
    )


async def _check_core_function(
    client: httpx.AsyncClient,
    *,
    api_prefix: str,
    auth_headers: dict[str, str],
    run_timeout: int,
    poll_interval: float,
) -> CheckResult:
    try:
        job = await _create_job(
            client,
            api_prefix=api_prefix,
            headers=auth_headers,
            payload={
                "url": "https://example.com",
                "scrape_type": "general",
                "prompt": "Extract visible text and links.",
                "max_pages": 1,
                "follow_pagination": False,
            },
        )
        run_id = await _create_run(client, api_prefix=api_prefix, headers=auth_headers, job_id=job["id"])
        terminal = await _poll_run_terminal(
            client,
            api_prefix=api_prefix,
            headers=auth_headers,
            run_id=run_id,
            timeout_seconds=run_timeout,
            poll_interval=poll_interval,
        )

        logs_resp = await client.get(f"{api_prefix}/runs/{run_id}/logs", headers=auth_headers)
        if logs_resp.status_code != 200:
            return CheckResult(
                "function",
                False,
                f"Run finished but logs endpoint failed: HTTP {logs_resp.status_code}",
            )
    except Exception as exc:
        return CheckResult("function", False, str(exc))

    return CheckResult(
        "function",
        True,
        f"Job/run flow completed with terminal status={terminal.get('status')} and logs accessible.",
    )


def _print_result(result: CheckResult) -> None:
    prefix = "PASS" if result.passed else "FAIL"
    print(f"[{prefix}] {result.name}: {result.details}")


async def _async_main(args: argparse.Namespace) -> int:
    api_prefix = args.api_prefix.rstrip("/")
    timeout = httpx.Timeout(connect=10.0, read=90.0, write=30.0, pool=30.0)
    base_url = args.base_url.rstrip("/")
    ports = _normalize_ports(args.ports, base_url)

    results: list[CheckResult] = []

    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        results.append(await _check_ports(base_url, ports))

        api_config_result = await _check_api_config(client, api_prefix, args.api_key)
        results.append(api_config_result)
        if not api_config_result.passed:
            for result in results:
                _print_result(result)
            return 1

        token = await _register_and_login(
            client,
            api_prefix=api_prefix,
            email=args.email,
            password=args.password,
        )
        auth_headers = {
            "Authorization": f"Bearer {token}",
            "X-API-Key": args.api_key,
        }

        results.append(await _check_pagination(client, api_prefix=api_prefix, auth_headers=auth_headers))
        results.append(
            await _check_crash_resilience(
                client,
                api_prefix=api_prefix,
                auth_headers=auth_headers,
                run_timeout=args.run_timeout,
                poll_interval=args.poll_interval,
            )
        )
        results.append(
            await _check_core_function(
                client,
                api_prefix=api_prefix,
                auth_headers=auth_headers,
                run_timeout=args.run_timeout,
                poll_interval=args.poll_interval,
            )
        )

    print("\n=== Runtime Quality Test Summary ===")
    for result in results:
        _print_result(result)

    failed = [result for result in results if not result.passed]
    if failed:
        print(f"\nQuality gate FAILED ({len(failed)} checks failed).")
        return 1

    print("\nQuality gate PASSED.")
    return 0


def main() -> int:
    args = _parse_args()
    try:
        return asyncio.run(_async_main(args))
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    except Exception as exc:
        print(f"\nQuality test failed with unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Dispatch chaos scraping jobs against a local Smart Scraper API.

Usage:
    python3 scripts/chaos_test.py
    python3 scripts/chaos_test.py --base-url http://127.0.0.1:8002 --run-timeout 240
"""

from __future__ import annotations

import argparse
import asyncio
import os
import uuid
from dataclasses import dataclass
from typing import Any

import httpx


DEFAULT_BASE_URL = os.getenv("CHAOS_API_BASE_URL", "http://127.0.0.1:8002")
DEFAULT_API_PREFIX = os.getenv("CHAOS_API_PREFIX", "/api/v1")


@dataclass(slots=True)
class ChaosCase:
    name: str
    url: str
    prompt: str
    max_pages: int
    follow_pagination: bool
    config: dict[str, Any]
    expectation: str


CHAOS_CASES: list[ChaosCase] = [
    ChaosCase(
        name="Infinite Timeout Trap",
        url="https://httpstat.us/200?sleep=60000",
        prompt="Attempt extraction but fail safely if the page hangs.",
        max_pages=1,
        follow_pagination=False,
        config={
            "timeout_ms": 10_000,
            "wait_until": "networkidle",
            "post_navigation_wait_until": "networkidle",
            "wait_for_selector_timeout_ms": 2_000,
        },
        expectation="Run should fail by timeout, not hang forever.",
    ),
    ChaosCase(
        name="Hard Block / Captcha",
        url="https://nowsecure.nl",
        prompt="Extract visible page metadata if possible; fail cleanly if blocked.",
        max_pages=1,
        follow_pagination=False,
        config={
            "timeout_ms": 20_000,
            "wait_until": "domcontentloaded",
            "post_navigation_wait_until": "networkidle",
        },
        expectation="Run should complete with limited data or fail with a clean error.",
    ),
    ChaosCase(
        name="Empty/Garbage DOM",
        url="https://httpbin.org/json",
        prompt="Extract title, links, and any records if present.",
        max_pages=1,
        follow_pagination=False,
        config={
            "timeout_ms": 10_000,
            "wait_until": "domcontentloaded",
            "wait_for_selector": "table.nonexistent-chaos-selector",
            "wait_for_selector_timeout_ms": 1_500,
        },
        expectation="Run should not crash on missing selectors/non-HTML-like content.",
    ),
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run chaos scraping jobs against local API.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL, e.g. http://127.0.0.1:8002")
    parser.add_argument("--api-prefix", default=DEFAULT_API_PREFIX, help="API prefix, default /api/v1")
    parser.add_argument("--email", default=f"chaos-{uuid.uuid4().hex[:10]}@example.com", help="Auth email")
    parser.add_argument("--password", default="super-secret-123", help="Auth password")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Run status poll interval (seconds)")
    parser.add_argument("--run-timeout", type=int, default=240, help="Max wait per run (seconds)")
    return parser.parse_args()


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
    case: ChaosCase,
) -> str:
    payload = {
        "url": case.url,
        "scrape_type": "general",
        "prompt": case.prompt,
        "max_pages": case.max_pages,
        "follow_pagination": case.follow_pagination,
        "config": case.config,
    }
    response = await client.post(f"{api_prefix}/jobs", headers=headers, json=payload)
    if response.status_code != 201:
        raise RuntimeError(
            f"[{case.name}] Job creation failed: HTTP {response.status_code} -> {response.text}"
        )
    return response.json()["id"]


async def _start_run(
    client: httpx.AsyncClient,
    *,
    api_prefix: str,
    headers: dict[str, str],
    case_name: str,
    job_id: str,
) -> str:
    response = await client.post(f"{api_prefix}/jobs/{job_id}/runs", headers=headers)
    if response.status_code != 201:
        raise RuntimeError(
            f"[{case_name}] Run start failed: HTTP {response.status_code} -> {response.text}"
        )
    return response.json()["id"]


async def _poll_run_status(
    client: httpx.AsyncClient,
    *,
    api_prefix: str,
    headers: dict[str, str],
    run_id: str,
    poll_interval: float,
    timeout_seconds: int,
) -> dict[str, Any]:
    started = asyncio.get_running_loop().time()
    while True:
        response = await client.get(f"{api_prefix}/runs/{run_id}", headers=headers)
        if response.status_code != 200:
            raise RuntimeError(
                f"Run status check failed for {run_id}: "
                f"HTTP {response.status_code} -> {response.text}"
            )
        run_payload = response.json()
        status = str(run_payload.get("status", "")).lower()
        if status in {"completed", "failed"}:
            return run_payload

        elapsed = asyncio.get_running_loop().time() - started
        if elapsed > timeout_seconds:
            return {
                "id": run_id,
                "status": "timeout_waiting_for_terminal_state",
                "error_message": f"Run did not reach completed/failed within {timeout_seconds}s",
            }
        await asyncio.sleep(poll_interval)


async def _fetch_run_logs(
    client: httpx.AsyncClient,
    *,
    api_prefix: str,
    headers: dict[str, str],
    run_id: str,
) -> list[dict[str, Any]]:
    response = await client.get(f"{api_prefix}/runs/{run_id}/logs", headers=headers)
    if response.status_code != 200:
        return [
            {
                "event": "logs_unavailable",
                "message": f"HTTP {response.status_code}: {response.text}",
            }
        ]
    return response.json().get("logs", [])


async def _run_case(
    client: httpx.AsyncClient,
    *,
    api_prefix: str,
    headers: dict[str, str],
    case: ChaosCase,
    poll_interval: float,
    run_timeout: int,
) -> dict[str, Any]:
    job_id = await _create_job(client, api_prefix=api_prefix, headers=headers, case=case)
    run_id = await _start_run(client, api_prefix=api_prefix, headers=headers, case_name=case.name, job_id=job_id)
    run_result = await _poll_run_status(
        client,
        api_prefix=api_prefix,
        headers=headers,
        run_id=run_id,
        poll_interval=poll_interval,
        timeout_seconds=run_timeout,
    )
    logs = await _fetch_run_logs(client, api_prefix=api_prefix, headers=headers, run_id=run_id)
    tail_logs = logs[-6:] if logs else []
    return {
        "case": case.name,
        "url": case.url,
        "expectation": case.expectation,
        "job_id": job_id,
        "run_id": run_id,
        "status": run_result.get("status"),
        "progress": run_result.get("progress"),
        "error_message": run_result.get("error_message") or run_result.get("error"),
        "tail_logs": tail_logs,
    }


def _print_result(result: dict[str, Any]) -> None:
    print("\n" + "=" * 88)
    print(f"Case:        {result['case']}")
    print(f"URL:         {result['url']}")
    print(f"Expectation: {result['expectation']}")
    print(f"Job ID:      {result['job_id']}")
    print(f"Run ID:      {result['run_id']}")
    print(f"Status:      {result['status']}")
    print(f"Progress:    {result.get('progress')}")
    print(f"Error:       {result.get('error_message')}")
    print("Run Log Tail:")
    if not result["tail_logs"]:
        print("  (no logs returned)")
        return
    for entry in result["tail_logs"]:
        event = entry.get("event", "unknown_event")
        level = entry.get("level", "info")
        msg = entry.get("message", "")
        print(f"  - [{level}] {event}: {msg}")


async def _async_main(args: argparse.Namespace) -> int:
    timeout = httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=30.0)
    async with httpx.AsyncClient(base_url=args.base_url.rstrip("/"), timeout=timeout) as client:
        token = await _register_and_login(
            client,
            api_prefix=args.api_prefix.rstrip("/"),
            email=args.email,
            password=args.password,
        )
        headers = {"Authorization": f"Bearer {token}"}
        print(f"Authenticated as {args.email}")
        print(f"Target API: {args.base_url.rstrip('/')}{args.api_prefix.rstrip('/')}")

        results = []
        for case in CHAOS_CASES:
            print(f"\nDispatching: {case.name}")
            result = await _run_case(
                client,
                api_prefix=args.api_prefix.rstrip("/"),
                headers=headers,
                case=case,
                poll_interval=args.poll_interval,
                run_timeout=args.run_timeout,
            )
            results.append(result)
            _print_result(result)

    print("\n" + "=" * 88)
    print("Chaos test finished.")
    print("Summary:")
    for result in results:
        print(f"  - {result['case']}: {result['status']} (run_id={result['run_id']})")
    return 0


def main() -> int:
    args = _parse_args()
    try:
        return asyncio.run(_async_main(args))
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    except Exception as exc:
        print(f"\nChaos test failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# OpenSandbox debug CLI

from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any, Iterable

import httpx


def _base_url() -> str:
    return (
        os.environ.get("OPEN_SANDBOX_DOMAIN")
        or os.environ.get("OPENSANDBOX_SERVER_URL")
        or os.environ.get("OPEN_SANDBOX_URL")
        or "http://localhost:8080"
    ).rstrip("/")


def _api_key() -> str | None:
    return (
        os.environ.get("OPEN_SANDBOX_API_KEY")
        or os.environ.get("OPENSANDBOX_API_KEY")
        or os.environ.get("SANDBOX_API_KEY")
    )


def _headers(args: argparse.Namespace) -> dict[str, str]:
    headers = {"accept": "application/json", "content-type": "application/json"}
    if args.trace_id:
        headers["X-Request-ID"] = args.trace_id
    key = _api_key()
    if key:
        headers["OPEN-SANDBOX-API-KEY"] = key
    return headers


async def _request(
    method: str, path: str, *, args: argparse.Namespace, json_body: dict[str, Any] | None = None
) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method,
            f"{_base_url()}{path}",
            headers=_headers(args),
            json=json_body,
            timeout=args.timeout,
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return {"status": response.status_code, "body": response.text}


def _print(payload: Any) -> None:
    if isinstance(payload, str):
        print(payload)
        return
    print(json.dumps(payload, indent=2, sort_keys=True))


async def cmd_health(args: argparse.Namespace) -> None:
    payload = await _request("GET", "/health", args=args)
    _print(payload)


async def cmd_openapi(args: argparse.Namespace) -> None:
    payload = await _request("GET", "/openapi.json", args=args)
    _print(payload)


async def cmd_list(args: argparse.Namespace) -> None:
    payload = await _request("GET", "/v1/sandboxes", args=args)
    _print(payload)


async def cmd_get(args: argparse.Namespace) -> None:
    payload = await _request("GET", f"/v1/sandboxes/{args.sandbox_id}", args=args)
    _print(payload)


async def cmd_endpoint(args: argparse.Namespace) -> None:
    payload = await _request(
        "GET",
        f"/v1/sandboxes/{args.sandbox_id}/endpoints/{args.port}",
        args=args,
    )
    _print(payload)


async def cmd_diagnostics(args: argparse.Namespace) -> None:
    scopes: Iterable[str] = args.scopes
    result: dict[str, Any] = {}
    for scope in scopes:
        result[scope] = await _request(
            "GET",
            f"/v1/sandboxes/{args.sandbox_id}/diagnostics/{scope}",
            args=args,
        )
    _print(result)


def _build_create_payload(args: argparse.Namespace) -> dict[str, Any]:
    resource_limits: dict[str, str] = {}
    if args.cpu:
        resource_limits["cpu"] = args.cpu
    if args.memory:
        resource_limits["memory"] = args.memory
    payload: dict[str, Any] = {
        "image": {
            "uri": args.image,
        },
        "entrypoint": args.entrypoint,
        "resourceLimits": resource_limits or {"cpu": "1", "memory": "2Gi"},
    }
    if args.timeout:
        payload["timeout"] = args.timeout
    return payload


async def cmd_create(args: argparse.Namespace) -> str:
    payload = _build_create_payload(args)
    _print(payload)
    response = await _request(
        "POST",
        "/v1/sandboxes",
        args=args,
        json_body=payload,
    )
    _print(response)
    sandbox_id = response.get("sandboxId") or response.get("id")
    if isinstance(sandbox_id, str):
        return sandbox_id
    return ""


async def cmd_delete(args: argparse.Namespace) -> None:
    payload = await _request("DELETE", f"/v1/sandboxes/{args.sandbox_id}", args=args)
    _print(payload)


async def cmd_smoke(args: argparse.Namespace) -> None:
    sandbox_id = await cmd_create(args)
    if not sandbox_id:
        raise RuntimeError("No sandbox_id returned from create call")

    try:
        _print({"sandbox_id": sandbox_id})
        # Keep this lightweight and non-blocking: status probe once for now.
        status = await _request("GET", f"/v1/sandboxes/{sandbox_id}", args=args)
        _print({"status": status})
        if args.port:
            endpoint = await _request(
                "GET",
                f"/v1/sandboxes/{sandbox_id}/endpoints/{args.port}",
                args=args,
            )
            _print({"endpoint": endpoint})
    finally:
        await cmd_delete(
            argparse.Namespace(
                sandbox_id=sandbox_id,
                trace_id=args.trace_id,
                timeout=args.timeout,
            )
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenSandbox CLI diagnostics helper")
    parser.add_argument("--trace-id", default=None, help="X-Request-ID for tracing")
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="HTTP timeout in seconds",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health").set_defaults(func=cmd_health)
    sub.add_parser("openapi").set_defaults(func=cmd_openapi)
    sub.add_parser("list").set_defaults(func=cmd_list)

    cmd = sub.add_parser("get")
    cmd.add_argument("sandbox_id")
    cmd.set_defaults(func=cmd_get)

    cmd = sub.add_parser("endpoint")
    cmd.add_argument("sandbox_id")
    cmd.add_argument("port", type=int)
    cmd.set_defaults(func=cmd_endpoint)

    cmd = sub.add_parser("diagnostics")
    cmd.add_argument("sandbox_id")
    cmd.add_argument(
        "--scope",
        dest="scopes",
        default=["logs", "events"],
        nargs="+",
        help='Diagnostics scope(s), e.g. logs, events, lifecycle',
    )
    cmd.set_defaults(func=cmd_diagnostics)

    cmd = sub.add_parser("delete")
    cmd.add_argument("sandbox_id")
    cmd.set_defaults(func=cmd_delete)

    cmd = sub.add_parser("create")
    cmd.add_argument("--image", default=os.environ.get("SANDBOX_CODE_IMAGE"))
    cmd.add_argument(
        "--entrypoint",
        nargs="+",
        default=["/opt/opensandbox/code-interpreter.sh"],
        help="Entrypoint command for sandbox",
    )
    cmd.add_argument("--cpu", default="1")
    cmd.add_argument("--memory", default="2Gi")
    cmd.add_argument("--timeout", type=int, default=600)
    cmd.set_defaults(func=cmd_create)

    cmd = sub.add_parser("smoke")
    cmd.add_argument("--image", default=os.environ.get("SANDBOX_CODE_IMAGE"))
    cmd.add_argument(
        "--entrypoint",
        nargs="+",
        default=["/opt/opensandbox/code-interpreter.sh"],
        help="Entrypoint command for sandbox",
    )
    cmd.add_argument("--cpu", default="1")
    cmd.add_argument("--memory", default="2Gi")
    cmd.add_argument("--timeout", type=int, default=600)
    cmd.add_argument("--port", type=int, default=None)
    cmd.set_defaults(func=cmd_smoke)

    return parser


async def _main_async(args: argparse.Namespace) -> None:
    if getattr(args, "func", None) in (cmd_create, cmd_smoke) and not args.image:
        raise RuntimeError(
            "Image is required; set --image or SANDBOX_CODE_IMAGE env var."
        )
    await args.func(args)


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    try:
        asyncio.run(_main_async(args))
        return 0
    except httpx.HTTPStatusError as exc:
        response = exc.response
        print(f"HTTP {response.status_code}: {response.text}")
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Provider-agnostic MCP catalog policy.

External MCP descriptors are untrusted input. This module keeps discovery,
descriptor snapshots, risk classification and token policy separate from
execution so Control UI and Meta-Harness can inspect the effective catalog
without invoking a server.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlparse

ApprovalLevel = Literal["auto", "confirm", "destructive", "admin", "blocked"]
Transport = Literal["stdio", "streamable-http", "sse", "http"]

_SAFE_NAME_RE = re.compile(r"[^a-z0-9_]+")
_PROMPT_INJECTION_PATTERNS = (
    re.compile(r"ignore (?:all )?(?:previous|prior|above) instructions", re.I),
    re.compile(r"system prompt", re.I),
    re.compile(r"developer message", re.I),
    re.compile(r"exfiltrat(?:e|ion)", re.I),
    re.compile(r"send .*token", re.I),
    re.compile(r"secret(?:s)?", re.I),
)
_DESTRUCTIVE_PATTERNS = (
    re.compile(r"\bdelete\b", re.I),
    re.compile(r"\bdrop\b", re.I),
    re.compile(r"\btruncate\b", re.I),
    re.compile(r"\boverwrite\b", re.I),
    re.compile(r"rm\s+-rf", re.I),
)
_ADMIN_PATTERNS = (
    re.compile(r"\badmin\b", re.I),
    re.compile(r"\broot\b", re.I),
    re.compile(r"\bimpersonat(?:e|ion)\b", re.I),
)


@dataclass(frozen=True)
class McpServerConfig:
    server_id: str
    transport: Transport
    command: str | None = None
    url: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    credential_scopes: tuple[str, ...] = ()
    tenant_allowlist: tuple[str, ...] = ()
    user_allowlist: tuple[str, ...] = ()
    denylisted_server_ids: tuple[str, ...] = ()
    denylisted_tool_names: tuple[str, ...] = ()
    denylisted_domains: tuple[str, ...] = ()
    denylisted_resource_uris: tuple[str, ...] = ()
    enabled: bool = False
    allow_token_passthrough: bool = False


@dataclass(frozen=True)
class McpToolDescriptorSnapshot:
    server_id: str
    original_name: str
    matrix_name: str
    descriptor_hash: str
    first_seen: str
    last_seen: str
    description: str = ""
    input_schema_hash: str = ""
    output_template_hash: str = ""
    security_schemes: tuple[str, ...] = ()
    resource_uris: tuple[str, ...] = ()
    risk_flags: tuple[str, ...] = ()
    approval_level: ApprovalLevel = "auto"
    enabled: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class McpCatalogEntry:
    server: McpServerConfig
    snapshot: McpToolDescriptorSnapshot
    visible: bool
    denial_reasons: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "server": {
                key: value for key, value in asdict(self.server).items() if key != "env"
            },
            "tool": self.snapshot.as_dict(),
            "visible": self.visible,
            "denial_reasons": list(self.denial_reasons),
            "secrets_redacted": True,
        }
        payload["server"]["env_keys"] = sorted(self.server.env)
        return payload


def normalize_tool_name(server_id: str, tool_name: str) -> str:
    """Return a Matrix-safe, server-qualified MCP tool name."""

    server = _slug(server_id) or "mcp"
    tool = _slug(tool_name) or "tool"
    return f"mcp_{server}__{tool}"


def snapshot_descriptor(
    server: McpServerConfig,
    descriptor: dict[str, Any],
    *,
    now: datetime | None = None,
    first_seen: str | None = None,
) -> McpToolDescriptorSnapshot:
    """Normalize and hash one MCP tool descriptor without trusting it."""

    timestamp = (now or datetime.now(UTC)).isoformat()
    original_name = str(descriptor.get("name") or "")
    matrix_name = normalize_tool_name(server.server_id, original_name)
    description = str(descriptor.get("description") or "")
    security_schemes = _security_scheme_names(descriptor)
    risk_flags = tuple(
        sorted(
            _descriptor_risk_flags(
                descriptor,
                server=server,
                matrix_name=matrix_name,
            )
        )
    )
    return McpToolDescriptorSnapshot(
        server_id=server.server_id,
        original_name=original_name,
        matrix_name=matrix_name,
        descriptor_hash=_stable_hash(descriptor),
        first_seen=first_seen or timestamp,
        last_seen=timestamp,
        description=description,
        input_schema_hash=_stable_hash(_input_schema(descriptor)),
        output_template_hash=_stable_hash(descriptor.get("_meta", {})),
        security_schemes=security_schemes,
        resource_uris=_descriptor_resource_uris_from_meta(
            descriptor.get("_meta") if isinstance(descriptor.get("_meta"), dict) else {}
        ),
        risk_flags=risk_flags,
        approval_level=_approval_level(risk_flags),
        enabled=server.enabled and "blocked_descriptor" not in risk_flags,
    )


def build_effective_catalog(
    server: McpServerConfig,
    descriptors: list[dict[str, Any]],
    *,
    tenant_id: str = "",
    user_id: str = "",
) -> list[McpCatalogEntry]:
    """Return policy-filtered catalog entries without executing tools."""

    catalog: list[McpCatalogEntry] = []
    seen_names: set[str] = set()
    duplicate_names: set[str] = set()
    snapshots = [snapshot_descriptor(server, descriptor) for descriptor in descriptors]
    for snapshot in snapshots:
        if snapshot.matrix_name in seen_names:
            duplicate_names.add(snapshot.matrix_name)
        seen_names.add(snapshot.matrix_name)

    for snapshot in snapshots:
        reasons: list[str] = []
        if not server.enabled:
            reasons.append("server-disabled")
        if server.server_id in server.denylisted_server_ids:
            reasons.append("server-denylisted")
        if server.tenant_allowlist and tenant_id not in server.tenant_allowlist:
            reasons.append("tenant-not-allowed")
        if server.user_allowlist and user_id not in server.user_allowlist:
            reasons.append("user-not-allowed")
        if (
            snapshot.original_name in server.denylisted_tool_names
            or snapshot.matrix_name in server.denylisted_tool_names
        ):
            reasons.append("tool-denylisted")
        if _domain(server.url) in server.denylisted_domains:
            reasons.append("domain-denylisted")
        if any(
            _resource_uri_denied(uri, server.denylisted_resource_uris)
            for uri in _descriptor_resource_uris(snapshot)
        ):
            reasons.append("resource-uri-denylisted")
        if snapshot.matrix_name in duplicate_names:
            reasons.append("tool-name-collision")
        if "prompt_injection" in snapshot.risk_flags:
            reasons.append("descriptor-prompt-injection")
        if "token_passthrough_requested" in snapshot.risk_flags:
            reasons.append("token-passthrough-denied")
        if "blocked_descriptor" in snapshot.risk_flags:
            reasons.append("descriptor-blocked")
        catalog.append(
            McpCatalogEntry(
                server=server,
                snapshot=snapshot,
                visible=not reasons,
                denial_reasons=tuple(reasons),
            )
        )
    return catalog


def diff_descriptor_snapshots(
    previous: McpToolDescriptorSnapshot,
    current: McpToolDescriptorSnapshot,
) -> dict[str, Any]:
    """Classify descriptor drift between two snapshots."""

    changed_fields = []
    if previous.original_name != current.original_name:
        changed_fields.append("name")
    if previous.description != current.description:
        changed_fields.append("description")
    if previous.input_schema_hash != current.input_schema_hash:
        changed_fields.append("input_schema")
    if previous.output_template_hash != current.output_template_hash:
        changed_fields.append("output_template")
    if previous.security_schemes != current.security_schemes:
        changed_fields.append("security_schemes")
    previous_risk = set(previous.risk_flags)
    current_risk = set(current.risk_flags)
    added_risk = sorted(current_risk - previous_risk)
    return {
        "changed": bool(changed_fields or added_risk),
        "changed_fields": changed_fields,
        "added_risk_flags": added_risk,
        "risk_escalated": bool(added_risk)
        or _approval_rank(current.approval_level)
        > _approval_rank(previous.approval_level),
        "requires_reapproval": bool(changed_fields or added_risk),
    }


def evaluate_token_passthrough(
    server: McpServerConfig,
    *,
    requested_scope: str | None,
) -> dict[str, Any]:
    """Fail closed unless passthrough and a named credential scope are allowed."""

    if not requested_scope:
        return {"allowed": False, "reason": "missing-credential-scope"}
    if not server.allow_token_passthrough:
        return {"allowed": False, "reason": "token-passthrough-disabled"}
    if requested_scope not in server.credential_scopes:
        return {"allowed": False, "reason": "credential-scope-not-allowed"}
    return {"allowed": True, "reason": "credential-scope-allowed"}


def evaluate_tool_invocation_policy(
    snapshot: McpToolDescriptorSnapshot,
    *,
    approval_channel_available: bool,
    approval_granted: bool = False,
) -> dict[str, Any]:
    """Fail closed when non-auto MCP tools cannot receive human approval."""

    if snapshot.approval_level == "blocked" or not snapshot.enabled:
        return {"allowed": False, "reason": "tool-blocked"}
    if snapshot.approval_level == "auto":
        return {"allowed": True, "reason": "auto-approved"}
    if not approval_channel_available:
        return {"allowed": False, "reason": "approval-channel-unavailable"}
    if not approval_granted:
        return {
            "allowed": False,
            "reason": f"approval-required:{snapshot.approval_level}",
        }
    return {"allowed": True, "reason": f"approved:{snapshot.approval_level}"}


def evaluate_resource_fetch_policy(
    server: McpServerConfig,
    *,
    resource_uri: str,
    purpose: str = "resource",
) -> dict[str, Any]:
    """Evaluate MCP resource fetch separately from tool execution."""

    uri = str(resource_uri or "").strip()
    if not uri:
        return {"allowed": False, "reason": "missing-resource-uri"}
    parsed = urlparse(uri)
    if parsed.scheme not in {"https", "http", "mcp", "matrix", "file"}:
        return {"allowed": False, "reason": "resource-scheme-not-allowed"}
    if parsed.scheme == "file":
        return {"allowed": False, "reason": "file-resource-fetch-denied"}
    if _domain(uri) in server.denylisted_domains:
        return {"allowed": False, "reason": "domain-denylisted"}
    if _resource_uri_denied(uri, server.denylisted_resource_uris):
        return {"allowed": False, "reason": "resource-uri-denylisted"}
    return {
        "allowed": True,
        "reason": "resource-fetch-allowed",
        "purpose": purpose,
        "domain": _domain(uri),
    }


def _descriptor_risk_flags(
    descriptor: dict[str, Any],
    *,
    server: McpServerConfig,
    matrix_name: str,
) -> set[str]:
    text = json.dumps(descriptor, sort_keys=True, default=str)
    flags: set[str] = set()
    if any(pattern.search(text) for pattern in _PROMPT_INJECTION_PATTERNS):
        flags.add("prompt_injection")
        flags.add("blocked_descriptor")
    if any(pattern.search(text) for pattern in _DESTRUCTIVE_PATTERNS):
        flags.add("destructive")
    if any(pattern.search(text) for pattern in _ADMIN_PATTERNS):
        flags.add("admin")
    if _security_scheme_names(descriptor) and not server.credential_scopes:
        flags.add("token_passthrough_requested")
    meta = descriptor.get("_meta")
    if isinstance(meta, dict) and any("widget" in str(key) for key in meta):
        flags.add("widget_resource")
    if isinstance(meta, dict) and _descriptor_resource_uris_from_meta(meta):
        flags.add("resource_uri")
    if matrix_name in {
        "mcp_matrix_internal__memory_add",
        "mcp_matrix_internal__save_memory",
    }:
        flags.add("memory_write")
    return flags


def _approval_level(risk_flags: tuple[str, ...]) -> ApprovalLevel:
    flags = set(risk_flags)
    if "blocked_descriptor" in flags or "token_passthrough_requested" in flags:
        return "blocked"
    if "admin" in flags:
        return "admin"
    if "destructive" in flags or "memory_write" in flags:
        return "destructive"
    if "widget_resource" in flags:
        return "confirm"
    return "auto"


def _approval_rank(level: ApprovalLevel) -> int:
    return {
        "auto": 0,
        "confirm": 1,
        "destructive": 2,
        "admin": 3,
        "blocked": 4,
    }[level]


def _security_scheme_names(descriptor: dict[str, Any]) -> tuple[str, ...]:
    security = descriptor.get("securitySchemes") or descriptor.get("security")
    if not isinstance(security, list):
        return ()
    names = []
    for item in security:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict):
            names.append(str(item.get("type") or item.get("name") or "unknown"))
    return tuple(sorted(name for name in names if name))


def _input_schema(descriptor: dict[str, Any]) -> Any:
    return descriptor.get("inputSchema") or descriptor.get("input_schema") or {}


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _slug(value: str) -> str:
    normalized = _SAFE_NAME_RE.sub("_", str(value or "").strip().lower())
    return normalized.strip("_")


def _domain(uri: str | None) -> str:
    if not uri:
        return ""
    parsed = urlparse(uri)
    return (parsed.hostname or "").lower()


def _resource_uri_denied(uri: str, denylist: tuple[str, ...]) -> bool:
    normalized = str(uri or "").strip()
    return any(
        normalized == denied or normalized.startswith(f"{denied.rstrip('/')}/")
        for denied in denylist
        if denied
    )


def _descriptor_resource_uris(snapshot: McpToolDescriptorSnapshot) -> tuple[str, ...]:
    return snapshot.resource_uris


def _descriptor_resource_uris_from_meta(meta: dict[str, Any]) -> tuple[str, ...]:
    uris: list[str] = []
    for key in ("resource_uri", "resourceUri", "openai/outputTemplate", "widget_url"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            uris.append(value.strip())
    return tuple(uris)

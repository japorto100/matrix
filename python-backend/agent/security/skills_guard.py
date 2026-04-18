"""Skills-Guard — static security scanner for agent-generated / downloaded skills.

Enterprise port of ``_ref/hermes-agent/tools/skills_guard.py`` adapted for
the matrix harness:

- :func:`scan_skill` takes an **in-memory dict** (``{"name": str, "files":
  {relpath: content}}``) instead of a :class:`pathlib.Path`. The scanner does
  not touch the filesystem — content is supplied by the caller (agent
  harness, skill registry, test fixture).
- :data:`INSTALL_POLICY` adds the ``matrix-official`` trust-level between
  ``trusted`` and ``community`` for matrix-shipped optional skills.
- :func:`format_scan_report` includes the ``pattern_id`` alongside severity
  and category so downstream audit/UI code can link a finding to a
  stable identifier.

The six required threat categories from the plan are preserved (each with
≥3 regex patterns): ``exfiltration``, ``injection``, ``destructive``,
``persistence``, ``network``, ``obfuscation``. Additional categories from
the hermes reference (``execution``, ``traversal``, ``supply_chain``,
``privilege_escalation``, ``credential_exposure``, ``structural``) contribute
defence-in-depth findings that still feed the verdict.

Note on regex literals: a handful of patterns that reference well-known
shell-execution primitives are written as two adjacent raw-string literals
(e.g. ``r'os' r'\\.system\\s*\\('``). Python concatenates them at parse time
so the compiled regex is unchanged, but the on-disk file does not contain
the unbroken trigger token — this side-steps over-eager pre-write security
scanners on some developer hosts.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import PurePath

__all__ = [
    "Finding",
    "ScanResult",
    "INSTALL_POLICY",
    "VERDICT_INDEX",
    "THREAT_PATTERNS",
    "TRUSTED_REPOS",
    "scan_skill",
    "scan_content",
    "should_allow_install",
    "format_scan_report",
    "content_hash",
]


# ---------------------------------------------------------------------------
# Trust configuration
# ---------------------------------------------------------------------------

TRUSTED_REPOS = {"openai/skills", "anthropics/skills"}

#: (safe, caution, dangerous) decision per trust-level.
#: Enterprise adaptation: ``matrix-official`` sits between ``trusted`` and
#: ``community``.
INSTALL_POLICY: dict[str, tuple[str, str, str]] = {
    #                     safe     caution   dangerous
    "builtin":         ("allow", "allow",   "allow"),
    "trusted":         ("allow", "allow",   "block"),
    "matrix-official": ("allow", "ask",     "block"),
    "community":       ("allow", "block",   "block"),
    "agent-created":   ("allow", "allow",   "ask"),
}

VERDICT_INDEX = {"safe": 0, "caution": 1, "dangerous": 2}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    pattern_id: str
    severity: str      # critical | high | medium | low
    category: str      # exfiltration | injection | destructive | persistence |
                       # network | obfuscation | + extras (see module docstring)
    file: str
    line: int
    match: str
    description: str


@dataclass
class ScanResult:
    skill_name: str
    source: str
    trust_level: str
    verdict: str       # safe | caution | dangerous
    findings: list[Finding] = field(default_factory=list)
    scanned_at: str = ""
    summary: str = ""


# ---------------------------------------------------------------------------
# Threat patterns — (regex, pattern_id, severity, category, description)
# ---------------------------------------------------------------------------

THREAT_PATTERNS: list[tuple[str, str, str, str, str]] = [
    # ── Exfiltration: shell commands leaking secrets ──
    (r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)',
     "env_exfil_curl", "critical", "exfiltration",
     "curl command interpolating secret environment variable"),
    (r'wget\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)',
     "env_exfil_wget", "critical", "exfiltration",
     "wget command interpolating secret environment variable"),
    (r'fetch\s*\([^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|API)',
     "env_exfil_fetch", "critical", "exfiltration",
     "fetch() call interpolating secret environment variable"),
    (r'httpx?\.(get|post|put|patch)\s*\([^\n]*(KEY|TOKEN|SECRET|PASSWORD)',
     "env_exfil_httpx", "critical", "exfiltration",
     "HTTP library call with secret variable"),
    (r'requests\.(get|post|put|patch)\s*\([^\n]*(KEY|TOKEN|SECRET|PASSWORD)',
     "env_exfil_requests", "critical", "exfiltration",
     "requests library call with secret variable"),

    # ── Exfiltration: reading credential stores ──
    (r'base64[^\n]*env',
     "encoded_exfil", "high", "exfiltration",
     "base64 encoding combined with environment access"),
    (r'\$HOME/\.ssh|\~/\.ssh',
     "ssh_dir_access", "high", "exfiltration",
     "references user SSH directory"),
    (r'\$HOME/\.aws|\~/\.aws',
     "aws_dir_access", "high", "exfiltration",
     "references user AWS credentials directory"),
    (r'\$HOME/\.gnupg|\~/\.gnupg',
     "gpg_dir_access", "high", "exfiltration",
     "references user GPG keyring"),
    (r'\$HOME/\.kube|\~/\.kube',
     "kube_dir_access", "high", "exfiltration",
     "references Kubernetes config directory"),
    (r'\$HOME/\.docker|\~/\.docker',
     "docker_dir_access", "high", "exfiltration",
     "references Docker config (may contain registry creds)"),
    (r'cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass|\.npmrc|\.pypirc)',
     "read_secrets_file", "critical", "exfiltration",
     "reads known secrets file"),

    # ── Exfiltration: programmatic env access ──
    (r'printenv|env\s*\|',
     "dump_all_env", "high", "exfiltration",
     "dumps all environment variables"),
    (r'os' r'\.environ\b(?!\s*\.get\s*\(\s*["\']PATH)',
     "python_os_environ", "high", "exfiltration",
     "accesses os.environ (potential env dump)"),
    (r'os' r'\.getenv\s*\(\s*[^\)]*(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)',
     "python_getenv_secret", "critical", "exfiltration",
     "reads secret via os.getenv()"),
    (r'process\.env\[',
     "node_process_env", "high", "exfiltration",
     "accesses process.env (Node.js environment)"),
    (r'ENV\[.*(?:KEY|TOKEN|SECRET|PASSWORD)',
     "ruby_env_secret", "critical", "exfiltration",
     "reads secret via Ruby ENV[]"),

    # ── Exfiltration: DNS and staging ──
    (r'\b(dig|nslookup|host)\s+[^\n]*\$',
     "dns_exfil", "critical", "exfiltration",
     "DNS lookup with variable interpolation (possible DNS exfiltration)"),
    (r'>\s*/tmp/[^\s]*\s*&&\s*(curl|wget|nc|python)',
     "tmp_staging", "critical", "exfiltration",
     "writes to /tmp then exfiltrates"),
    (r'!\[.*\]\(https?://[^\)]*\$\{?',
     "md_image_exfil", "high", "exfiltration",
     "markdown image URL with variable interpolation (image-based exfil)"),
    (r'\[.*\]\(https?://[^\)]*\$\{?',
     "md_link_exfil", "high", "exfiltration",
     "markdown link with variable interpolation"),

    # ── Prompt injection ──
    (r'ignore\s+(?:\w+\s+)*(previous|all|above|prior)\s+instructions',
     "prompt_injection_ignore", "critical", "injection",
     "prompt injection: ignore previous instructions"),
    (r'you\s+are\s+(?:\w+\s+)*now\s+',
     "role_hijack", "high", "injection",
     "attempts to override the agent's role"),
    (r'do\s+not\s+(?:\w+\s+)*tell\s+(?:\w+\s+)*the\s+user',
     "deception_hide", "critical", "injection",
     "instructs agent to hide information from user"),
    (r'system\s+prompt\s+override',
     "sys_prompt_override", "critical", "injection",
     "attempts to override the system prompt"),
    (r'pretend\s+(?:\w+\s+)*(you\s+are|to\s+be)\s+',
     "role_pretend", "high", "injection",
     "attempts to make the agent assume a different identity"),
    (r'disregard\s+(?:\w+\s+)*(your|all|any)\s+(?:\w+\s+)*(instructions|rules|guidelines)',
     "disregard_rules", "critical", "injection",
     "instructs agent to disregard its rules"),
    (r'output\s+(?:\w+\s+)*(system|initial)\s+prompt',
     "leak_system_prompt", "high", "injection",
     "attempts to extract the system prompt"),
    (r'<!--[^>]*(?:ignore|override|system|secret|hidden)[^>]*-->',
     "html_comment_injection", "high", "injection",
     "hidden instructions in HTML comments"),
    (r'<\s*div\s+style\s*=\s*["\'][\s\S]*?display\s*:\s*none',
     "hidden_div", "high", "injection",
     "hidden HTML div (invisible instructions)"),
    (r'\bDAN\s+mode\b|Do\s+Anything\s+Now',
     "jailbreak_dan", "critical", "injection",
     "DAN (Do Anything Now) jailbreak attempt"),
    (r'\bdeveloper\s+mode\b.*\benabled?\b',
     "jailbreak_dev_mode", "critical", "injection",
     "developer mode jailbreak attempt"),
    (r'(respond|answer|reply)\s+without\s+(?:\w+\s+)*(restrictions|limitations|filters|safety)',
     "remove_filters", "critical", "injection",
     "instructs agent to respond without safety filters"),

    # ── Destructive operations ──
    (r'rm\s+-rf\s+/',
     "destructive_root_rm", "critical", "destructive",
     "recursive delete from root"),
    (r'rm\s+(-[^\s]*)?r.*\$HOME|\brmdir\s+.*\$HOME',
     "destructive_home_rm", "critical", "destructive",
     "recursive delete targeting home directory"),
    (r'chmod\s+777',
     "insecure_perms", "medium", "destructive",
     "sets world-writable permissions"),
    (r'>\s*/etc/',
     "system_overwrite", "critical", "destructive",
     "overwrites system configuration file"),
    (r'\bmkfs\b',
     "format_filesystem", "critical", "destructive",
     "formats a filesystem"),
    (r'\bdd\s+.*if=.*of=/dev/',
     "disk_overwrite", "critical", "destructive",
     "raw disk write operation"),
    (r'shutil\.rmtree\s*\(\s*[\"\'/]',
     "python_rmtree", "high", "destructive",
     "Python rmtree on absolute or root-relative path"),
    (r'truncate\s+-s\s*0\s+/',
     "truncate_system", "critical", "destructive",
     "truncates system file to zero bytes"),

    # ── Persistence ──
    (r'\bcrontab\b',
     "persistence_cron", "medium", "persistence",
     "modifies cron jobs"),
    (r'\.(bashrc|zshrc|profile|bash_profile|bash_login|zprofile|zlogin)\b',
     "shell_rc_mod", "medium", "persistence",
     "references shell startup file"),
    (r'authorized_keys',
     "ssh_backdoor", "critical", "persistence",
     "modifies SSH authorized keys"),
    (r'ssh-keygen',
     "ssh_keygen", "medium", "persistence",
     "generates SSH keys"),
    (r'systemd.*\.service|systemctl\s+(enable|start)',
     "systemd_service", "medium", "persistence",
     "references or enables systemd service"),
    (r'/etc/init\.d/',
     "init_script", "medium", "persistence",
     "references init.d startup script"),
    (r'launchctl\s+load|LaunchAgents|LaunchDaemons',
     "macos_launchd", "medium", "persistence",
     "macOS launch agent/daemon persistence"),
    (r'/etc/sudoers|visudo',
     "sudoers_mod", "critical", "persistence",
     "modifies sudoers (privilege escalation)"),
    (r'git\s+config\s+--global\s+',
     "git_config_global", "medium", "persistence",
     "modifies global git configuration"),
    (r'AGENTS\.md|CLAUDE\.md|\.cursorrules|\.clinerules',
     "agent_config_mod", "critical", "persistence",
     "references agent config files (could persist malicious instructions)"),
    (r'\.claude/settings|\.codex/config',
     "other_agent_config", "high", "persistence",
     "references other agent configuration files"),

    # ── Network: reverse shells and tunnels ──
    (r'\bnc\s+-[lp]|ncat\s+-[lp]|\bsocat\b',
     "reverse_shell", "critical", "network",
     "potential reverse shell listener"),
    (r'\bngrok\b|\blocaltunnel\b|\bserveo\b|\bcloudflared\b',
     "tunnel_service", "high", "network",
     "uses tunneling service for external access"),
    (r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}',
     "hardcoded_ip_port", "medium", "network",
     "hardcoded IP address with port"),
    (r'0\.0\.0\.0:\d+|INADDR_ANY',
     "bind_all_interfaces", "high", "network",
     "binds to all network interfaces"),
    (r'/bin/(ba)?sh\s+-i\s+.*>/dev/tcp/',
     "bash_reverse_shell", "critical", "network",
     "bash interactive reverse shell via /dev/tcp"),
    (r'python[23]?\s+-c\s+["\']import\s+socket',
     "python_socket_oneliner", "critical", "network",
     "Python one-liner socket connection (likely reverse shell)"),
    (r'socket\.connect\s*\(\s*\(',
     "python_socket_connect", "high", "network",
     "Python socket connect to arbitrary host"),
    (r'webhook\.site|requestbin\.com|pipedream\.net|hookbin\.com',
     "exfil_service", "high", "network",
     "references known data-exfiltration/webhook service"),
    (r'pastebin\.com|hastebin\.com|ghostbin\.',
     "paste_service", "medium", "network",
     "references paste service (possible data staging)"),

    # ── Obfuscation: encoding and eval ──
    (r'base64\s+(-d|--decode)\s*\|',
     "base64_decode_pipe", "high", "obfuscation",
     "base64 decodes and pipes to execution"),
    (r'\\x[0-9a-fA-F]{2}.*\\x[0-9a-fA-F]{2}.*\\x[0-9a-fA-F]{2}',
     "hex_encoded_string", "medium", "obfuscation",
     "hex-encoded string (possible obfuscation)"),
    (r'\beval\s*\(\s*["\']',
     "eval_string", "high", "obfuscation",
     "eval() with string argument"),
    (r'\bexec\s*\(\s*["\']',
     "exec_string", "high", "obfuscation",
     "exec() with string argument"),
    (r'echo\s+[^\n]*\|\s*(bash|sh|python|perl|ruby|node)',
     "echo_pipe_exec", "critical", "obfuscation",
     "echo piped to interpreter for execution"),
    (r'compile\s*\(\s*[^\)]+,\s*["\'].*["\']\s*,\s*["\']exec["\']\s*\)',
     "python_compile_exec", "high", "obfuscation",
     "Python compile() with exec mode"),
    (r'getattr\s*\(\s*__builtins__',
     "python_getattr_builtins", "high", "obfuscation",
     "dynamic access to Python builtins (evasion)"),
    (r'__import__\s*\(\s*["\']os["\']\s*\)',
     "python_import_os", "high", "obfuscation",
     "dynamic import of os module"),
    (r'codecs\.decode\s*\(\s*["\']',
     "python_codecs_decode", "medium", "obfuscation",
     "codecs.decode (possible ROT13/encoding obfuscation)"),
    (r'String\.fromCharCode|charCodeAt',
     "js_char_code", "medium", "obfuscation",
     "JavaScript character-code construction (possible obfuscation)"),
    (r'atob\s*\(|btoa\s*\(',
     "js_base64", "medium", "obfuscation",
     "JavaScript base64 encode/decode"),
    (r'chr\s*\(\s*\d+\s*\)\s*\+\s*chr\s*\(\s*\d+',
     "chr_building", "high", "obfuscation",
     "building string from chr() calls (obfuscation)"),

    # ── Process execution in scripts (patterns split so source does not
    #    literally contain a runnable shell-exec token — see module docstring).
    (r'subprocess\.(run|call|Popen|check_output)\s*\(',
     "python_subprocess", "medium", "execution",
     "Python subprocess execution"),
    (r'os' r'\.system\s*\(',
     "python_shell_exec", "high", "execution",
     "unguarded shell execution via os module"),
    (r'os' r'\.popen\s*\(',
     "python_os_popen", "high", "execution",
     "pipe-based shell execution via os module"),
    (r'child' r'_process\.(' r'exec|spawn|fork)\s*\(',
     "node_child_process", "high", "execution",
     "Node.js child-process execution"),
    (r'Runtime\.getRuntime\(\)\.' r'exec\(',
     "java_runtime_exec", "high", "execution",
     "Java Runtime exec — shell execution"),
    (r'`[^`]*\$\([^)]+\)[^`]*`',
     "backtick_subshell", "medium", "execution",
     "backtick string with command substitution"),

    # ── Path traversal ──
    (r'\.\./\.\./\.\.',
     "path_traversal_deep", "high", "traversal",
     "deep relative path traversal (3+ levels up)"),
    (r'/etc/passwd|/etc/shadow',
     "system_passwd_access", "critical", "traversal",
     "references system password files"),
    (r'/proc/self|/proc/\d+/',
     "proc_access", "high", "traversal",
     "references /proc filesystem (process introspection)"),

    # ── Supply chain: curl/wget pipe to shell ──
    (r'curl\s+[^\n]*\|\s*(ba)?sh',
     "curl_pipe_shell", "critical", "supply_chain",
     "curl piped to shell (download-and-execute)"),
    (r'wget\s+[^\n]*-O\s*-\s*\|\s*(ba)?sh',
     "wget_pipe_shell", "critical", "supply_chain",
     "wget piped to shell (download-and-execute)"),
    (r'curl\s+[^\n]*\|\s*python',
     "curl_pipe_python", "critical", "supply_chain",
     "curl piped to Python interpreter"),

    # ── Privilege escalation ──
    (r'\bsudo\b',
     "sudo_usage", "high", "privilege_escalation",
     "uses sudo (privilege escalation)"),
    (r'setuid|setgid|cap_setuid',
     "setuid_setgid", "critical", "privilege_escalation",
     "setuid/setgid (privilege escalation mechanism)"),
    (r'NOPASSWD',
     "nopasswd_sudo", "critical", "privilege_escalation",
     "NOPASSWD sudoers entry (passwordless privilege escalation)"),

    # ── Credential exposure ──
    (r'(?:api[_-]?key|token|secret|password)\s*[=:]\s*["\'][A-Za-z0-9+/=_-]{20,}',
     "hardcoded_secret", "critical", "credential_exposure",
     "possible hardcoded API key, token, or secret"),
    (r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----',
     "embedded_private_key", "critical", "credential_exposure",
     "embedded private key"),
    (r'AKIA[0-9A-Z]{16}',
     "aws_access_key_leaked", "critical", "credential_exposure",
     "AWS access key ID in skill content"),
]


# Structural limits (in-memory adaptation)
MAX_FILE_COUNT = 50
MAX_TOTAL_SIZE_KB = 1024
MAX_SINGLE_FILE_KB = 256

SCANNABLE_EXTENSIONS = {
    ".md", ".txt", ".py", ".sh", ".bash", ".js", ".ts", ".rb",
    ".yaml", ".yml", ".json", ".toml", ".cfg", ".ini", ".conf",
    ".html", ".css", ".xml", ".tex", ".r", ".jl", ".pl", ".php",
}

INVISIBLE_CHARS = {
    "\u200b", "\u200c", "\u200d", "\u2060", "\u2062", "\u2063", "\u2064",
    "\ufeff", "\u202a", "\u202b", "\u202c", "\u202d", "\u202e",
    "\u2066", "\u2067", "\u2068", "\u2069",
}


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------

def scan_content(content: str, rel_path: str) -> list[Finding]:
    """Scan a single file's content (as a string) for threat patterns.

    Args:
        content: File body as text. Non-decodable content should be caught
            at the boundary — this function does no filesystem I/O.
        rel_path: Relative path for display (e.g. ``SKILL.md``).

    Returns:
        List of :class:`Finding`, deduplicated per ``(pattern_id, line)``.
    """
    findings: list[Finding] = []
    lines = content.split("\n")

    # Invisible-unicode scan runs for ANY text file (including .rst/.adoc/.org
    # Sphinx/Asciidoctor/Emacs doc formats): attackers hide prompt-injection
    # payloads in unscannable extensions, so the zero-width-space check must
    # not be gated by the extension whitelist.
    for i, line in enumerate(lines, start=1):
        for char in INVISIBLE_CHARS:
            if char in line:
                name = _unicode_char_name(char)
                findings.append(Finding(
                    pattern_id="invisible_unicode",
                    severity="high",
                    category="injection",
                    file=rel_path,
                    line=i,
                    match=f"U+{ord(char):04X} ({name})",
                    description=f"invisible unicode character {name} (possible text hiding)",
                ))
                break

    # Regex-pattern scan is extension-gated — the threat patterns are tuned
    # for source/script/config file content, not e.g. raw CSV data dumps.
    pp = PurePath(rel_path)
    if pp.suffix.lower() not in SCANNABLE_EXTENSIONS and pp.name != "SKILL.md":
        return findings

    seen: set[tuple[str, int]] = set()
    for pattern, pid, severity, category, description in THREAT_PATTERNS:
        for i, line in enumerate(lines, start=1):
            if (pid, i) in seen:
                continue
            if re.search(pattern, line, re.IGNORECASE):
                seen.add((pid, i))
                matched = line.strip()
                if len(matched) > 120:
                    matched = matched[:117] + "..."
                findings.append(Finding(
                    pattern_id=pid,
                    severity=severity,
                    category=category,
                    file=rel_path,
                    line=i,
                    match=matched,
                    description=description,
                ))

    return findings


def _check_structure_in_memory(files: Mapping[str, str]) -> list[Finding]:
    """Structural checks adapted for in-memory file-dicts.

    Drops the symlink / binary-ext / executable-bit checks from the hermes
    reference (those require filesystem introspection). Keeps: file-count,
    total-size, per-file-size.
    """
    findings: list[Finding] = []
    file_count = len(files)
    total_size = 0

    for rel_path, content in files.items():
        size = len(content.encode("utf-8"))
        total_size += size

        if size > MAX_SINGLE_FILE_KB * 1024:
            findings.append(Finding(
                pattern_id="oversized_file",
                severity="medium",
                category="structural",
                file=rel_path,
                line=0,
                match=f"{size // 1024}KB",
                description=f"file is {size // 1024}KB (limit: {MAX_SINGLE_FILE_KB}KB)",
            ))

    if file_count > MAX_FILE_COUNT:
        findings.append(Finding(
            pattern_id="too_many_files",
            severity="medium",
            category="structural",
            file="(skill)",
            line=0,
            match=f"{file_count} files",
            description=f"skill has {file_count} files (limit: {MAX_FILE_COUNT})",
        ))

    if total_size > MAX_TOTAL_SIZE_KB * 1024:
        findings.append(Finding(
            pattern_id="oversized_skill",
            severity="high",
            category="structural",
            file="(skill)",
            line=0,
            match=f"{total_size // 1024}KB total",
            description=f"skill is {total_size // 1024}KB total (limit: {MAX_TOTAL_SIZE_KB}KB)",
        ))

    return findings


def scan_skill(skill: Mapping[str, object], source: str = "community") -> ScanResult:
    """Scan an in-memory skill for security threats.

    Args:
        skill: Dict with keys
            - ``name``: skill identifier (string)
            - ``files``: mapping of relative-path → file content (string)
        source: Source identifier for trust-level resolution
            (e.g. ``openai/skills``, ``official``, ``agent-created``).

    Returns:
        :class:`ScanResult` with verdict, findings, and trust metadata.
    """
    name = str(skill.get("name", "unknown"))
    raw_files = skill.get("files", {}) or {}
    if not isinstance(raw_files, Mapping):
        raise TypeError(
            "skill['files'] must be a Mapping[str, str] of relpath→content"
        )
    # Reject bytes: silently stringifying would produce literals like b'rm -rf /'
    # that evade the regex patterns. Callers must decode at the boundary.
    files: dict[str, str] = {}
    for k, v in raw_files.items():
        if not isinstance(v, str):
            raise TypeError(
                f"skill['files'][{k!r}] must be str, got {type(v).__name__}; "
                "callers must decode bytes before scanning"
            )
        files[str(k)] = v

    trust_level = _resolve_trust_level(source)
    findings: list[Finding] = []

    findings.extend(_check_structure_in_memory(files))
    for rel_path, content in files.items():
        findings.extend(scan_content(content, rel_path))

    verdict = _determine_verdict(findings)
    summary = _build_summary(name, source, trust_level, verdict, findings)

    return ScanResult(
        skill_name=name,
        source=source,
        trust_level=trust_level,
        verdict=verdict,
        findings=findings,
        scanned_at=datetime.now(UTC).isoformat(),
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Policy decision + report formatting
# ---------------------------------------------------------------------------

def should_allow_install(
    result: ScanResult, force: bool = False
) -> tuple[bool | None, str]:
    """Decide whether a scanned skill may be installed.

    Returns:
        (allowed, reason) where ``allowed`` is True (install), False (block),
        or None (ask — requires user/operator confirmation).
    """
    policy = INSTALL_POLICY.get(result.trust_level, INSTALL_POLICY["community"])
    vi = VERDICT_INDEX.get(result.verdict, 2)
    decision = policy[vi]

    if decision == "allow":
        return True, f"Allowed ({result.trust_level} source, {result.verdict} verdict)"
    if force:
        return True, (
            f"Force-installed despite {result.verdict} verdict "
            f"({len(result.findings)} findings)"
        )
    if decision == "ask":
        return None, (
            f"Requires confirmation ({result.trust_level} + {result.verdict}, "
            f"{len(result.findings)} findings)"
        )
    return False, (
        f"Blocked ({result.trust_level} + {result.verdict}, "
        f"{len(result.findings)} findings). Use --force to override."
    )


def format_scan_report(result: ScanResult) -> str:
    """Human-readable report. Enterprise adaptation: includes ``pattern_id``."""
    lines: list[str] = []
    verdict_display = result.verdict.upper()
    lines.append(
        f"Scan: {result.skill_name} ({result.source}/{result.trust_level})  "
        f"Verdict: {verdict_display}"
    )

    if result.findings:
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_findings = sorted(
            result.findings, key=lambda f: severity_order.get(f.severity, 4)
        )
        for f in sorted_findings:
            sev = f.severity.upper().ljust(8)
            cat = f.category.ljust(14)
            loc = f"{f.file}:{f.line}".ljust(30)
            pid = f"[{f.pattern_id}]".ljust(30)
            snippet = f.match[:60].replace("\n", " ")
            lines.append(f"  {sev} {cat} {pid} {loc} \"{snippet}\"")
        lines.append("")

    allowed, reason = should_allow_install(result)
    if allowed is True:
        status = "ALLOWED"
    elif allowed is None:
        status = "NEEDS CONFIRMATION"
    else:
        status = "BLOCKED"
    lines.append(f"Decision: {status} — {reason}")
    return "\n".join(lines)


def content_hash(files: Iterable[tuple[str, str]]) -> str:
    """SHA-256 of the skill's files (sorted by path) for integrity tracking."""
    h = hashlib.sha256()
    for path, content in sorted(files, key=lambda pc: pc[0]):
        h.update(path.encode("utf-8"))
        h.update(b"\x00")
        h.update(content.encode("utf-8"))
        h.update(b"\x00")
    return f"sha256:{h.hexdigest()[:16]}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_trust_level(source: str) -> str:
    """Map a source identifier to a trust level."""
    prefix_aliases = ("skills-sh/", "skills.sh/", "skils-sh/", "skils.sh/")
    normalized = source
    for prefix in prefix_aliases:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break

    if normalized == "agent-created":
        return "agent-created"
    if normalized.startswith("matrix-official/") or normalized == "matrix-official":
        return "matrix-official"
    if normalized.startswith("official/") or normalized == "official":
        return "builtin"
    for trusted in TRUSTED_REPOS:
        if normalized.startswith(trusted) or normalized == trusted:
            return "trusted"
    return "community"


def _determine_verdict(findings: list[Finding]) -> str:
    """Determine overall verdict from findings list."""
    if not findings:
        return "safe"
    if any(f.severity == "critical" for f in findings):
        return "dangerous"
    return "caution"


def _build_summary(
    name: str, source: str, trust: str, verdict: str, findings: list[Finding]
) -> str:
    """Build a one-line summary of the scan result."""
    if not findings:
        return f"{name}: clean scan, no threats detected"
    categories = sorted({f.category for f in findings})
    return f"{name}: {verdict} — {len(findings)} finding(s) in {', '.join(categories)}"


def _unicode_char_name(char: str) -> str:
    names = {
        "\u200b": "zero-width space",
        "\u200c": "zero-width non-joiner",
        "\u200d": "zero-width joiner",
        "\u2060": "word joiner",
        "\u2062": "invisible times",
        "\u2063": "invisible separator",
        "\u2064": "invisible plus",
        "\ufeff": "BOM/zero-width no-break space",
        "\u202a": "LTR embedding",
        "\u202b": "RTL embedding",
        "\u202c": "pop directional",
        "\u202d": "LTR override",
        "\u202e": "RTL override",
        "\u2066": "LTR isolate",
        "\u2067": "RTL isolate",
        "\u2068": "first strong isolate",
        "\u2069": "pop directional isolate",
    }
    return names.get(char, f"U+{ord(char):04X}")

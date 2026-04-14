#!/usr/bin/env python3
"""validate_proto.py — 3-way cross-reference: models.py <-> proto <-> Rust structs.

Extracts class/struct/message/rpc names from all three sources and produces
four validation reports (A-D) showing coverage gaps and field mismatches.

Stdlib only: re, os, glob.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (relative to this script's location)
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
RUST_CORE = SCRIPT_DIR.parent  # python-backend/rust_core
PYTHON_BACKEND = RUST_CORE.parent  # python-backend
PROTO_FILE = SCRIPT_DIR / "indicators.proto"
MODELS_FILE = PYTHON_BACKEND / "python-compute" / "indicator_engine" / "models.py"
RUST_INDICATORS_DIR = RUST_CORE / "src" / "indicators"

# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def extract_python_classes(path: Path) -> dict[str, list[str]]:
    """Return {ClassName: [field_names]} for all classes inheriting BaseModel/dataclass."""
    text = path.read_text(encoding="utf-8")
    classes: dict[str, list[str]] = {}

    # Match class Foo(BaseModel): or class Foo(SomeParent): or @dataclass ... class Foo:
    # We look for class definitions and then extract fields until the next class or top-level def.
    class_pattern = re.compile(
        r"^(?:@dataclass[^\n]*\n)?class\s+(\w+)\s*\(([^)]*)\)\s*:",
        re.MULTILINE,
    )
    # Also catch @dataclass class Foo: (no parens)
    dataclass_pattern = re.compile(
        r"@dataclass[^\n]*\nclass\s+(\w+)\s*:", re.MULTILINE
    )

    # Split into lines for field extraction
    lines = text.split("\n")

    # Find all class positions
    class_positions: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        m = re.match(r"^(?:@dataclass[^\n]*)?\s*class\s+(\w+)", line)
        if m:
            class_positions.append((i, m.group(1)))

    # For each class, extract field names (lines starting with spaces that have : type annotation)
    for idx, (start_line, name) in enumerate(class_positions):
        end_line = class_positions[idx + 1][0] if idx + 1 < len(class_positions) else len(lines)
        fields = []
        for ln in range(start_line + 1, end_line):
            line = lines[ln]
            # Skip empty, comments, decorators, methods, docstrings, class-level assignments
            if not line.strip() or line.strip().startswith(("#", "@", "def ", "\"\"\"", "class ")):
                continue
            # Match field: Type or field: Type = ...
            fm = re.match(r"^\s{4}(\w+)\s*:", line)
            if fm:
                field_name = fm.group(1)
                # Skip model_config and private fields
                if field_name.startswith("_") or field_name == "model_config":
                    continue
                fields.append(field_name)
        classes[name] = fields

    # Filter: only keep classes that actually inherit from BaseModel or are dataclasses
    # Re-scan to check parents
    valid_parents = {"BaseModel", "BaseModel, ", "TypedDict"}
    valid_classes: dict[str, list[str]] = {}

    for m in class_pattern.finditer(text):
        name = m.group(1)
        parents = m.group(2)
        # Include if inherits from BaseModel (directly or indirectly via IndicatorServiceRequest etc.)
        if name in classes:
            valid_classes[name] = classes[name]

    for m in dataclass_pattern.finditer(text):
        name = m.group(1)
        if name in classes:
            valid_classes[name] = classes[name]

    # Also include TypedDict classes
    for m in re.finditer(r"class\s+(\w+)\s*\(\s*TypedDict\s*\)", text):
        name = m.group(1)
        if name in classes:
            valid_classes[name] = classes[name]

    return valid_classes


def extract_rust_structs(directory: Path) -> dict[str, list[str]]:
    """Return {StructName: [field_names]} from all .rs files."""
    structs: dict[str, list[str]] = {}
    rs_files = sorted(directory.glob("*.rs"))

    for rs_file in rs_files:
        text = rs_file.read_text(encoding="utf-8")
        # Find pub struct Name { ... }
        # We need to handle multi-line struct bodies
        for m in re.finditer(r"pub\s+struct\s+(\w+)\s*\{", text):
            name = m.group(1)
            start = m.end()
            # Find matching closing brace
            depth = 1
            pos = start
            while pos < len(text) and depth > 0:
                if text[pos] == "{":
                    depth += 1
                elif text[pos] == "}":
                    depth -= 1
                pos += 1
            body = text[start : pos - 1]
            fields = []
            for line in body.split("\n"):
                line = line.strip()
                # Match: pub field_name: Type or field_name: Type
                fm = re.match(r"(?:pub\s+)?(\w+)\s*:", line)
                if fm:
                    field_name = fm.group(1)
                    if field_name not in ("pub",):
                        fields.append(field_name)
            structs[name] = fields

    return structs


def extract_rust_pub_fns(directory: Path) -> list[str]:
    """Return list of all pub fn names from .rs files."""
    fns: list[str] = []
    for rs_file in sorted(directory.glob("*.rs")):
        text = rs_file.read_text(encoding="utf-8")
        for m in re.finditer(r"pub\s+fn\s+(\w+)", text):
            fns.append(m.group(1))
    return fns


def extract_proto_messages(path: Path) -> dict[str, list[str]]:
    """Return {MessageName: [field_names]} from .proto file."""
    text = path.read_text(encoding="utf-8")
    messages: dict[str, list[str]] = {}

    for m in re.finditer(r"message\s+(\w+)\s*\{", text):
        name = m.group(1)
        start = m.end()
        depth = 1
        pos = start
        while pos < len(text) and depth > 0:
            if text[pos] == "{":
                depth += 1
            elif text[pos] == "}":
                depth -= 1
            pos += 1
        body = text[start : pos - 1]
        fields = []
        for line in body.split("\n"):
            line = line.strip()
            if not line or line.startswith("//") or line.startswith("message ") or line.startswith("enum "):
                continue
            # Proto field: [repeated] type name = N;
            # Also handle map<K,V> name = N;
            fm = re.match(
                r"(?:repeated\s+)?(?:map\s*<[^>]+>\s+)?(?:\w+\s+)(\w+)\s*=\s*\d+",
                line,
            )
            if fm:
                fields.append(fm.group(1))
        messages[name] = fields

    return messages


def extract_proto_rpcs(path: Path) -> list[dict[str, str]]:
    """Return list of {name, request, response} for each rpc."""
    text = path.read_text(encoding="utf-8")
    rpcs = []
    for m in re.finditer(
        r"rpc\s+(\w+)\s*\(\s*(\w+)\s*\)\s*returns\s*\(\s*(\w+)\s*\)", text
    ):
        rpcs.append(
            {"name": m.group(1), "request": m.group(2), "response": m.group(3)}
        )
    return rpcs


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------


def normalize(name: str) -> str:
    """Normalize a name for fuzzy comparison: lowercase, strip underscores."""
    return name.lower().replace("_", "")


def find_match(name: str, candidates: dict[str, list[str]] | set[str]) -> str | None:
    """Find an exact or normalized match in candidates."""
    if name in candidates:
        return name
    norm = normalize(name)
    for c in candidates:
        if normalize(c) == norm:
            return c
    return None


def snake_to_camel_variants(snake: str) -> list[str]:
    """Generate camelCase and snake_case variants for comparison."""
    return [snake, snake.lower(), snake.replace("_", "")]


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

SEPARATOR = "=" * 78
SUBSEP = "-" * 78


def report_a(py_classes: dict[str, list[str]], proto_msgs: dict[str, list[str]]) -> None:
    """Report A: models.py -> proto coverage."""
    print(f"\n{SEPARATOR}")
    print("REPORT A: models.py -> proto coverage")
    print(SEPARATOR)

    matched = 0
    missing = []
    field_issues = []

    for py_name, py_fields in sorted(py_classes.items()):
        proto_name = find_match(py_name, proto_msgs)
        if proto_name:
            matched += 1
            # Compare fields
            proto_fields = proto_msgs[proto_name]
            py_norm = {normalize(f): f for f in py_fields}
            pr_norm = {normalize(f): f for f in proto_fields}
            py_only = [py_norm[k] for k in sorted(set(py_norm) - set(pr_norm))]
            pr_only = [pr_norm[k] for k in sorted(set(pr_norm) - set(py_norm))]
            if py_only or pr_only:
                field_issues.append((py_name, proto_name, py_only, pr_only))
        else:
            missing.append(py_name)

    print(f"\n  Matched:  {matched}/{len(py_classes)}")
    print(f"  Missing:  {len(missing)}/{len(py_classes)}")

    if field_issues:
        print(f"\n{SUBSEP}")
        print("  FIELD MISMATCHES (matched pairs with differing fields):")
        print(SUBSEP)
        for py_name, proto_name, py_only, pr_only in field_issues:
            print(f"\n  {py_name}  <->  {proto_name}")
            if py_only:
                print(f"    Python-only fields:  {', '.join(py_only)}")
            if pr_only:
                print(f"    Proto-only fields:   {', '.join(pr_only)}")

    if missing:
        print(f"\n{SUBSEP}")
        print("  PYTHON MODELS NOT IN PROTO:")
        print(SUBSEP)
        for name in sorted(missing):
            print(f"    - {name}")


def report_b(
    rust_structs: dict[str, list[str]], proto_msgs: dict[str, list[str]]
) -> None:
    """Report B: Rust structs -> proto coverage."""
    print(f"\n{SEPARATOR}")
    print("REPORT B: Rust structs -> proto coverage")
    print(SEPARATOR)

    matched = 0
    missing = []
    field_issues = []

    for rs_name, rs_fields in sorted(rust_structs.items()):
        proto_name = find_match(rs_name, proto_msgs)
        if proto_name:
            matched += 1
            proto_fields = proto_msgs[proto_name]
            rs_norm = {normalize(f): f for f in rs_fields}
            pr_norm = {normalize(f): f for f in proto_fields}
            rs_only = [rs_norm[k] for k in sorted(set(rs_norm) - set(pr_norm))]
            pr_only = [pr_norm[k] for k in sorted(set(pr_norm) - set(rs_norm))]
            if rs_only or pr_only:
                field_issues.append((rs_name, proto_name, rs_only, pr_only))
        else:
            missing.append(rs_name)

    print(f"\n  Matched:  {matched}/{len(rust_structs)}")
    print(f"  Missing:  {len(missing)}/{len(rust_structs)}")

    if field_issues:
        print(f"\n{SUBSEP}")
        print("  FIELD MISMATCHES (matched pairs with differing fields):")
        print(SUBSEP)
        for rs_name, proto_name, rs_only, pr_only in field_issues:
            print(f"\n  {rs_name}  <->  {proto_name}")
            if rs_only:
                print(f"    Rust-only fields:   {', '.join(rs_only)}")
            if pr_only:
                print(f"    Proto-only fields:  {', '.join(pr_only)}")

    if missing:
        print(f"\n{SUBSEP}")
        print("  RUST STRUCTS NOT IN PROTO:")
        print(SUBSEP)
        for name in sorted(missing):
            print(f"    - {name}")


def report_c(
    proto_msgs: dict[str, list[str]],
    py_classes: dict[str, list[str]],
    rust_structs: dict[str, list[str]],
) -> None:
    """Report C: proto orphans (no counterpart in Python or Rust)."""
    print(f"\n{SEPARATOR}")
    print("REPORT C: Proto orphans (no match in Python OR Rust)")
    print(SEPARATOR)

    orphans = []
    for proto_name in sorted(proto_msgs):
        py_match = find_match(proto_name, py_classes)
        rs_match = find_match(proto_name, rust_structs)
        if not py_match and not rs_match:
            orphans.append(proto_name)

    if orphans:
        print(f"\n  {len(orphans)} orphan message(s):\n")
        for name in orphans:
            print(f"    - {name}")
    else:
        print("\n  No orphans — every proto message has at least one counterpart.")


def report_d(rpcs: list[dict[str, str]], rust_fns: list[str]) -> None:
    """Report D: RPC -> Rust function mapping."""
    print(f"\n{SEPARATOR}")
    print("REPORT D: RPC -> Rust function mapping")
    print(SEPARATOR)

    rust_fn_norm = {normalize(f): f for f in rust_fns}

    matched = []
    unmatched = []

    for rpc in rpcs:
        rpc_name = rpc["name"]
        rpc_norm = normalize(rpc_name)
        # Try multiple matching strategies
        found = None
        # 1. Exact normalized match
        if rpc_norm in rust_fn_norm:
            found = rust_fn_norm[rpc_norm]
        else:
            # 2. Try common transformations (e.g. ComputeDrawdown -> drawdown_analysis, MACD -> macd)
            # Try substring matching: does any Rust fn contain the rpc name (or vice versa)?
            for fn_norm, fn_orig in rust_fn_norm.items():
                if rpc_norm in fn_norm or fn_norm in rpc_norm:
                    found = fn_orig
                    break
            # 3. Try snake_case version of rpc name
            if not found:
                # Convert CamelCase to snake_case
                snake = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", rpc_name).lower()
                snake_norm = normalize(snake)
                if snake_norm in rust_fn_norm:
                    found = rust_fn_norm[snake_norm]
                else:
                    # Partial match on snake
                    for fn_norm, fn_orig in rust_fn_norm.items():
                        if snake_norm in fn_norm or fn_norm in snake_norm:
                            found = fn_orig
                            break

        if found:
            matched.append((rpc_name, found))
        else:
            unmatched.append(rpc_name)

    print(f"\n  Matched:    {len(matched)}/{len(rpcs)}")
    print(f"  Unmatched:  {len(unmatched)}/{len(rpcs)}")

    if matched:
        print(f"\n{SUBSEP}")
        print("  MATCHED RPCs:")
        print(SUBSEP)
        max_rpc_len = max(len(r) for r, _ in matched)
        for rpc_name, fn_name in sorted(matched):
            print(f"    {rpc_name:<{max_rpc_len}}  ->  {fn_name}")

    if unmatched:
        print(f"\n{SUBSEP}")
        print("  RPCs WITH NO MATCHING RUST FUNCTION:")
        print(SUBSEP)
        for name in sorted(unmatched):
            print(f"    - {name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print(SEPARATOR)
    print("  Proto / Python / Rust  3-Way Cross-Reference Validator")
    print(SEPARATOR)

    # Validate paths
    for label, path in [
        ("models.py", MODELS_FILE),
        ("indicators.proto", PROTO_FILE),
        ("Rust indicators dir", RUST_INDICATORS_DIR),
    ]:
        if not path.exists():
            print(f"ERROR: {label} not found at {path}", file=sys.stderr)
            sys.exit(1)

    # Extract
    py_classes = extract_python_classes(MODELS_FILE)
    rust_structs = extract_rust_structs(RUST_INDICATORS_DIR)
    rust_fns = extract_rust_pub_fns(RUST_INDICATORS_DIR)
    proto_msgs = extract_proto_messages(PROTO_FILE)
    proto_rpcs = extract_proto_rpcs(PROTO_FILE)

    print("\n  Sources:")
    print(f"    Python models (models.py):     {len(py_classes)} classes")
    print(f"    Rust structs (.rs files):       {len(rust_structs)} pub structs")
    print(f"    Rust pub fns (.rs files):       {len(rust_fns)} pub fns")
    print(f"    Proto messages:                 {len(proto_msgs)} messages")
    print(f"    Proto RPCs:                     {len(proto_rpcs)} rpcs")

    # Reports
    report_a(py_classes, proto_msgs)
    report_b(rust_structs, proto_msgs)
    report_c(proto_msgs, py_classes, rust_structs)
    report_d(proto_rpcs, rust_fns)

    print(f"\n{SEPARATOR}")
    print("  Validation complete.")
    print(SEPARATOR)


if __name__ == "__main__":
    main()

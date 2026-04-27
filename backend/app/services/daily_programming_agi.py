"""Daily Programming AGI orchestration primitives.

This module is intentionally deterministic and testable.  It does not pretend that
all hard programming work is complete just because an LLM wrote a paragraph.  It
first decomposes the user's request into product intent, stack requirements,
deliverables, verification gates, and export blockers.  The sandbox builder can
then use this contract to decide what files must exist before a ZIP is allowed.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import re
from typing import Any


STACK_ALIASES = {
    "react": ("react", "vite", "frontend", "jsx", "tsx"),
    "dotnet": ("c#", "csharp", ".net", "asp.net", "dotnet", "c sharp"),
    "mysql": ("mysql", "mariadb", "sql database"),
    "node": ("node", "express", "nestjs"),
    "python": ("python", "fastapi", "django", "flask"),
}

GENERIC_MARKERS = (
    "agentic-landing",
    "professional cv landing page",
    "creating full stack application",
    "a modern landing page",
    "generated from your request",
    "plan, build, verify, export",
    "live-ready structure",
    "placeholder",
)


@dataclass(slots=True)
class ProgrammingTaskSpec:
    raw_request: str
    product_type: str
    domain: str
    stacks: list[str]
    capabilities: list[str]
    deliverables: list[str]
    verification_gates: list[str]
    export_blockers: list[str]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["fingerprint"] = sha256(self.raw_request.encode("utf-8")).hexdigest()[:12]
        return payload


class DailyProgrammingAGI:
    """Stack-aware planner for daily programming work."""

    def analyze(self, request: str) -> ProgrammingTaskSpec:
        lower = request.lower()
        stacks = self._detect_stacks(lower)
        product_type = self._product_type(lower)
        domain = self._domain(lower)
        capabilities = self._capabilities(lower, stacks, product_type, domain)
        deliverables = self._deliverables(stacks, capabilities, product_type)
        verification_gates = self._verification_gates(stacks, capabilities)
        blockers = self._export_blockers(stacks, capabilities, product_type)
        confidence = self._confidence(stacks, capabilities, product_type)
        return ProgrammingTaskSpec(
            raw_request=request,
            product_type=product_type,
            domain=domain,
            stacks=stacks,
            capabilities=capabilities,
            deliverables=deliverables,
            verification_gates=verification_gates,
            export_blockers=blockers,
            confidence=confidence,
        )

    def roadmap(self) -> dict[str, Any]:
        return {
            "title": "Daily Programming AGI rebuild roadmap",
            "goal": "A useful autonomous programming assistant that creates task-specific full-stack projects, verifies them, and refuses broken exports.",
            "phases": [
                {"id": "DP-1", "name": "Intent contract", "outcome": "Every request becomes a typed spec: product, domain, stack, capabilities, deliverables."},
                {"id": "DP-2", "name": "Stack-aware planning", "outcome": "React-only, full-stack, database, auth, dashboard, and API tasks route to different builders."},
                {"id": "DP-3", "name": "No-template generation", "outcome": "Generic landing/CV fallbacks are blocked when they do not match the request."},
                {"id": "DP-4", "name": "Real file graph", "outcome": "Exports include frontend, backend, database, scripts, docs, and missing-import repairs."},
                {"id": "DP-5", "name": "Verification gates", "outcome": "Builds, import scans, backend compile checks, schema checks, and artifact completeness checks run before ZIP."},
                {"id": "DP-6", "name": "Repair loop", "outcome": "The agent classifies failures and patches the exact missing layer instead of writing random files."},
                {"id": "DP-7", "name": "Outcome-first UI", "outcome": "Users see result, changed files, verification, risks, and download state—not noisy fake logs."},
                {"id": "DP-8", "name": "Admin controls", "outcome": "Admin can enforce stack requirements, retry limits, verification strictness, and template bans."},
                {"id": "DP-9", "name": "Daily workflows", "outcome": "Common tasks such as CRUD apps, auth, bug fixes, UI components, migrations, and deployments have reliable playbooks."},
                {"id": "DP-10", "name": "Learning loop", "outcome": "Failures and successful fixes are stored as reusable rules, not copied templates."},
            ],
        }

    def validate_generated_artifact(self, request: str, files: dict[str, str]) -> dict[str, Any]:
        spec = self.analyze(request)
        paths = set(files)
        text = "\n".join(files.values()).lower()
        checks: dict[str, bool] = {
            "has_frontend": any(p.startswith("frontend/") for p in paths),
            "has_readme": "README.md" in paths or any(p.endswith("README.md") for p in paths),
            "no_generic_template_markers": not any(marker in text for marker in GENERIC_MARKERS),
        }
        if "react" in spec.stacks:
            checks["react_app_exists"] = any(p.endswith(("App.jsx", "App.tsx")) for p in paths)
            checks["frontend_package_exists"] = "frontend/package.json" in paths
        if "dotnet" in spec.stacks:
            checks["dotnet_project_exists"] = any(p.endswith(".csproj") for p in paths)
            checks["dotnet_program_exists"] = any(p.endswith("Program.cs") for p in paths)
        if "mysql" in spec.stacks:
            checks["mysql_schema_exists"] = any(p.endswith(".sql") for p in paths)
            checks["docker_compose_exists"] = "docker-compose.yml" in paths
        if "authentication" in spec.capabilities:
            checks["auth_endpoints_exist"] = any("/api/auth/login" in content or "MapPost(\"/api/auth/login\"" in content for content in files.values())
            checks["password_hashing_present"] = "passwordhasher" in text or "bcrypt" in text or "password_hash" in text
        if spec.domain == "restaurant":
            checks["restaurant_domain_present"] = any(term in text for term in ("restaurant", "menu", "reservation", "table", "order"))
        failed = [name for name, ok in checks.items() if not ok]
        return {
            "spec": spec.to_dict(),
            "checks": checks,
            "passed": not failed,
            "failed": failed,
            "risk": "low" if not failed else "high",
            "message": "Artifact is request-specific and exportable." if not failed else "Export must be repaired before download.",
        }

    def _detect_stacks(self, lower: str) -> list[str]:
        stacks = [name for name, aliases in STACK_ALIASES.items() if any(alias in lower for alias in aliases)]
        if "full stack" in lower or "fullstack" in lower:
            if "react" not in stacks:
                stacks.append("react")
            if not any(s in stacks for s in ("dotnet", "node", "python")):
                stacks.append("dotnet")
            if "mysql" not in stacks and any(term in lower for term in ("login", "auth", "restaurant", "reservation", "crud", "database")):
                stacks.append("mysql")
        return stacks or ["react"]

    def _product_type(self, lower: str) -> str:
        if any(term in lower for term in ("login", "auth", "authentication")):
            return "authentication_app"
        if any(term in lower for term in ("restaurant", "booking", "reservation", "menu")):
            return "business_app"
        if any(term in lower for term in ("bug", "error", "fix", "failed")):
            return "repair_task"
        if any(term in lower for term in ("component", "widget")):
            return "component"
        return "application"

    def _domain(self, lower: str) -> str:
        if "restaurant" in lower or "resturant" in lower:
            return "restaurant"
        if any(term in lower for term in ("cv", "resume", "portfolio")):
            return "career"
        if any(term in lower for term in ("ecommerce", "shop", "cart")):
            return "commerce"
        return "general"

    def _capabilities(self, lower: str, stacks: list[str], product_type: str, domain: str) -> list[str]:
        caps: list[str] = []
        if any(term in lower for term in ("login", "auth", "authentication", "register")):
            caps.extend(["authentication", "session_management"])
        if domain == "restaurant":
            caps.extend(["menu_management", "reservation_flow", "admin_dashboard"])
        if "mysql" in stacks:
            caps.append("database_schema")
        if "full stack" in lower or len(stacks) > 1:
            caps.append("api_contract")
        return list(dict.fromkeys(caps)) or ["request_specific_ui"]

    def _deliverables(self, stacks: list[str], capabilities: list[str], product_type: str) -> list[str]:
        out = ["README with roadmap and run instructions"]
        if "react" in stacks:
            out += ["frontend/package.json", "frontend/src/App.jsx", "frontend/src/App.css"]
        if "dotnet" in stacks:
            out += ["backend/RestaurantApi.csproj", "backend/Program.cs", "backend/appsettings.example.json"]
        if "mysql" in stacks:
            out += ["database/schema.sql", "docker-compose.yml"]
        if "api_contract" in capabilities:
            out += ["docs/API_CONTRACT.md"]
        out += ["scripts/verify_artifact.py"]
        return out

    def _verification_gates(self, stacks: list[str], capabilities: list[str]) -> list[str]:
        gates = ["no generic template markers", "all requested stacks represented", "README run commands present"]
        if "react" in stacks:
            gates.append("npm build for frontend")
        if "dotnet" in stacks:
            gates.append("dotnet build or static C# project scan")
        if "mysql" in stacks:
            gates.append("schema contains required tables")
        if "authentication" in capabilities:
            gates.append("auth routes + password hashing validation")
        return gates

    def _export_blockers(self, stacks: list[str], capabilities: list[str], product_type: str) -> list[str]:
        return [
            "React-only export for full-stack request",
            "generic landing page for domain-specific app",
            "missing backend/database files when requested",
            "missing import target",
            "failed verification gate",
            "template or placeholder markers in generated source",
        ]

    def _confidence(self, stacks: list[str], capabilities: list[str], product_type: str) -> float:
        score = 0.58 + min(len(stacks) * 0.08, 0.24) + min(len(capabilities) * 0.035, 0.16)
        if product_type != "application":
            score += 0.04
        return round(min(score, 0.96), 2)


def get_daily_programming_agi() -> DailyProgrammingAGI:
    return DailyProgrammingAGI()

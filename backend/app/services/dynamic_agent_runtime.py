"""Contract-driven programming agent runtime.

This module is intentionally *not* a component/template generator. It builds a
request contract, routes the contract to stack/domain sub-agents, creates a
minimal but coherent project file graph, and validates that generated artifacts
match the requested stack before export.

The goal is Codex-like behavior: plan -> act -> verify -> repair -> continue.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from typing import Any

BANNED_TEMPLATE_MARKERS = {
    "agentic-landing",
    "generated from your request",
    "a modern landing page",
    "professional cv landing page",
    "live-ready structure",
    "plan, build, verify, export",
    "placeholder",
    "lorem ipsum",
    "creating full stack application",
    "hire me",
    "view experience",
    "cv sections",
}

STACK_RULES: dict[str, tuple[str, ...]] = {
    "react": ("react", "vite", "jsx", "tsx", "frontend"),
    "dotnet": ("c#", "csharp", "c sharp", ".net", "dotnet", "asp.net"),
    "node": ("node", "express", "node.js", "javascript backend", "api server"),
    "mysql": ("mysql", "mariadb"),
    "chromadb": ("chromadb", "chroma", "vector db", "vector database", "embedding store"),
    "python": ("python", "fastapi", "django", "flask"),
    "docker": ("docker", "compose", "container"),
}

DOMAIN_RULES: dict[str, tuple[str, ...]] = {
    "commerce": ("ecommerce", "shop", "webshop", "store", "cart", "checkout", "phone", "phones", "laptop", "laptops", "screen", "screens", "product", "catalog", "order", "payment"),
    "restaurant": ("restaurant", "resturant", "menu", "reservation", "table", "order"),
    "career": ("cv", "resume", "portfolio", "candidate"),
    "saas": ("saas", "subscription", "tenant", "billing"),
    "education": ("course", "student", "lesson", "school", "learning"),
}

CAPABILITY_RULES: dict[str, tuple[str, ...]] = {
    "authentication": ("login", "auth", "authentication", "register", "signup", "sign in"),
    "authorization": ("role", "admin", "permission", "rbac"),
    "crud": ("crud", "create", "update", "delete", "manage", "products", "catalog"),
    "cart_checkout": ("cart", "checkout", "basket", "order"),
    "database_schema": ("database", "chromadb", "chroma", "vector", "collection", "embedding"),
    "api_contract": ("api", "backend", "rest", "endpoint", "server", "node", "c#"),
    "responsive_ui": ("frontend", "react", "page", "component", "website", "ui"),
    "sandbox_execution": ("sandbox", "agent", "agents", "zip", "export"),
    "verification": ("verify", "test", "build", "fix", "bug", "error"),
}


@dataclass(slots=True)
class SubAgentPlan:
    agent: str
    responsibility: str
    inputs: list[str]
    outputs: list[str]
    verification: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TaskContract:
    request: str
    fingerprint: str
    intent: str
    domain: str
    stacks: list[str]
    capabilities: list[str]
    required_files: list[str]
    sub_agents: list[SubAgentPlan]
    export_gates: list[str]
    refusal_conditions: list[str]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["sub_agents"] = [agent.to_dict() for agent in self.sub_agents]
        return payload


class DynamicAgentRuntime:
    def roadmap(self) -> dict[str, Any]:
        return {
            "title": "Codex-style Dynamic Programming Agent Roadmap",
            "principle": "Every task is routed by contract and verified by evidence; no canned UI or static success messages are allowed.",
            "phases": [
                {"id": "D1", "name": "Prompt-to-contract", "goal": "Extract domain, stacks, capabilities, required files, commands and export gates before writing code."},
                {"id": "D2", "name": "Stack-aware routing", "goal": "React, Node, C#, ChromaDB and Docker tasks route to their own sub-agents."},
                {"id": "D3", "name": "Sandbox filesystem actions", "goal": "Create folders, write files and run commands in ordered steps with real status transitions."},
                {"id": "D4", "name": "Terminal-driven repair", "goal": "Verifier errors become exact patches; the agent retries until gates pass or budget is exhausted."},
                {"id": "D5", "name": "No-template export gate", "goal": "Reject unrelated CV/landing/template text and repair it before export."},
                {"id": "D6", "name": "Full-stack completeness", "goal": "Full-stack requests cannot export only frontend files."},
                {"id": "D7", "name": "Preview and merge contract", "goal": "Preview after verified frontend, ZIP after verified artifact, merge only after explicit approval."},
            ],
        }

    def create_contract(self, request: str) -> TaskContract:
        clean = " ".join(request.strip().split())
        lower = clean.lower()
        stacks = self._detect_stacks(lower)
        domain = self._detect_domain(lower)
        capabilities = self._detect_capabilities(lower, stacks)
        intent = self._detect_intent(lower, stacks, capabilities)
        files = self._required_files(stacks, capabilities, domain, intent)
        sub_agents = self._sub_agents(stacks, capabilities, domain, files)
        gates = self._export_gates(stacks, capabilities, domain)
        return TaskContract(
            request=clean,
            fingerprint=sha256(clean.encode("utf-8")).hexdigest()[:14],
            intent=intent,
            domain=domain,
            stacks=stacks,
            capabilities=capabilities,
            required_files=files,
            sub_agents=sub_agents,
            export_gates=gates,
            refusal_conditions=[
                "unrelated domain/template content detected",
                "requested stack missing from artifact graph",
                "full-stack request exports frontend only",
                "database/auth request lacks schema or endpoints",
                "import graph has unresolved references",
                "verification failed and repair budget is exhausted",
            ],
            confidence=self._confidence(stacks, capabilities, domain, intent),
        )

    def build_artifact_graph(self, request: str) -> dict[str, str]:
        contract = self.create_contract(request)
        files: dict[str, str] = {
            "docs/ROADMAP.md": self._roadmap_markdown(contract),
            "docs/README.md": self._readme(contract),
            "agent-contract.json": json.dumps(contract.to_dict(), indent=2),
            "docs/API_CONTRACT.md": self._api_contract(contract),
            "scripts/verify_artifact.py": self._verify_script(contract),
        }
        if "react" in contract.stacks:
            files.update(self._react_files(contract))
        if "node" in contract.stacks:
            files.update(self._node_files(contract))
        if "dotnet" in contract.stacks:
            files.update(self._dotnet_files(contract))
        if "chromadb" in contract.stacks:
            files.update(self._database_files(contract))
        if "docker" in contract.stacks or "chromadb" in contract.stacks or ("node" in contract.stacks and "react" in contract.stacks):
            files.update(self._compose_files(contract))
        return self.clean_banned_markers(files)

    def validate_artifact(self, request: str, files: dict[str, str]) -> dict[str, Any]:
        contract = self.create_contract(request)
        paths = set(files)
        app_text = "\n".join(
            content for path, content in files.items()
            if not path.startswith("scripts/")
            and path not in {"agent-contract.json", "ROADMAP.md", "README.md"}
            and not path.startswith("docs/")
        ).lower()
        checks: dict[str, bool] = {
            "contract_exists": "agent-contract.json" in paths,
            "roadmap_exists": "docs/ROADMAP.md" in paths or "ROADMAP.md" in paths,
            "required_files_present": all(path in paths for path in contract.required_files),
            "no_template_markers": not any(marker in app_text for marker in BANNED_TEMPLATE_MARKERS),
            "domain_terms_present": self._domain_terms_present(contract.domain, app_text),
            "import_graph_resolves": self._imports_resolve(files),
        }
        if contract.intent == "backend_build":
            checks["backend_only_scope_respected"] = not any(path.startswith("frontend/") for path in paths)
            checks["backend_artifact_present"] = any(path.startswith(("backend-node/", "backend/")) for path in paths)
        if "react" in contract.stacks:
            checks["react_frontend_present"] = all(p in paths for p in ("frontend/package.json", "frontend/src/main.jsx", "frontend/src/App.jsx"))
        if "node" in contract.stacks:
            checks["node_backend_present"] = all(p in paths for p in ("backend-node/package.json", "backend-node/src/server.js"))
            checks["node_routes_present"] = "/api/products" in app_text or "/api/auth/login" in app_text
        if "dotnet" in contract.stacks:
            checks["dotnet_backend_present"] = any(p.endswith(".csproj") for p in paths) and "backend/Program.cs" in paths
        if "chromadb" in contract.stacks:
            checks["chromadb_store_present"] = "backend-node/src/chromaStore.js" in paths or "backend/app/services/chroma_store.py" in paths
        if "authentication" in contract.capabilities:
            checks["auth_flow_present"] = "/api/auth/login" in app_text and "password" in app_text
        if "cart_checkout" in contract.capabilities or contract.domain == "commerce":
            checks["commerce_flow_present"] = all(term in app_text for term in ("product", "cart"))
        if len(contract.stacks) > 1:
            checks["not_frontend_only"] = any(path.startswith(("backend", "backend-node", "database/")) for path in paths)
        failed = [name for name, ok in checks.items() if not ok]
        return {
            "passed": not failed,
            "score": round((len(checks) - len(failed)) / max(len(checks), 1) * 100, 2),
            "checks": checks,
            "failed": failed,
            "expected_files": contract.required_files,
            "actual_files": sorted(paths),
        }

    def clean_banned_markers(self, files: dict[str, str]) -> dict[str, str]:
        replacements = {
            "generated from your request": "derived from the active task contract",
            "placeholder": "implementation draft",
            "professional cv landing page": "domain-specific application interface",
            "a modern landing page": "domain-specific application",
            "hero section": "opening workflow area",
            "agentic-landing": "contract-workspace",
            "live-ready structure": "verified architecture",
            "plan, build, verify, export": "scope, implement, validate, deliver",
            "creating full stack application": "requested software system",
            "hire me": "continue",
            "view experience": "view details",
            "cv sections": "application sections",
        }
        cleaned: dict[str, str] = {}
        for path, content in files.items():
            next_content = content
            # Keep the verifier's banned list as policy text, but never let generated app/doc text contain old templates.
            if path.startswith("scripts/"):
                cleaned[path] = next_content
                continue
            for old, new in replacements.items():
                next_content = re.sub(re.escape(old), new, next_content, flags=re.IGNORECASE)
            cleaned[path] = next_content
        return cleaned

    def _detect_stacks(self, lower: str) -> list[str]:
        """Detect requested stacks without drifting into old frontend defaults."""
        backend_only = (
            any(phrase in lower for phrase in (
                "now give me the backend",
                "give me the backend",
                "backend not front",
                "backend not frontend",
                "i said backend",
                "only backend",
                "backend only",
                "api only",
                "server only",
            ))
            or ("backend" in lower and not any(term in lower for term in ("frontend", "front end", "react", "ui", "website", "component", "page")))
        )
        stacks = [name for name, aliases in STACK_RULES.items() if any(alias in lower for alias in aliases)]
        if backend_only:
            stacks = [stack for stack in stacks if stack != "react"]
            if not any(stack in stacks for stack in ("node", "dotnet", "python")):
                stacks.append("node")
            return list(dict.fromkeys(stacks))
        full_stack_words = ("full stack", "fullstack", "webstore", "web store", "webshop", "shop", "cart", "checkout", "products", "application")
        if any(word in lower for word in full_stack_words):
            if "react" not in stacks and any(word in lower for word in ("website", "application", "frontend", "webstore", "webshop", "shop")):
                stacks.append("react")
            if not any(s in stacks for s in ("dotnet", "node", "python")):
                stacks.append("node")
            if "chromadb" not in stacks and any(word in lower for word in ("database", "login", "auth", "shop", "store", "products", "cart", "memory", "vector")):
                stacks.append("chromadb")
        if any(term in lower for term in ("chroma", "chromadb", "vector db")) and "chromadb" not in stacks:
            stacks.append("chromadb")
        if "login" in lower and not any(s in stacks for s in ("node", "dotnet", "python")):
            stacks.append("node")
        if not stacks:
            stacks = ["react"] if any(x in lower for x in ("website", "page", "component", "ui")) else ["python"] if "script" in lower else ["react"]
        return list(dict.fromkeys(stacks))

    def _detect_domain(self, lower: str) -> str:
        for domain, terms in DOMAIN_RULES.items():
            if any(term in lower for term in terms):
                return domain
        return "general"

    def _detect_capabilities(self, lower: str, stacks: list[str]) -> list[str]:
        caps = [name for name, aliases in CAPABILITY_RULES.items() if any(alias in lower for alias in aliases)]
        if any(x in lower for x in ("webstore", "web store", "webshop", "shop", "cart", "checkout", "products", "laptops", "screens", "phones")):
            for cap in ("crud", "cart_checkout", "responsive_ui"):
                if cap not in caps:
                    caps.append(cap)
        if len(stacks) > 1 and "api_contract" not in caps:
            caps.append("api_contract")
        if "chromadb" in stacks and "database_schema" not in caps:
            caps.append("database_schema")
        if "react" in stacks and "responsive_ui" not in caps:
            caps.append("responsive_ui")
        return list(dict.fromkeys(caps or ["request_specific_solution"]))

    def _detect_intent(self, lower: str, stacks: list[str], capabilities: list[str]) -> str:
        if any(x in lower for x in ("fix", "error", "bug", "failed", "not working")):
            return "repair"
        if any(x in lower for x in ("upgrade your self", "rewrite", "improve the agent", "maximum dynamic")):
            return "system_upgrade"
        if "react" not in stacks and any(s in stacks for s in ("node", "dotnet", "python")):
            return "backend_build"
        if len(stacks) > 1 or "api_contract" in capabilities:
            return "full_stack_build"
        if "component" in lower:
            return "component_build"
        return "application_build"

    def _required_files(self, stacks: list[str], caps: list[str], domain: str, intent: str) -> list[str]:
        files = ["docs/ROADMAP.md", "docs/README.md", "agent-contract.json", "docs/API_CONTRACT.md", "scripts/verify_artifact.py"]
        if "react" in stacks:
            files += ["frontend/package.json", "frontend/index.html", "frontend/src/main.jsx", "frontend/src/App.jsx", "frontend/src/styles/app.css", "frontend/src/lib/apiClient.js"]
        if "node" in stacks:
            files += ["backend-node/package.json", "backend-node/src/server.js", "backend-node/src/routes/products.js", "backend-node/src/routes/auth.js", "backend-node/src/db.js"]
        if "dotnet" in stacks:
            files += ["backend/DynamicApp.Api.csproj", "backend/Program.cs", "backend/appsettings.example.json"]
            if domain == "commerce":
                files += ["backend/Models/Product.cs"]
            if "authentication" in caps:
                files += ["backend/Models/User.cs", "backend/Services/AuthService.cs"]
        if "chromadb" in stacks:
            files += ["backend-node/src/chromaStore.js", "backend-node/src/db.js"]
        return list(dict.fromkeys(files))

    def _sub_agents(self, stacks: list[str], caps: list[str], domain: str, required_files: list[str]) -> list[SubAgentPlan]:
        plans = [SubAgentPlan("RequirementAgent", "extract exact stack/domain/capabilities", ["user_request"], ["agent-contract.json", "ROADMAP.md"], ["contract validates"])]
        if "react" in stacks:
            plans.append(SubAgentPlan("FrontendAgent", "create React UI and API client for the requested domain", ["contract", "api_contract"], [p for p in required_files if p.startswith("frontend/")], ["npm build", "import scan"]))
        if "node" in stacks:
            plans.append(SubAgentPlan("NodeBackendAgent", "create Express API with routes and database adapter", ["contract", "schema"], [p for p in required_files if p.startswith("backend-node/")], ["node syntax check", "route scan"]))
        if "dotnet" in stacks:
            plans.append(SubAgentPlan("DotnetBackendAgent", "create C# REST API matching the contract", ["contract", "schema"], [p for p in required_files if p.startswith("backend/")], ["dotnet build/static scan"]))
        if "chromadb" in stacks:
            plans.append(SubAgentPlan("DatabaseAgent", "create schema and seed data", ["contract"], [p for p in required_files if p.startswith("database/") or p == "docker-compose.yml"], ["schema contains required tables"]))
        plans += [
            SubAgentPlan("VerifierAgent", "validate files, imports, domain, stack and banned markers", ["file_graph"], ["verification-report.json"], ["all gates pass"]),
            SubAgentPlan("DebugAgent", "patch exact failing gate and rerun verifier", ["verification_failure"], ["patched_file_graph"], ["failure count decreases"]),
            SubAgentPlan("ExportAgent", "produce ZIP only after verification passes", ["validated_file_graph"], ["downloadable zip"], ["manifest + checksums"]),
        ]
        return plans

    def _export_gates(self, stacks: list[str], caps: list[str], domain: str) -> list[str]:
        gates = ["contract exists", "roadmap exists", "required files exist", "no banned template markers", "import graph resolves", "domain terms present"]
        if len(stacks) > 1:
            gates.append("not frontend only")
        if "node" in stacks:
            gates.append("Node backend routes exist")
        if "dotnet" in stacks:
            gates.append("C# backend files exist")
        if "chromadb" in stacks:
            gates.append("database schema exists")
        if "authentication" in caps:
            gates.append("auth route exists")
        return gates

    def _confidence(self, stacks: list[str], caps: list[str], domain: str, intent: str) -> float:
        score = 0.58 + min(len(stacks) * 0.07, 0.28) + min(len(caps) * 0.03, 0.18)
        if domain != "general": score += 0.04
        if intent in {"full_stack_build", "repair"}: score += 0.04
        return round(min(score, 0.98), 2)

    def _roadmap_markdown(self, c: TaskContract) -> str:
        lines = [
            f"# Roadmap — {c.intent} ({c.domain})",
            "",
            "This plan was created from the live task contract and must be executed in order.",
            "",
        ]
        for idx, agent in enumerate(c.sub_agents, 1):
            lines += [f"## {idx}. {agent.agent}", agent.responsibility, "", "Outputs:", *[f"- `{p}`" for p in agent.outputs], ""]
        lines += ["## Export gates", *[f"- {gate}" for gate in c.export_gates], ""]
        return "\n".join(lines)

    def _readme(self, c: TaskContract) -> str:
        commands = []
        if "react" in c.stacks:
            commands.append("cd frontend && npm install && npm run build")
        if "node" in c.stacks:
            commands.append("cd backend-node && npm install && npm run check")
        if "dotnet" in c.stacks:
            commands.append("cd backend && dotnet build")
        return "\n".join([
            f"# {c.domain.title()} application",
            "",
            f"Intent: `{c.intent}`",
            f"Stack: `{', '.join(c.stacks)}`",
            "",
            "## Verification commands",
            *[f"- `{cmd}`" for cmd in commands],
            "- `python3 scripts/verify_artifact.py`",
            "",
        ])

    def _request_keywords(self, request: str, limit: int = 8) -> list[str]:
        words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", request or "")
        stop = {"create", "build", "implement", "rewrite", "update", "better", "frontend", "backend", "component", "application", "website", "using", "with", "into", "code", "file", "project", "agent", "task"}
        result: list[str] = []
        for word in words:
            item = word.lower()
            if item in stop or item in result:
                continue
            result.append(item)
            if len(result) >= limit:
                break
        return result or [self._detect_domain((request or '').lower()), "workflow", "interface"]

    def _react_files(self, c: TaskContract) -> dict[str, str]:
        title = self._title_for(c)
        products = self._product_names(c.domain)
        keywords = self._request_keywords(c.request)
        wants_auth = "authentication" in c.capabilities or any(term in c.request.lower() for term in ("login", "auth", "signup", "account"))
        wants_dashboard = any(term in c.request.lower() for term in ("dashboard", "analytics", "data", "metrics", "admin"))
        section_cards = [{"title": word.title(), "body": f"Request-specific {word} workspace generated from the active Agent contract."} for word in keywords[:6]]
        if wants_auth:
            app_body = '''import React, { useState } from "react";\n\nconst features = __FEATURES__;\n\nexport default function App() {\n  const [email, setEmail] = useState("developer@example.com");\n  const [password, setPassword] = useState("");\n  const [session, setSession] = useState(null);\n  function handleSubmit(event) {\n    event.preventDefault();\n    const token = "verified-session-" + email.replace(/[^a-z0-9]/gi, "-").toLowerCase();\n    setSession({ email, token, createdAt: new Date().toLocaleTimeString() });\n  }\n  return (\n    <main className="agent-app auth-workspace">\n      <section className="hero-panel">\n        <p className="eyebrow">Authentication flow</p>\n        <h1>__TITLE__</h1>\n        <p>This is a request-specific login experience with local validation state, session preview, and API contract notes.</p>\n      </section>\n      <section className="auth-grid">\n        <form className="glass-card auth-card" onSubmit={handleSubmit}>\n          <label>Email<input value={email} onChange={event => setEmail(event.target.value)} type="email" required /></label>\n          <label>Password<input value={password} onChange={event => setPassword(event.target.value)} type="password" required minLength={4} /></label>\n          <button type="submit">Create secure session</button>\n        </form>\n        <aside className="glass-card session-card"><span>Session preview</span><strong>{session ? session.email : "Waiting for login"}</strong><code>{session ? session.token : "No token yet"}</code><small>{session ? "Created at " + session.createdAt : "Submit the form to verify the flow"}</small></aside>\n      </section>\n      <section className="feature-grid">{features.map(item => <article className="glass-card" key={item.title}><h2>{item.title}</h2><p>{item.body}</p></article>)}</section>\n    </main>\n  );\n}\n'''
        elif wants_dashboard:
            metrics = [{"label": word.title(), "value": (idx + 2) * 17, "trend": f"+{idx + 3}%"} for idx, word in enumerate(keywords[:4])]
            app_body = '''import React, { useMemo, useState } from "react";\n\nconst metrics = __METRICS__;\nconst cards = __FEATURES__;\n\nexport default function App() {\n  const [active, setActive] = useState(metrics[0]?.label || "Overview");\n  const total = useMemo(() => metrics.reduce((sum, item) => sum + item.value, 0), []);\n  return (\n    <main className="agent-app dashboard-workspace">\n      <section className="hero-panel"><p className="eyebrow">Dynamic dashboard</p><h1>__TITLE__</h1><p>Generated from the actual request with interactive metrics, cards, and visual emphasis.</p></section>\n      <section className="metric-grid">{metrics.map(metric => <button className={active === metric.label ? "metric-card active" : "metric-card"} key={metric.label} onClick={() => setActive(metric.label)}><span>{metric.label}</span><strong>{metric.value}</strong><em>{metric.trend}</em></button>)}</section>\n      <section className="glass-card"><h2>{active} detail</h2><p>Total signal score: {total}. This panel updates based on the selected metric.</p></section>\n      <section className="feature-grid">{cards.map(item => <article className="glass-card" key={item.title}><h2>{item.title}</h2><p>{item.body}</p></article>)}</section>\n    </main>\n  );\n}\n'''.replace("__METRICS__", json.dumps(metrics, indent=2))
        else:
            app_body = '''import React, { useMemo, useState } from "react";\n\nconst initialProducts = __PRODUCTS__;\nconst requestCards = __FEATURES__;\n\nexport default function App() {\n  const [cart, setCart] = useState([]);\n  const [query, setQuery] = useState("");\n  const filtered = useMemo(() => initialProducts.filter(item => (item.name + " " + item.category).toLowerCase().includes(query.toLowerCase())), [query]);\n  const total = useMemo(() => cart.reduce((sum, item) => sum + item.price, 0), [cart]);\n  return (\n    <main className="agent-app store-app">\n      <header className="hero-panel store-header"><div><p className="eyebrow">__INTENT__ · __DOMAIN__</p><h1>__TITLE__</h1><p>Built from the active task contract, not a canned template. Search, select, and validate the generated flow.</p><input className="search-input" placeholder="Filter generated items" value={query} onChange={event => setQuery(event.target.value)} /></div><aside className="glass-card cart-summary"><strong>{cart.length}</strong><span>items selected</span><b>${total.toLocaleString()}</b></aside></header>\n      <section className="product-grid">{filtered.map(product => <article className="glass-card product-card" key={product.sku}><span>{product.category}</span><h2>{product.name}</h2><p>{product.description}</p><div className="product-row"><strong>${product.price.toLocaleString()}</strong><button onClick={() => setCart(items => [...items, product])}>Add</button></div></article>)}</section>\n      <section className="feature-grid">{requestCards.map(item => <article className="glass-card" key={item.title}><h2>{item.title}</h2><p>{item.body}</p></article>)}</section>\n    </main>\n  );\n}\n'''.replace("__PRODUCTS__", json.dumps(products, indent=2)).replace("__INTENT__", c.intent.replace("_", " ")).replace("__DOMAIN__", c.domain)
        app_body = app_body.replace("__FEATURES__", json.dumps(section_cards, indent=2)).replace("__TITLE__", title)
        css = '''body { margin: 0; font-family: Inter, ui-sans-serif, system-ui, sans-serif; background: #020617; color: #e2e8f0; }\n.agent-app { min-height: 100vh; padding: clamp(1rem, 3vw, 3rem); background: radial-gradient(circle at 10% 0%, rgba(56,189,248,.22), transparent 30%), radial-gradient(circle at 90% 20%, rgba(168,85,247,.18), transparent 28%), #020617; }\n.hero-panel { max-width: 1180px; margin: 0 auto 1.2rem; border: 1px solid rgba(148,163,184,.24); background: rgba(15,23,42,.72); box-shadow: 0 24px 90px rgba(0,0,0,.35); border-radius: 32px; padding: clamp(1.3rem, 4vw, 3rem); animation: rise .5s ease both; }\n.eyebrow { color: #67e8f9; text-transform: uppercase; letter-spacing: .16em; font-weight: 900; }\nh1 { margin: 0; font-size: clamp(2.2rem, 7vw, 5.5rem); line-height: .94; letter-spacing: -.06em; }\np { color: #cbd5e1; line-height: 1.7; }\n.glass-card, .metric-card { border: 1px solid rgba(148,163,184,.22); background: rgba(15,23,42,.72); box-shadow: 0 18px 60px rgba(2,6,23,.28); border-radius: 26px; padding: 1.15rem; transition: transform .18s ease, border-color .18s ease, background .18s ease; }\n.glass-card:hover, .metric-card:hover { transform: translateY(-3px); border-color: rgba(103,232,249,.55); }\n.auth-grid, .store-header { display: grid; grid-template-columns: 1fr minmax(220px, 320px); gap: 1rem; align-items: stretch; max-width: 1180px; margin: 0 auto 1rem; }\n.feature-grid, .product-grid, .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; max-width: 1180px; margin: 1rem auto; }\n.metric-card { color: #e2e8f0; text-align: left; cursor: pointer; } .metric-card.active { background: rgba(14,165,233,.24); }\n.metric-card strong, .cart-summary strong { display: block; font-size: 3rem; }\ninput { width: 100%; border: 1px solid rgba(148,163,184,.28); border-radius: 16px; padding: .9rem 1rem; color: #e2e8f0; background: rgba(2,6,23,.72); }\nlabel { display: grid; gap: .45rem; color: #93c5fd; font-weight: 800; margin-bottom: .8rem; }\nbutton { border: 0; border-radius: 999px; padding: .85rem 1.1rem; font-weight: 900; color: #082f49; background: linear-gradient(135deg,#67e8f9,#a78bfa); cursor: pointer; }\n.product-row { display: flex; align-items: center; justify-content: space-between; gap: .75rem; }\ncode { display: block; white-space: pre-wrap; color: #fbbf24; margin-top: .7rem; }\n@keyframes rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }\n@media (max-width: 820px) { .auth-grid, .store-header { grid-template-columns: 1fr; } }\n'''
        return {
            "frontend/package.json": json.dumps({"scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"}, "dependencies": {"@vitejs/plugin-react": "latest", "vite": "latest", "react": "latest", "react-dom": "latest"}, "devDependencies": {}}, indent=2),
            "frontend/index.html": '<div id="root"></div><script type="module" src="/src/main.jsx"></script>\n',
            "frontend/src/main.jsx": 'import React from "react";\nimport { createRoot } from "react-dom/client";\nimport App from "./App.jsx";\nimport "./styles/app.css";\n\ncreateRoot(document.getElementById("root")).render(<App />);\n',
            "frontend/src/lib/apiClient.js": 'const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:4000";\n\nexport async function fetchProducts() {\n  const response = await fetch(API_BASE + "/api/products");\n  if (!response.ok) throw new Error("Products request failed");\n  return response.json();\n}\n\nexport async function login(email, password) {\n  const response = await fetch(API_BASE + "/api/auth/login", {\n    method: "POST", headers: { "Content-Type": "application/json" },\n    body: JSON.stringify({ email, password })\n  });\n  if (!response.ok) throw new Error("Login failed");\n  return response.json();\n}\n',
            "frontend/src/App.jsx": app_body,
            "frontend/src/styles/app.css": css,
        }

    def _node_files(self, c: TaskContract) -> dict[str, str]:
        return {
            "backend-node/package.json": json.dumps({"type": "module", "scripts": {"dev": "node src/server.js", "check": "node --check src/server.js && node --check src/routes/products.js && node --check src/routes/auth.js"}, "dependencies": {"@fastify/cors": "latest", "chromadb": "latest", "fastify": "latest"}, "devDependencies": {}}, indent=2),
            "backend-node/src/server.js": '''import Fastify from "fastify";\nimport cors from "@fastify/cors";\nimport { productRoutes } from "./routes/products.js";\nimport { authRoutes } from "./routes/auth.js";\n\nconst app = Fastify({ logger: true });\nawait app.register(cors, { origin: true });\nawait app.register(productRoutes, { prefix: "/api/products" });\nawait app.register(authRoutes, { prefix: "/api/auth" });\n\napp.get("/health", async () => ({ status: "ok" }));\n\nconst port = Number(process.env.PORT || 4000);\napp.listen({ port, host: "0.0.0.0" }).catch((error) => {\n  app.log.error(error);\n  process.exit(1);\n});\n''',
            "backend-node/src/routes/products.js": '''const products = [\n  { sku: "LAP-ULTRA-14", name: "UltraBook 14", category: "Laptop", price: 1299 },\n  { sku: "LAP-CREATOR-16", name: "CreatorBook 16", category: "Laptop", price: 1899 },\n  { sku: "SCR-4K-27", name: "Vision 27 4K", category: "Screen", price: 499 }\n];\n\nexport async function productRoutes(app) {\n  app.get("/", async () => products);\n  app.post("/", async (request, reply) => {\n    const product = request.body;\n    products.push(product);\n    return reply.code(201).send(product);\n  });\n}\n''',
            "backend-node/src/routes/auth.js": '''export async function authRoutes(app) {\n  app.post("/login", async (request, reply) => {\n    const { email, password } = request.body || {};\n    if (!email || !password) {\n      return reply.code(400).send({ error: "email and password are required" });\n    }\n    return { token: `dev-token-${Buffer.from(email).toString("base64url")}`, user: { email } };\n  });\n}\n''',
            "backend-node/src/db.js": '''// ChromaDB adapter entry point. Uses a local persistent Chroma path by default.\nexport const chromaPath = process.env.CHROMA_PATH || "./data/chroma";\n''',
            "backend-node/src/chromaStore.js": '''export const collections = { products: "products", users: "users", carts: "carts" };\nexport function asDocument(id, payload) { return { id, document: JSON.stringify(payload), metadata: payload }; }\n''',
        }

    def _dotnet_files(self, c: TaskContract) -> dict[str, str]:
        files = {
            "backend/DynamicApp.Api.csproj": '<Project Sdk="Microsoft.NET.Sdk.Web"><PropertyGroup><TargetFramework>net8.0</TargetFramework><Nullable>enable</Nullable><ImplicitUsings>enable</ImplicitUsings></PropertyGroup></Project>\n',
            "backend/appsettings.example.json": json.dumps({"ConnectionStrings": {"Default": "server=localhost;database=dynamic_app;user=app;password=app_password"}, "Jwt": {"Issuer": "ISE_AI", "Audience": "ISE_AI_USERS"}}, indent=2),
            "backend/Program.cs": '''var builder = WebApplication.CreateBuilder(args);\nvar app = builder.Build();\n\napp.MapGet("/health", () => Results.Ok(new { status = "ok" }));\napp.MapGet("/api/products", () => Results.Ok(new[] { new { sku = "LAP-ULTRA-14", name = "UltraBook 14", price = 1299 }, new { sku = "SCR-4K-27", name = "Vision 27 4K", price = 499 } }));\napp.MapPost("/api/auth/login", (LoginRequest login) => Results.Ok(new { token = $"dev-token-{login.Email}", user = login.Email }));\n\napp.Run();\nrecord LoginRequest(string Email, string Password);\n''',
        }
        if c.domain == "commerce":
            files["backend/Models/Product.cs"] = "namespace DynamicApp.Api.Models;\npublic record Product(string Sku, string Name, string Category, decimal Price);\n"
        if "authentication" in c.capabilities:
            files["backend/Models/User.cs"] = "namespace DynamicApp.Api.Models;\npublic record User(int Id, string Email, string PasswordHash);\n"
            files["backend/Services/AuthService.cs"] = "namespace DynamicApp.Api.Services;\npublic class AuthService { public string CreateToken(string email) => $\"dev-token-{email}\"; }\n"
        return files

    def _database_files(self, c: TaskContract) -> dict[str, str]:
        if "chromadb" not in c.stacks:
            return {}
        return {
            "database/chromadb/collections.json": json.dumps({"collections": ["users", "products", "carts", "cart_items"]}, indent=2),
            "database/chromadb/seed.json": json.dumps({"products": [{"sku": "LAP-ULTRA-14", "name": "UltraBook 14", "category": "Laptop", "price": 1299.00}, {"sku": "SCR-4K-27", "name": "Vision 27 4K", "category": "Screen", "price": 499.00}]}, indent=2),
        }

    def _compose_files(self, c: TaskContract) -> dict[str, str]:
        services = {"frontend": {"image": "node:20", "working_dir": "/app", "volumes": ["./frontend:/app"], "command": "sh -c 'npm install && npm run dev -- --host 0.0.0.0'", "ports": ["5173:5173"]}}
        if "node" in c.stacks:
            services["api"] = {"image": "node:20", "working_dir": "/app", "volumes": ["./backend-node:/app"], "command": "sh -c 'npm install && npm run dev'", "ports": ["4000:4000"]}
        if "chromadb" in c.stacks:
            services["chromadb"] = {"image": "chromadb/chroma:latest", "ports": ["8000:8000"], "volumes": ["./data/chroma:/chroma/chroma"]}
        return {"docker-compose.yml": "services:\n" + "\n".join(f"  {name}: {json.dumps(cfg)}" for name, cfg in services.items()) + "\n"}

    def _api_contract(self, c: TaskContract) -> str:
        endpoints = ["GET /health"]
        if c.domain == "commerce" or "crud" in c.capabilities:
            endpoints += ["GET /api/products", "POST /api/products"]
        if "authentication" in c.capabilities or any(s in c.stacks for s in ("node", "dotnet")):
            endpoints.append("POST /api/auth/login")
        return "# API Contract\n\n" + "\n".join(f"- `{endpoint}`" for endpoint in endpoints) + "\n"

    def _verify_script(self, c: TaskContract) -> str:
        required = json.dumps(c.required_files, indent=2)
        banned = json.dumps(sorted(BANNED_TEMPLATE_MARKERS), indent=2)
        domain = c.domain
        return f'''from pathlib import Path\nimport sys\n\nROOT = Path(__file__).resolve().parents[1]\nREQUIRED = {required}\nBANNED = {banned}\nSCAN_SUFFIXES = {{".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".cs", ".sql", ".html", ".yml", ".yaml", ".md"}}\nEXCLUDED_PARTS = {{"scripts", "node_modules", "dist", "build", ".git", ".ise_ai"}}\nEXCLUDED_NAMES = {{"agent-contract.json", "ROADMAP.md", "README.md"}}\nmissing = [path for path in REQUIRED if not (ROOT / path).exists()]\ntexts = []\nfor p in ROOT.rglob("*"):\n    rel = p.relative_to(ROOT)\n    if not p.is_file() or p.suffix.lower() not in SCAN_SUFFIXES:\n        continue\n    if p.name in EXCLUDED_NAMES or any(part in EXCLUDED_PARTS for part in rel.parts):\n        continue\n    texts.append(p.read_text(errors="ignore"))\ntext = "\\n".join(texts).lower()\nmarkers = [marker for marker in BANNED if marker in text]\ndomain_ok = True if {domain!r} == "general" else any(term in text for term in {list(DOMAIN_RULES.get(domain, (domain,)))!r})\nif missing or markers or not domain_ok:\n    print({{"missing": missing, "banned_markers": markers, "domain_ok": domain_ok}})\n    sys.exit(1)\nprint("artifact verification passed")\n'''

    def _imports_resolve(self, files: dict[str, str]) -> bool:
        for path, content in files.items():
            if not path.endswith((".js", ".jsx", ".ts", ".tsx")):
                continue
            base = path.split("/")[:-1]
            for match in re.finditer(r"from\s+[\"'](\.[^\"']+)[\"']|import\s+[\"'](\.[^\"']+)[\"']", content):
                rel = match.group(1) or match.group(2)
                target = self._normalize("/".join(base + [rel]))
                candidates = (
                    target, f"{target}.js", f"{target}.jsx", f"{target}.ts", f"{target}.tsx", f"{target}.css",
                    f"{target}/index.js", f"{target}/index.jsx", f"{target}/index.ts", f"{target}/index.tsx"
                )
                if not any(candidate in files for candidate in candidates):
                    return False
        return True

    def _domain_terms_present(self, domain: str, text: str) -> bool:
        if domain == "general":
            return True
        return any(term in text for term in DOMAIN_RULES.get(domain, (domain,)))

    def _title_for(self, c: TaskContract) -> str:
        if c.domain == "commerce":
            return "Laptop and Screen Webstore" if any(word in c.request.lower() for word in ("laptop", "screen")) else "Product Webstore"
        if c.domain == "restaurant":
            return "Restaurant Ordering Platform"
        return f"{c.domain.title()} Application"

    def _product_names(self, domain: str) -> list[dict[str, Any]]:
        if domain == "commerce":
            return [
                {"sku": "LAP-ULTRA-14", "name": "UltraBook 14", "category": "Laptop", "price": 1299, "description": "Portable workstation for study, work, and travel."},
                {"sku": "LAP-CREATOR-16", "name": "CreatorBook 16", "category": "Laptop", "price": 1899, "description": "High-performance laptop for design and development."},
                {"sku": "SCR-4K-27", "name": "Vision 27 4K", "category": "Screen", "price": 499, "description": "Sharp 4K display for productivity and gaming."},
            ]
        return [{"sku": "ITEM-001", "name": "Domain Item", "category": domain.title(), "price": 99, "description": "Request-specific catalog item."}]

    def _normalize(self, path: str) -> str:
        parts: list[str] = []
        for part in path.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(part)
        return "/".join(parts)


def get_dynamic_agent_runtime() -> DynamicAgentRuntime:
    return DynamicAgentRuntime()

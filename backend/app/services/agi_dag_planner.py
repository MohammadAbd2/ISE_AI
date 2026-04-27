from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass
class DAGStep:
    id: str
    agent: str
    title: str
    depends_on: list[str]
    success_condition: str
    outputs: list[str]

    def to_dict(self):
        return asdict(self)

class DAGPlanner:
    def build(self, contract: dict[str, Any], has_source: bool = False) -> list[DAGStep]:
        stacks = set(contract.get("stacks", []))
        steps: list[DAGStep] = []
        if has_source:
            steps.append(DAGStep("ingest", "IngestionAgent", "Copy project folder into isolated sandbox", [], "sandbox contains source files without recursive agent output", ["sandbox file index"]))
        base_dep = ["ingest"] if has_source else []
        steps.append(DAGStep("plan", "PlannerAgent", "Create typed roadmap, task contract, and file graph", base_dep, "contract and docs exist", ["docs/ROADMAP.md", "agent-contract.json"]))
        if "react" in stacks:
            steps.append(DAGStep("frontend", "FrontendAgent", "Create or update React frontend", ["plan"], "React entry, App, styles and API client exist", ["frontend/src/App.jsx"]))
        if {"node", "dotnet", "python"} & stacks:
            steps.append(DAGStep("backend", "BackendAgent", "Create or update backend/API", ["plan"], "backend health route and requested routes exist", ["backend-node/src/server.js", "backend/Program.cs"]))
        if "chromadb" in stacks:
            steps.append(DAGStep("database", "DatabaseAgent", "Create or update ChromaDB collections", ["backend" if {"node", "dotnet"} & stacks else "plan"], "ChromaDB collections and seed data exist", ["database/chromadb/collections.json", "database/chromadb/seed.json"]))
        steps.append(DAGStep("verify", "VerifierAgent", "Run import, stack, anti-template and build checks", [s.id for s in steps if s.id != "ingest"], "all export gates pass", ["verification-report.json"]))
        steps.append(DAGStep("repair", "RepairAgent", "Repair failed checks and rerun validation", ["verify"], "failed gates are fixed or escalated with evidence", ["repair-evidence.json"]))
        if "react" in stacks:
            steps.append(DAGStep("preview", "PreviewAgent", "Create real preview lifecycle contract", ["repair"], "preview command and URL are derived from real frontend", ["preview-contract.json"]))
        steps.append(DAGStep("export", "ExportAgent", "Create verified downloadable ZIP", ["repair"], "ZIP blocked unless validation passed", ["AGI_Output/run.zip"]))
        return steps

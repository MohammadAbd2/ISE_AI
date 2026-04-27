
from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class DeploymentAdvice:
    target: str
    files: list[str]
    commands: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DeploymentTargetRegistry:
    def list_targets(self) -> list[dict[str, Any]]:
        return [
            {"id": "vercel", "name": "Vercel", "best_for": "React/Vite frontend apps"},
            {"id": "netlify", "name": "Netlify", "best_for": "static frontend deployments"},
            {"id": "docker", "name": "Docker", "best_for": "full-stack portable apps"},
            {"id": "github", "name": "GitHub", "best_for": "version control and collaboration"},
        ]

    def advice(self, target: str, project_dir: str | Path) -> dict[str, Any]:
        target = (target or "vercel").lower()
        project = Path(project_dir).expanduser().resolve()
        if target == "docker":
            return DeploymentAdvice(
                target="docker",
                files=["Dockerfile", ".dockerignore"],
                commands=["docker build -t generated-app .", "docker run -p 3000:3000 generated-app"],
                notes=["Generate Dockerfile only after project structure is finalized.", f"Project: {project}"],
            ).to_dict()
        if target == "netlify":
            return DeploymentAdvice(target="netlify", files=["netlify.toml"], commands=["npm run build"], notes=["Publish frontend/dist for Vite apps."]).to_dict()
        if target == "github":
            return DeploymentAdvice(target="github", files=["README.md", ".gitignore"], commands=["git init", "git add .", "git commit -m initial"], notes=["Push only after user approval."]).to_dict()
        return DeploymentAdvice(target="vercel", files=["vercel.json"], commands=["npm run build"], notes=["Use Vite output directory: dist."]).to_dict()


@lru_cache
def get_deployment_registry() -> DeploymentTargetRegistry:
    return DeploymentTargetRegistry()

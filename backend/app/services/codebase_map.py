from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re

from app.core.config import settings


@dataclass(slots=True)
class CodebaseMapService:
    project_root: Path

    def build_map(self) -> dict:
        backend_api = self._collect_files("backend/app/api", "*.py")
        backend_services = self._collect_files("backend/app/services", "*.py")
        frontend_components = self._collect_files("frontend/src/components", "*.jsx")
        frontend_lib = self._collect_files("frontend/src/lib", "*.js")
        docs = self._collect_files("docs", "*.md")
        tests = self._collect_files("tests", "*.py")

        main_routes = self._extract_fastapi_routes()

        return {
            "root": str(self.project_root),
            "summary": {
                "backend_api_files": len(backend_api),
                "backend_service_files": len(backend_services),
                "frontend_component_files": len(frontend_components),
                "frontend_lib_files": len(frontend_lib),
                "docs_files": len(docs),
                "test_files": len(tests),
                "registered_route_modules": len(main_routes["modules"]),
            },
            "backend": {
                "api_files": backend_api[:20],
                "service_files": backend_services[:24],
                "route_modules": main_routes["modules"],
                "route_import_failures": main_routes["failures"],
            },
            "frontend": {
                "component_files": frontend_components[:20],
                "lib_files": frontend_lib[:20],
                "key_views": [
                    path for path in frontend_components
                    if Path(path).name in {"ChatLayout.jsx", "DashboardView.jsx", "MessageList.jsx", "DocumentationView.jsx"}
                ],
            },
            "docs": {
                "files": docs[:24],
                "developer_handbook_present": "docs/ISE_DEVELOPER_HANDBOOK.md" in docs,
            },
            "tests": {
                "files": tests[:24],
            },
        }

    def build_prompt_context(self) -> list[str]:
        codebase_map = self.build_map()
        summary = codebase_map["summary"]
        backend = codebase_map["backend"]
        frontend = codebase_map["frontend"]
        docs = codebase_map["docs"]

        return [
            "Codebase map:",
            (
                f"Backend API files: {summary['backend_api_files']}, backend services: {summary['backend_service_files']}, "
                f"frontend components: {summary['frontend_component_files']}, frontend libs: {summary['frontend_lib_files']}, "
                f"docs: {summary['docs_files']}, tests: {summary['test_files']}."
            ),
            "Registered FastAPI route modules: " + ", ".join(backend["route_modules"][:12]),
            "Key frontend views: " + ", ".join(frontend["key_views"][:8]),
            "Key documentation files: " + ", ".join(docs["files"][:8]),
        ]

    def _collect_files(self, relative_dir: str, pattern: str) -> list[str]:
        root = self.project_root / relative_dir
        if not root.exists():
            return []
        return sorted(
            str(path.relative_to(self.project_root))
            for path in root.rglob(pattern)
            if path.is_file()
        )

    def _extract_fastapi_routes(self) -> dict:
        main_path = self.project_root / "backend/app/main.py"
        if not main_path.exists():
            return {"modules": [], "failures": []}

        content = main_path.read_text(encoding="utf-8")
        modules = []
        failures = []

        for match in re.finditer(r"from app\.api\.(\w+) import router as (\w+)", content):
            modules.append(match.group(1))

        for match in re.finditer(r'Could not load ([^"]+)', content):
            failures.append(match.group(1))

        return {
            "modules": sorted(dict.fromkeys(modules)),
            "failures": sorted(dict.fromkeys(failures)),
        }


@lru_cache
def get_codebase_map_service() -> CodebaseMapService:
    return CodebaseMapService(project_root=settings.project_root)

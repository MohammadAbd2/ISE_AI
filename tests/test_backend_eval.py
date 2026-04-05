import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from backend.app.services.documents import DocumentService
from backend.app.services.intent_classifier import IntentClassifier
from backend.app.services.intelligent_coding_agent import IntelligentCodingAgent
from backend.app.services.orchestrator import CodingAgent
from backend.app.services.planning_agent import AutonomousPlanningAgent
from backend.app.services.capability_registry import CapabilityRegistry
from backend.app.services.dynamic_tool_registry import DynamicToolRegistry
from backend.app.services.session_analytics import build_session_analytics_payload
from backend.app.services.search import SearchService
from backend.app.core.config import settings
from backend.app.services.orchestrator import CapabilityAgent, OrchestratorResult
from backend.app.schemas.chat import ArtifactSummary
from backend.app.schemas.chat import SearchSource, WebSearchLog


class _DummyService:
    pass


class BackendEvalTests(unittest.TestCase):
    def setUp(self):
        self.intent = IntentClassifier()
        self.documents = DocumentService(_DummyService(), _DummyService())
        self.coding_agent = IntelligentCodingAgent()
        self.planning_agent = AutonomousPlanningAgent()
        self.search = SearchService(_DummyService(), None)

    def test_visualization_request_stays_out_of_agent_mode(self):
        result = self.intent.classify("create a 2d chart with random 1 year salary", "auto")
        self.assertEqual(result.kind, "visualization")
        self.assertFalse(result.use_agent)

    def test_coding_request_uses_agent_mode(self):
        result = self.intent.classify("create file frontend/src/components/Hello.jsx", "auto")
        self.assertEqual(result.kind, "coding")
        self.assertTrue(result.use_agent)

    def test_project_request_uses_project_context(self):
        result = self.intent.classify("read the uploaded project zip and analyze the codebase", "auto")
        self.assertEqual(result.kind, "project_analysis")
        self.assertTrue(result.use_project_context)

    def test_search_query_variants_add_freshness_and_site_bias(self):
        variants = self.search._build_query_variants(
            "latest vite docs on vitejs.dev",
            "latest vite docs site:vitejs.dev",
        )
        self.assertEqual(variants[0], "latest vite docs site:vitejs.dev")
        self.assertTrue(any("current" in variant or "latest" in variant for variant in variants))
        self.assertTrue(any("site:vitejs.dev" in variant for variant in variants))

    def test_search_query_preparation_preserves_requested_site(self):
        prepared = self.search._prepare_query("search on the web for vite config on vitejs.dev")
        self.assertIn("site:vitejs.dev", prepared)

    def test_search_render_blocks_include_source_cards(self):
        log = WebSearchLog(
            query="latest vite release",
            searched_at="2024-01-01T00:00:00+00:00",
            provider="duckduckgo+bing",
            summary="Collected current release notes.",
            sources=[
                SearchSource(
                    title="Vite release notes",
                    url="https://vitejs.dev/releases",
                    snippet="Latest release details",
                    domain="vitejs.dev",
                )
            ],
        )
        blocks = self.search.build_render_blocks(log)
        self.assertEqual(blocks[0]["type"], "research_result")
        self.assertEqual(blocks[1]["type"], "report")
        self.assertEqual(blocks[2]["type"], "file_result")
        self.assertTrue(any("latest" in item or "current" in item for item in blocks[0]["payload"]["query_plan"]))
        self.assertIn(blocks[0]["payload"]["confidence"], {"low", "medium", "high"})
        self.assertIn("vitejs.dev", blocks[1]["payload"]["highlights"])
        self.assertEqual(blocks[2]["payload"]["files"][0]["path"], "https://vitejs.dev/releases")

    def test_research_artifact_metadata_and_content_include_ranked_summary(self):
        log = WebSearchLog(
            query="latest vite release",
            searched_at="2024-01-01T00:00:00+00:00",
            provider="duckduckgo+bing",
            summary="Collected current release notes.",
            sources=[
                SearchSource(
                    title="Vite release notes",
                    url="https://vitejs.dev/releases",
                    snippet="Latest release details from March 15, 2026",
                    domain="vitejs.dev",
                )
            ],
        )
        variants = ["latest vite release", "latest vite release current"]
        metadata = self.search._build_research_metadata(log, variants)
        content = self.search._build_research_artifact_content(log, variants)
        self.assertEqual(metadata["query_variants"], variants)
        self.assertEqual(metadata["provider"], "duckduckgo+bing")
        self.assertIn("confidence", metadata)
        self.assertIn("Freshness:", content)
        self.assertIn("Query plan:", content)
        self.assertIn("https://vitejs.dev/releases", content)

    def test_search_conflict_detection_flags_numeric_disagreement(self):
        sources = [
            SearchSource(title="Source A", url="https://a.test", snippet="Price is $100", domain="a.test"),
            SearchSource(title="Source B", url="https://b.test", snippet="Price is $135", domain="b.test"),
        ]
        conflict = self.search._detect_numeric_conflict(sources)
        self.assertIn("Potential source conflict", conflict)

    def test_search_freshness_and_confidence_inference(self):
        sources = [
            SearchSource(
                title="Official update 2026",
                url="https://docs.example.com/update",
                snippet="Updated in 2026 with current release notes",
                domain="docs.example.com",
            ),
            SearchSource(
                title="Backup source",
                url="https://example.gov/report",
                snippet="2025 overview",
                domain="example.gov",
            ),
        ]
        freshness = self.search._estimate_freshness(sources)
        confidence = self.search._estimate_confidence(sources, "")
        self.assertIn("2026", freshness)
        self.assertEqual(confidence, "high")

    def test_search_extract_source_datetime_supports_full_dates(self):
        source = SearchSource(
            title="Release notes",
            url="https://example.com/release",
            snippet="Updated March 15, 2026 with new details",
            domain="example.com",
        )
        parsed = self.search._extract_source_datetime(source)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.year, 2026)
        self.assertEqual(parsed.month, 3)
        self.assertEqual(parsed.day, 15)

    def test_search_freshness_scoring_prefers_recent_source(self):
        recent_score = self.search._score_result(
            "Release notes",
            "https://docs.example.com/release",
            "Updated March 15, 2026 with latest release notes",
            "latest release notes",
            [],
            True,
        )
        older_score = self.search._score_result(
            "Release notes",
            "https://docs.example.com/release",
            "Updated March 15, 2022 with release notes",
            "latest release notes",
            [],
            True,
        )
        self.assertGreater(recent_score, older_score)

    def test_archive_extraction_detects_frameworks(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(
                "package.json",
                json.dumps(
                    {
                        "dependencies": {"react": "^18.0.0"},
                        "devDependencies": {"vite": "^5.0.0"},
                    }
                ),
            )
            archive.writestr("src/App.jsx", "export default function App() { return <div>Hello</div>; }")

        extracted, metadata = self.documents._extract_archive(buffer.getvalue(), "project.zip")
        self.assertIn("Detected frameworks: React, Vite", extracted)
        self.assertIn("FILE: package.json", extracted)
        self.assertIn("FILE: src/App.jsx", extracted)
        self.assertIn("React", metadata["frameworks"])
        self.assertIn("Vite", metadata["frameworks"])
        self.assertIn("package.json", metadata["important_configs"])

    def test_verification_commands_follow_project_layout(self):
        commands = self.coding_agent._build_verification_commands(
            ["frontend/src/components/Hello.jsx", "backend/app/api/users.py"]
        )
        self.assertIn("cd frontend && npm run build", commands)
        self.assertIn("python -m compileall backend/app", commands)

    def test_existing_file_edit_generates_diff(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = IntelligentCodingAgent(Path(temp_dir))
            target = Path(temp_dir) / "frontend" / "src" / "utils" / "logger.js"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("export function log() {\n  return true;\n}\n", encoding="utf-8")

            context = {
                "language": "javascript",
                "framework": None,
                "task_intent": "edit_file",
                "component_name": "Logger",
                "file_path": "frontend/src/utils/logger.js",
                "message_content": "Hello World",
                "summary": "Language: javascript, Intent: edit_file",
            }
            file_ops = self._run(agent._determine_files("update file frontend/src/utils/logger.js and add console.log \"Hello World\"", context))
            self.assertEqual(file_ops[0]["operation"], "edit")
            success, _, diff = self._run(agent._apply_file_operation(file_ops[0]))
            self.assertTrue(success)
            self.assertIn('console.log("Hello World");', target.read_text(encoding="utf-8"))
            self.assertIn("+++ frontend/src/utils/logger.js", diff)

    def test_identifier_normalization_strips_extensions(self):
        agent = IntelligentCodingAgent()
        self.assertEqual(agent._normalize_identifier("Hello.jsx"), "HelloJsx")
        self.assertEqual(agent._normalize_identifier("my-component"), "MyComponent")

    def test_repair_rewrites_invalid_export_identifier(self):
        agent = IntelligentCodingAgent()
        broken = "const Hello.jsx = () => null;\nexport default Hello.jsx;\n"
        repaired = agent._repair_file_content("frontend/src/components/Hello.jsx", broken, {})
        self.assertIn("const HelloJsx = () => null;", repaired)
        self.assertIn("export default HelloJsx;", repaired)

    def test_find_existing_target_prefers_project_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = IntelligentCodingAgent(Path(temp_dir))
            target = Path(temp_dir) / "frontend" / "src" / "components" / "Navbar.jsx"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("export default function Navbar() { return null; }\n", encoding="utf-8")
            resolved = agent._find_existing_target(
                "update the navbar component to add a link",
                {"component_name": "Navbar", "language": "javascript"},
            )
            self.assertEqual(resolved, "frontend/src/components/Navbar.jsx")

    def test_react_nav_edit_inserts_link(self):
        agent = IntelligentCodingAgent()
        content = "export default function Navbar() {\n  return <nav>\n  </nav>;\n}\n"
        updated = agent._edit_javascript_content(
            "update navbar to add link \"Dashboard\"",
            "Dashboard",
            content,
            "frontend/src/components/Navbar.jsx",
        )
        self.assertIn('<a href="/dashboard">Dashboard</a>', updated)

    def test_fastapi_edit_inserts_route(self):
        agent = IntelligentCodingAgent()
        content = 'from fastapi import APIRouter\n\nrouter = APIRouter()\n'
        updated = agent._edit_python_content(
            "add endpoint status",
            "Get status",
            content,
            "backend/app/api/status.py",
        )
        self.assertIn('@router.get("/api/status")', updated)
        self.assertIn("async def get_status()", updated)

    def test_create_api_also_registers_router_in_main(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_path = root / "backend" / "app" / "main.py"
            main_path.parent.mkdir(parents=True, exist_ok=True)
            main_path.write_text(
                "from backend.app.api.routes import router\n"
                "from backend.app.api.evolution_routes import evolution_router\n"
                "from backend.app.core.config import settings\n\n"
                "app = object()\n"
                "app.include_router(router)\n"
                "app.include_router(evolution_router)\n",
                encoding="utf-8",
            )

            agent = IntelligentCodingAgent(root)
            context = {
                "language": "python",
                "framework": "fastapi",
                "task_intent": "create_api",
                "component_name": "Status",
                "file_path": "backend/app/api/status.py",
                "message_content": "Get status",
                "summary": "Language: python, Framework: fastapi, Intent: create_api",
            }
            files = self._run(agent._determine_files("create api status", context))
            paths = [item["path"] for item in files]
            self.assertIn("backend/app/api/status.py", paths)
            self.assertIn("backend/app/main.py", paths)
            main_update = next(item for item in files if item["path"] == "backend/app/main.py")
            self.assertIn("from backend.app.api.status import router as status_router", main_update["content"])
            self.assertIn("app.include_router(status_router)", main_update["content"])

    def test_create_dashboard_component_registers_in_dashboard_view(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dashboard_path = root / "frontend" / "src" / "components" / "DashboardView.jsx"
            dashboard_path.parent.mkdir(parents=True, exist_ok=True)
            dashboard_path.write_text(
                'import FeaturesPanel from "./FeaturesPanel";\n'
                'import DynamicVisualization from "./DynamicVisualization";\n'
                'import { artifactDownloadUrl } from "../lib/api";\n\n'
                "export default function DashboardView() {\n"
                "  return (\n"
                "    <div className=\"dashboard-view\">\n"
                "      <ArtifactPanel artifacts={artifacts} />\n"
                "    </div>\n"
                "  );\n"
                "}\n",
                encoding="utf-8",
            )

            agent = IntelligentCodingAgent(root)
            update = self._run(
                agent._build_frontend_component_registration(
                    "frontend/src/components/InsightsPanel.jsx",
                    "create a dashboard component called InsightsPanel",
                )
            )
            self.assertIsNotNone(update)
            self.assertIn('import InsightsPanel from "./InsightsPanel";', update["content"])
            self.assertIn("<InsightsPanel />", update["content"])

    def test_project_context_biases_framework_detection(self):
        agent = IntelligentCodingAgent()
        context = agent._understand_task(
            "create a dashboard component called InsightsPanel",
            {"frameworks": ["React", "Vite"]},
        )
        self.assertEqual(context["language"], "javascript")
        self.assertEqual(context["framework"], "react")

    def test_workspace_view_task_uses_workspace_intent(self):
        agent = IntelligentCodingAgent()
        context = agent._understand_task(
            "create a new workspace view called InsightsPanel",
            {"frameworks": ["React", "Vite"]},
        )
        self.assertEqual(context["task_intent"], "create_workspace_view")
        self.assertEqual(context["file_path"], None)

    def test_dashboard_tool_task_uses_dashboard_tool_intent(self):
        agent = IntelligentCodingAgent()
        context = agent._understand_task(
            "create a dashboard tool called Finance Monitor",
            {"frameworks": ["React", "Vite"]},
        )
        self.assertEqual(context["task_intent"], "create_dashboard_tool")

    def test_analytics_dashboard_task_uses_analytics_intent(self):
        agent = IntelligentCodingAgent()
        context = agent._understand_task(
            "create an analytics dashboard for profit charts",
            {"frameworks": ["React", "Vite"]},
        )
        self.assertEqual(context["task_intent"], "create_analytics_dashboard")

    def test_planning_agent_builds_project_aware_frontend_plan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dashboard_path = root / "frontend" / "src" / "components" / "DashboardView.jsx"
            dashboard_path.parent.mkdir(parents=True, exist_ok=True)
            dashboard_path.write_text(
                'import { artifactDownloadUrl } from "../lib/api";\n\n'
                "export default function DashboardView() {\n"
                "  return (\n"
                "    <div className=\"dashboard-view\">\n"
                "      <ArtifactPanel artifacts={artifacts} />\n"
                "    </div>\n"
                "  );\n"
                "}\n",
                encoding="utf-8",
            )

            agent = AutonomousPlanningAgent(root)
            plan = self._run(
                agent.create_plan(
                    "create a dashboard component called InsightsPanel for the dashboard",
                    {"frameworks": ["React", "Vite"]},
                )
            )

            targets = [step.target for step in plan.steps]
            self.assertIn("frontend/src/components/InsightsPanel.jsx", targets)
            self.assertIn("frontend/src/components/DashboardView.jsx", targets)
            self.assertIn("cd frontend && npm run build", targets)
            self.assertNotIn("output.txt", targets)

    def test_planning_agent_enriches_explicit_verify_step(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dashboard_path = root / "frontend" / "src" / "components" / "DashboardView.jsx"
            dashboard_path.parent.mkdir(parents=True, exist_ok=True)
            dashboard_path.write_text(
                'import { artifactDownloadUrl } from "../lib/api";\n\n'
                "export default function DashboardView() {\n"
                "  return (\n"
                "    <div className=\"dashboard-view\">\n"
                "      <ArtifactPanel artifacts={artifacts} />\n"
                "    </div>\n"
                "  );\n"
                "}\n",
                encoding="utf-8",
            )

            agent = AutonomousPlanningAgent(root)
            plan = self._run(
                agent.create_plan(
                    "create a dashboard component called InsightsPanel then verify it",
                    {"frameworks": ["React", "Vite"]},
                )
            )

            self.assertEqual(plan.steps[0].target, "frontend/src/components/InsightsPanel.jsx")
            self.assertEqual(plan.steps[1].action_type, "run_command")
            self.assertEqual(plan.steps[1].target, "cd frontend && npm run build")

    def test_coding_render_blocks_include_plan_result(self):
        agent = CodingAgent.__new__(CodingAgent)
        blocks = CodingAgent._build_render_blocks(
            agent,
            "create and verify dashboard component",
            [{"path": "frontend/src/components/InsightsPanel.jsx", "summary": "Create component"}],
            "completed",
            plan_steps=[
                {
                    "step_number": 1,
                    "description": "Create component",
                    "status": "completed",
                    "target": "frontend/src/components/InsightsPanel.jsx",
                    "output": "created",
                    "error": "",
                }
            ],
        )
        plan_block = next(block for block in blocks if block["type"] == "plan_result")
        self.assertEqual(plan_block["payload"]["status"], "completed")
        self.assertEqual(plan_block["payload"]["steps"][0]["target"], "frontend/src/components/InsightsPanel.jsx")

    def test_create_workspace_view_registers_app_and_layout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app_path = root / "frontend" / "src" / "App.jsx"
            app_path.parent.mkdir(parents=True, exist_ok=True)
            app_path.write_text(
                'import ChatLayout from "./components/ChatLayout";\n'
                'import MessageList from "./components/MessageList";\n\n'
                "export default function App() {\n"
                "  return (\n"
                "    <ChatLayout\n"
                "      activeView={activeView}\n"
                "      onViewChange={setActiveView}\n"
                "      chatContent={<div />}\n"
                "      dashboardContent={<div />}\n"
                "    />\n"
                "  );\n"
                "}\n",
                encoding="utf-8",
            )
            layout_path = root / "frontend" / "src" / "components" / "ChatLayout.jsx"
            layout_path.parent.mkdir(parents=True, exist_ok=True)
            layout_path.write_text(
                "export default function ChatLayout({\n"
                "  activeView,\n"
                "  onViewChange,\n"
                "  chatContent,\n"
                "  dashboardContent,\n"
                "}) {\n"
                "  return (\n"
                "    <div className=\"app-shell\">\n"
                "      <nav className=\"main-nav\">\n"
                "        <button type=\"button\" className={activeView === \"dashboard\" ? \"active\" : \"\"} onClick={() => onViewChange(\"dashboard\")}>\n"
                "          Dashboard\n"
                "        </button>\n"
                "        <button type=\"button\" className={activeView === \"chat\" ? \"active\" : \"\"} onClick={() => onViewChange(\"chat\")}>\n"
                "          Chat\n"
                "        </button>\n"
                "      </nav>\n"
                "      <main className=\"main-stage\">\n"
                "        {activeView === \"dashboard\" ? dashboardContent : chatContent}\n"
                "      </main>\n"
                "    </div>\n"
                "  );\n"
                "}\n",
                encoding="utf-8",
            )

            agent = IntelligentCodingAgent(root)
            context = {
                "language": "javascript",
                "framework": "react",
                "task_intent": "create_workspace_view",
                "component_name": "InsightsPanel",
                "file_path": "frontend/src/components/InsightsPanel.jsx",
                "message_content": None,
                "summary": "Language: javascript, Framework: react, Intent: create_workspace_view",
            }
            files = self._run(agent._determine_files("create a new workspace view called InsightsPanel", context))
            paths = [item["path"] for item in files]
            self.assertIn("frontend/src/components/InsightsPanel.jsx", paths)
            self.assertIn("frontend/src/App.jsx", paths)
            self.assertIn("frontend/src/components/ChatLayout.jsx", paths)

            app_update = next(item for item in files if item["path"] == "frontend/src/App.jsx")
            self.assertIn('import InsightsPanel from "./components/InsightsPanel";', app_update["content"])
            self.assertIn('extraViews={[', app_update["content"])
            self.assertIn('{ id: "insightspanel", label: "Insights Panel", content: <InsightsPanel /> }', app_update["content"])

            layout_update = next(item for item in files if item["path"] == "frontend/src/components/ChatLayout.jsx")
            self.assertIn("extraViews = []", layout_update["content"])
            self.assertIn("{extraViews.map((view) => (", layout_update["content"])
            self.assertIn('extraViews.find((view) => view.id === activeView)?.content ?? chatContent', layout_update["content"])

    def test_create_dashboard_tool_registers_component_and_registries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dashboard_path = root / "frontend" / "src" / "components" / "DashboardView.jsx"
            dashboard_path.parent.mkdir(parents=True, exist_ok=True)
            dashboard_path.write_text(
                'import { artifactDownloadUrl } from "../lib/api";\n\n'
                "export default function DashboardView() {\n"
                "  return (\n"
                "    <div className=\"dashboard-view\">\n"
                "      <ArtifactPanel artifacts={artifacts} />\n"
                "    </div>\n"
                "  );\n"
                "}\n",
                encoding="utf-8",
            )
            (root / ".evolution-tools.json").write_text("{}", encoding="utf-8")
            (root / ".evolution-registry.json").write_text("{}", encoding="utf-8")

            agent = IntelligentCodingAgent(root)
            context = {
                "language": "javascript",
                "framework": "react",
                "task_intent": "create_dashboard_tool",
                "component_name": "FinanceMonitor",
                "file_path": "frontend/src/components/FinanceMonitorTool.jsx",
                "message_content": None,
                "summary": "Language: javascript, Framework: react, Intent: create_dashboard_tool",
            }
            files = self._run(agent._determine_files("create a dashboard tool called Finance Monitor", context))
            paths = [item["path"] for item in files]
            self.assertIn("frontend/src/components/FinanceMonitorTool.jsx", paths)
            self.assertIn("frontend/src/components/DashboardView.jsx", paths)
            self.assertIn(".evolution-tools.json", paths)
            self.assertIn(".evolution-registry.json", paths)

            tool_update = next(item for item in files if item["path"] == ".evolution-tools.json")
            self.assertIn('"finance_monitor_tool"', tool_update["content"])
            self.assertIn('"category": "dashboard"', tool_update["content"])

            capability_update = next(item for item in files if item["path"] == ".evolution-registry.json")
            self.assertIn('"finance_monitor_tool"', capability_update["content"])
            self.assertIn('"kind": "dashboard_tool"', capability_update["content"])

    def test_create_analytics_dashboard_registers_workspace_and_uses_visualization_component(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dashboard_path = root / "frontend" / "src" / "components" / "DashboardView.jsx"
            dashboard_path.parent.mkdir(parents=True, exist_ok=True)
            dashboard_path.write_text(
                'import { artifactDownloadUrl } from "../lib/api";\n\n'
                "export default function DashboardView() {\n"
                "  return (\n"
                "    <div className=\"dashboard-view\">\n"
                "      <ArtifactPanel artifacts={artifacts} />\n"
                "    </div>\n"
                "  );\n"
                "}\n",
                encoding="utf-8",
            )
            app_path = root / "frontend" / "src" / "App.jsx"
            app_path.write_text(
                'import ChatLayout from "./components/ChatLayout";\n'
                'import MessageList from "./components/MessageList";\n\n'
                "export default function App() {\n"
                "  return (\n"
                "    <ChatLayout\n"
                "      activeView={activeView}\n"
                "      onViewChange={setActiveView}\n"
                "      chatContent={<div />}\n"
                "      dashboardContent={<div />}\n"
                "    />\n"
                "  );\n"
                "}\n",
                encoding="utf-8",
            )
            layout_path = root / "frontend" / "src" / "components" / "ChatLayout.jsx"
            layout_path.write_text(
                "export default function ChatLayout({\n"
                "  activeView,\n"
                "  onViewChange,\n"
                "  chatContent,\n"
                "  dashboardContent,\n"
                "}) {\n"
                "  return (\n"
                "    <div className=\"app-shell\">\n"
                "      <nav className=\"main-nav\">\n"
                "        <button type=\"button\" className={activeView === \"dashboard\" ? \"active\" : \"\"} onClick={() => onViewChange(\"dashboard\")}>\n"
                "          Dashboard\n"
                "        </button>\n"
                "        <button type=\"button\" className={activeView === \"chat\" ? \"active\" : \"\"} onClick={() => onViewChange(\"chat\")}>\n"
                "          Chat\n"
                "        </button>\n"
                "      </nav>\n"
                "      <main className=\"main-stage\">\n"
                '        {activeView === "dashboard" ? dashboardContent : chatContent}\n'
                "      </main>\n"
                "    </div>\n"
                "  );\n"
                "}\n",
                encoding="utf-8",
            )
            (root / ".evolution-tools.json").write_text("{}", encoding="utf-8")
            (root / ".evolution-registry.json").write_text("{}", encoding="utf-8")

            agent = IntelligentCodingAgent(root)
            context = {
                "language": "javascript",
                "framework": "react",
                "task_intent": "create_analytics_dashboard",
                "component_name": "ProfitInsights",
                "file_path": "frontend/src/components/ProfitInsightsDashboard.jsx",
                "message_content": None,
                "summary": "Language: javascript, Framework: react, Intent: create_analytics_dashboard",
            }
            files = self._run(agent._determine_files("create an analytics dashboard for profit charts", context))
            paths = [item["path"] for item in files]
            self.assertIn("frontend/src/components/ProfitInsightsDashboard.jsx", paths)
            self.assertIn("frontend/src/components/DashboardView.jsx", paths)
            self.assertIn("frontend/src/App.jsx", paths)
            self.assertIn("frontend/src/components/ChatLayout.jsx", paths)

            component = next(item for item in files if item["path"] == "frontend/src/components/ProfitInsightsDashboard.jsx")
            self.assertIn('import DynamicVisualization from "./DynamicVisualization";', component["content"])
            self.assertIn('import { buildVisualizationArtifacts } from "../lib/visualization";', component["content"])
            self.assertIn('import useSessionAnalytics from "../hooks/useSessionAnalytics";', component["content"])
            self.assertIn("<DynamicVisualization spec={activeSpec} />", component["content"])
            self.assertIn("sessionId = \"\"", component["content"])
            self.assertIn("useSessionAnalytics(sessionId", component["content"])
            self.assertIn("const renderBlocks = buildVisualizationArtifacts(activeSpec);", component["content"])

    def test_session_analytics_payload_prefers_latest_visualization_and_artifacts(self):
        session = {
            "id": "session-1",
            "messages": [
                type(
                    "Msg",
                    (),
                    {
                        "render_blocks": [
                            {
                                "type": "report",
                                "payload": {"title": "Older report"},
                            }
                        ]
                    },
                )(),
                type(
                    "Msg",
                    (),
                    {
                        "render_blocks": [
                            {
                                "type": "visualization",
                                "payload": {"type": "chart2d", "rows": [{"label": "Jan", "value": 10}]},
                            },
                            {
                                "type": "report",
                                "payload": {"title": "Latest report"},
                            },
                        ]
                    },
                )(),
            ],
        }
        artifacts = [
            ArtifactSummary(
                id="a1",
                session_id="session-1",
                kind="archive",
                title="project.zip",
                preview="archive",
                metadata={},
                created_at="2024-01-01T00:00:00+00:00",
                updated_at="2024-01-01T00:00:00+00:00",
            )
        ]
        payload = build_session_analytics_payload(session, artifacts)
        self.assertTrue(payload["has_context"])
        self.assertEqual(payload["visualization"]["type"], "chart2d")
        self.assertEqual(payload["render_blocks"][0].type, "visualization")
        self.assertEqual(payload["artifacts"][0].title, "project.zip")

    def test_capability_registry_merges_missing_builtins_into_existing_registry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original_root = settings.backend_root
            try:
                settings.backend_root = Path(temp_dir) / "backend" / "app"
                settings.backend_root.mkdir(parents=True, exist_ok=True)
                registry_path = settings.backend_root.parent / ".evolution-registry.json"
                registry_path.write_text(
                    json.dumps(
                        {
                            "text_generation": {
                                "name": "text_generation",
                                "description": "Generate text responses using language models",
                                "status": "available",
                                "version": "1.0.0",
                                "added_at": "2026-01-01T00:00:00+00:00",
                                "metadata": {"default": True},
                            }
                        }
                    ),
                    encoding="utf-8",
                )

                registry = CapabilityRegistry()
                names = {cap["name"] for cap in registry.list_capabilities()}
                self.assertIn("structured_artifacts", names)
                self.assertIn("dynamic_visualization", names)
                self.assertIn("research_memory", names)
                self.assertIn("analytics_dashboard_generation", names)
            finally:
                settings.backend_root = original_root

    def test_dynamic_tool_registry_merges_missing_builtins_into_existing_registry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original_root = settings.backend_root
            try:
                settings.backend_root = Path(temp_dir) / "backend" / "app"
                settings.backend_root.mkdir(parents=True, exist_ok=True)
                registry_path = settings.backend_root.parent / ".evolution-tools.json"
                registry_path.write_text(
                    json.dumps(
                        {
                            "read_file": {
                                "name": "read_file",
                                "description": "Read the contents of a file",
                                "function_ref": "tool_executor.read_file",
                                "parameters": {"path": {"type": "string", "description": "File path"}},
                                "return_type": "str",
                                "category": "file_io",
                                "version": "1.0.0",
                                "enabled": True,
                            }
                        }
                    ),
                    encoding="utf-8",
                )

                registry = DynamicToolRegistry()
                names = {tool["name"] for tool in registry.list_tools()}
                self.assertIn("web_research", names)
                self.assertIn("build_visualization", names)
                self.assertIn("session_analytics", names)
                self.assertIn("reopen_artifact", names)
                self.assertIn("list_directory", names)
                self.assertIn("analyze_imports", names)
                self.assertIn("session_history", names)
            finally:
                settings.backend_root = original_root

    def test_runtime_tool_executes_visualization_builder(self):
        registry = DynamicToolRegistry()
        result = self._run(
            registry.execute_tool_async(
                "build_visualization",
                prompt="create a 2d chart with random 1 year salary",
            )
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["spec"]["type"], "chart2d")
        self.assertEqual(result["render_blocks"][0]["type"], "visualization")

    def test_runtime_tool_can_reopen_research_artifact(self):
        artifact = {
            "id": "artifact-1",
            "session_id": "session-1",
            "kind": "research",
            "title": "Latest Vite Notes",
            "content": "Collected current release notes.",
            "metadata": {
                "query": "latest vite release",
                "provider": "duckduckgo+bing",
                "query_variants": ["latest vite release", "vite release current"],
                "confidence": "high",
                "freshness": "Likely current (2026)",
                "sources": [{"title": "Vite", "url": "https://vitejs.dev", "domain": "vitejs.dev"}],
            },
        }

        class FakeArtifacts:
            async def get_artifact(self, artifact_id: str):
                return artifact if artifact_id == "artifact-1" else None

        registry = DynamicToolRegistry()
        with patch("backend.app.services.dynamic_tool_registry.get_artifact_service", return_value=FakeArtifacts()):
            result = self._run(
                registry.execute_tool_async("reopen_artifact", artifact_id=artifact["id"], session_id="session-1")
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["render_blocks"][0]["type"], "research_result")
        self.assertEqual(result["render_blocks"][1]["type"], "report")

    def test_runtime_tool_returns_session_history(self):
        class FakeHistory:
            async def get_session(self, session_id: str):
                return {
                    "id": session_id,
                    "title": "Debug Session",
                    "messages": [
                        type("Msg", (), {"role": "user", "content": "hello"})(),
                        type("Msg", (), {"role": "assistant", "content": "hi there"})(),
                    ],
                }

        registry = DynamicToolRegistry()
        with patch("backend.app.services.dynamic_tool_registry.get_history_service", return_value=FakeHistory()):
            result = self._run(registry.execute_tool_async("session_history", session_id="session-1"))
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message_count"], 2)
        self.assertEqual(result["messages"][0]["role"], "user")

    def test_capability_agent_reopens_latest_research_memory(self):
        artifact = {
            "id": "artifact-1",
            "title": "Saved Research",
        }

        class FakeArtifacts:
            async def list_artifacts(self, session_id: str, kinds=None, limit: int = 1):
                return [artifact]

        async def fake_execute(tool_name: str, **kwargs):
            if tool_name == "reopen_artifact":
                return {
                    "render_blocks": [
                        {"type": "research_result", "payload": {"query": "latest vite"}},
                        {"type": "report", "payload": {"title": "Saved Research"}},
                    ]
                }
            raise AssertionError(f"Unexpected tool call: {tool_name}")

        agent = CapabilityAgent()
        agent.artifacts = FakeArtifacts()
        agent.registry.execute_tool_async = fake_execute
        result = self._run(agent.run("session-1", "open research memory"))
        self.assertEqual(result.direct_reply, "Reopened research memory: Saved Research")
        self.assertEqual(result.render_blocks[0]["type"], "research_result")

    def test_capability_agent_session_analytics_returns_render_blocks(self):
        async def fake_execute(tool_name: str, **kwargs):
            if tool_name == "session_analytics":
                return {
                    "visualization": {"type": "chart2d", "rows": [{"label": "Jan", "value": 10}]},
                    "render_blocks": [{"type": "report", "payload": {"title": "Latest report"}}],
                    "artifacts": [{"id": "a1"}],
                    "has_context": True,
                }
            raise AssertionError(f"Unexpected tool call: {tool_name}")

        agent = CapabilityAgent()
        agent.registry.execute_tool_async = fake_execute
        result = self._run(agent.run("session-1", "show session analytics"))
        self.assertEqual(result.direct_reply, "Loaded the latest session analytics context.")
        self.assertEqual(result.render_blocks[0]["type"], "visualization")
        self.assertEqual(result.render_blocks[-1]["type"], "report")

    def _run(self, coro):
        import asyncio
        return asyncio.run(coro)


if __name__ == "__main__":
    unittest.main()

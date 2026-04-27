from dataclasses import dataclass
from functools import lru_cache

from app.services.capability_registry import CapabilityRegistry
from app.services.documents import DocumentService, get_document_service
from app.services.eval_history import EvalHistoryService, get_eval_history_service
from app.services.intent_classifier import IntentClassifier, get_intent_classifier
from app.services.search import SearchService, get_search_service


@dataclass(slots=True)
class EvalCase:
    name: str
    prompt: str
    expected_kind: str | None = None
    expected_use_agent: bool | None = None
    expected_search: bool | None = None
    expected_docs: bool | None = None


class EvalService:
    def __init__(
        self,
        intent_classifier: IntentClassifier,
        search_service: SearchService,
        document_service: DocumentService,
        capability_registry: CapabilityRegistry | None = None,
        eval_history: EvalHistoryService | None = None,
    ) -> None:
        self.intent_classifier = intent_classifier
        self.search_service = search_service
        self.document_service = document_service
        self.capability_registry = capability_registry or CapabilityRegistry()
        self.eval_history = eval_history or get_eval_history_service()

    async def run_regression_suite(self) -> dict:
        cases = [
            EvalCase(
                name="small_talk_stays_chat",
                prompt="Hi, how are you today?",
                expected_kind="chat",
                expected_use_agent=False,
                expected_search=False,
                expected_docs=False,
            ),
            EvalCase(
                name="latest_docs_triggers_research",
                prompt="latest vite docs",
                expected_kind="research",
                expected_use_agent=False,
                expected_search=True,
                expected_docs=False,
            ),
            EvalCase(
                name="chart_request_stays_visualization",
                prompt="display random data in a 2d chart for me",
                expected_kind="visualization",
                expected_use_agent=False,
                expected_search=False,
                expected_docs=False,
            ),
            EvalCase(
                name="chart_component_escalates_to_agent",
                prompt="put the data in a 2d chart component in the frontend and render the result in the chat",
                expected_kind="coding",
                expected_use_agent=True,
                expected_search=False,
                expected_docs=False,
            ),
            EvalCase(
                name="self_development_loads_docs",
                prompt="How can you develop yourself now based on this project architecture?",
                expected_kind="chat",
                expected_use_agent=False,
                expected_search=False,
                expected_docs=True,
            ),
            EvalCase(
                name="project_analysis_uses_context",
                prompt="analyze the uploaded project zip and inspect the codebase",
                expected_kind="project_analysis",
                expected_use_agent=False,
                expected_search=False,
                expected_docs=False,
            ),
        ]

        results = []
        passed = 0

        for case in cases:
            intent = self.intent_classifier.classify(case.prompt, "auto")
            search = self.search_service.should_search(case.prompt)
            docs_context = await self.document_service.build_context(None, [], case.prompt)
            docs_loaded = any("Developer reference:" in block for block in docs_context)

            checks = []
            if case.expected_kind is not None:
                checks.append(("kind", intent.kind, case.expected_kind))
            if case.expected_use_agent is not None:
                checks.append(("use_agent", intent.use_agent, case.expected_use_agent))
            if case.expected_search is not None:
                checks.append(("should_search", search, case.expected_search))
            if case.expected_docs is not None:
                checks.append(("docs_loaded", docs_loaded, case.expected_docs))

            failures = [
                {
                    "field": field,
                    "actual": actual,
                    "expected": expected,
                }
                for field, actual, expected in checks
                if actual != expected
            ]
            ok = len(failures) == 0
            if ok:
                passed += 1

            results.append(
                {
                    "name": case.name,
                    "prompt": case.prompt,
                    "passed": ok,
                    "intent": {
                        "kind": intent.kind,
                        "use_agent": intent.use_agent,
                        "confidence": intent.confidence,
                    },
                    "should_search": search,
                    "docs_loaded": docs_loaded,
                    "failures": failures,
                }
            )

        contract_results = self._run_capability_contracts()
        passed_contracts = len([item for item in contract_results if item["passed"]])
        passed += passed_contracts
        total = len(results) + len(contract_results)
        score = round((passed / total) * 10, 2) if total else 0.0
        report = {
            "suite": "system_regression",
            "score": score,
            "passed": passed,
            "total": total,
            "sections": {
                "routing": {
                    "passed": len([item for item in results if item["passed"]]),
                    "total": len(results),
                },
                "contracts": {
                    "passed": passed_contracts,
                    "total": len(contract_results),
                },
            },
            "results": results,
            "contracts": contract_results,
        }
        self.eval_history.append(report)
        return report

    def _run_capability_contracts(self) -> list[dict]:
        required_capabilities = [
            "codebase_mapping",
            "regression_evaluation",
            "self_improvement_planning",
            "turn_diagnostics",
            "structured_memory_summary",
        ]
        results = []
        for capability_name in required_capabilities:
            capability = self.capability_registry.get_capability(capability_name)
            passed = capability is not None and capability.status.value == "available"
            results.append(
                {
                    "name": f"capability::{capability_name}",
                    "passed": passed,
                    "status": capability.status.value if capability else "missing",
                    "route": capability.metadata.get("route", "") if capability else "",
                    "dashboard_panel": capability.metadata.get("dashboard_panel", "") if capability else "",
                }
            )
        return results


@lru_cache
def get_eval_service() -> EvalService:
    return EvalService(
        intent_classifier=get_intent_classifier(),
        search_service=get_search_service(),
        document_service=get_document_service(),
    )

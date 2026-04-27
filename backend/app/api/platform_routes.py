from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.agent_observability import get_agent_trace_store
from app.services.no_template_verifier import NoTemplateVerifier
from app.services.preview_runtime import get_preview_registry
from app.services.reliability_suite import EndToEndReliabilitySuite

router = APIRouter()


class ReliabilitySmokeRequest(BaseModel):
    task: str = Field("generated React project", description="Task description to validate against")
    workspace: str | None = Field(None, description="Workspace path. Defaults to project root.")
    session_id: str = Field("reliability-smoke", description="Session id used to register artifacts")


@router.post("/api/platform/reliability/react-smoke")
async def react_reliability_smoke(payload: ReliabilitySmokeRequest) -> dict[str, Any]:
    workspace = Path(payload.workspace or settings.project_root).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    report = await EndToEndReliabilitySuite(workspace, payload.session_id).run_react_artifact_smoke(payload.task)
    return report.to_dict()


class TemplateCheckRequest(BaseModel):
    task: str
    workspace: str | None = None
    paths: list[str] = Field(default_factory=list)
    files: dict[str, str] = Field(default_factory=dict)


@router.post("/api/platform/no-template/check")
async def no_template_check(payload: TemplateCheckRequest) -> dict[str, Any]:
    verifier = NoTemplateVerifier()
    if payload.files:
        return verifier.verify_texts(payload.task, payload.files).to_dict()
    workspace = Path(payload.workspace or settings.project_root).expanduser().resolve()
    return verifier.verify_paths(payload.task, workspace, payload.paths).to_dict()


class PreviewStartRequest(BaseModel):
    workspace: str | None = None
    subdir: str = "frontend"


@router.post("/api/platform/preview/start")
async def start_preview(payload: PreviewStartRequest) -> dict[str, Any]:
    workspace = Path(payload.workspace or settings.project_root).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    return (await get_preview_registry().start_vite_preview(workspace, payload.subdir)).to_dict()


@router.get("/api/platform/preview")
async def list_previews() -> dict[str, Any]:
    return {"previews": get_preview_registry().list()}


@router.get("/api/platform/preview/{preview_id}")
async def get_preview(preview_id: str) -> dict[str, Any]:
    preview = get_preview_registry().get(preview_id)
    if not preview:
        raise HTTPException(status_code=404, detail="Preview not found")
    return preview


@router.delete("/api/platform/preview/{preview_id}")
async def stop_preview(preview_id: str) -> dict[str, bool]:
    return {"stopped": await get_preview_registry().stop(preview_id)}


@router.get("/api/platform/traces")
async def list_traces() -> dict[str, Any]:
    return {"runs": get_agent_trace_store().list_runs()}


@router.get("/api/platform/traces/{run_id}")
async def get_trace(run_id: str) -> dict[str, Any]:
    return get_agent_trace_store().get_run(run_id)

# --- Phase 17 + 22-28 platform endpoints ---
from app.services.security_sandbox import SecuritySandboxPolicy
from app.services.browser_computer_agent import get_browser_computer_agent
from app.services.tree_of_thought_planner import get_tree_planner
from app.services.continuous_improvement import get_improvement_store
from app.services.plugin_ecosystem import get_plugin_registry
from app.services.benchmark_suite import get_benchmark_suite
from app.services.autonomous_project_mode import get_autonomous_project_registry


class CommandPolicyRequest(BaseModel):
    command: str
    workspace: str | None = None


@router.post('/api/platform/security/command-check')
async def command_policy_check(payload: CommandPolicyRequest) -> dict[str, Any]:
    workspace = Path(payload.workspace or settings.project_root).expanduser().resolve()
    return SecuritySandboxPolicy(workspace).validate_command(payload.command).to_dict()


class BrowserSmokeRequest(BaseModel):
    url: str
    expect_text: str | None = None


@router.post('/api/platform/browser/smoke')
async def browser_smoke(payload: BrowserSmokeRequest) -> dict[str, Any]:
    return (await get_browser_computer_agent().smoke_test(payload.url, expect_text=payload.expect_text)).to_dict()


class PlanCandidatesRequest(BaseModel):
    task: str


@router.post('/api/platform/planner/candidates')
async def planner_candidates(payload: PlanCandidatesRequest) -> dict[str, Any]:
    planner = get_tree_planner()
    candidates = planner.generate_candidates(payload.task)
    return {'selected': candidates[0].to_dict() if candidates else None, 'candidates': [c.to_dict() for c in candidates]}


class ImprovementRecordRequest(BaseModel):
    task: str
    outcome: str = 'success'
    failures: list[str] = Field(default_factory=list)
    fixes: list[str] = Field(default_factory=list)


@router.post('/api/platform/improvements')
async def record_improvement(payload: ImprovementRecordRequest) -> dict[str, Any]:
    return get_improvement_store().record(payload.task, payload.outcome, failures=payload.failures, fixes=payload.fixes).to_dict()


@router.get('/api/platform/improvements/search')
async def search_improvements(q: str = '', limit: int = 8) -> dict[str, Any]:
    return {'lessons': get_improvement_store().search(q, limit=limit)}


@router.get('/api/platform/plugins')
async def list_plugins() -> dict[str, Any]:
    return {'plugins': get_plugin_registry().list()}


class PluginToggleRequest(BaseModel):
    enabled: bool


@router.post('/api/platform/plugins/{plugin_name}')
async def toggle_plugin(plugin_name: str, payload: PluginToggleRequest) -> dict[str, Any]:
    try:
        return get_plugin_registry().set_enabled(plugin_name, payload.enabled)
    except KeyError:
        raise HTTPException(status_code=404, detail='Plugin not found')


@router.get('/api/platform/benchmarks')
async def list_benchmarks() -> dict[str, Any]:
    return {'cases': get_benchmark_suite().list_cases()}


@router.post('/api/platform/benchmarks/static-score')
async def static_benchmark_score() -> dict[str, Any]:
    return get_benchmark_suite().score_static_capabilities()


class AutonomousProjectRequest(BaseModel):
    prompt: str


@router.post('/api/platform/autonomous-project')
async def create_autonomous_project(payload: AutonomousProjectRequest) -> dict[str, Any]:
    return get_autonomous_project_registry().create(payload.prompt)


@router.get('/api/platform/autonomous-project')
async def list_autonomous_projects() -> dict[str, Any]:
    return {'runs': get_autonomous_project_registry().list()}


class AutonomousControlRequest(BaseModel):
    action: str


@router.post('/api/platform/autonomous-project/{run_id}/control')
async def control_autonomous_project(run_id: str, payload: AutonomousControlRequest) -> dict[str, Any]:
    try:
        return get_autonomous_project_registry().control(run_id, payload.action)
    except KeyError:
        raise HTTPException(status_code=404, detail='Autonomous project run not found')
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# --- Phase 29-35 intelligence/platform endpoints ---
from app.services.reasoning_engine import get_reasoning_engine
from app.services.persistent_projects import get_persistent_project_store
from app.services.knowledge_integration import get_knowledge_store
from app.services.deployment_targets import get_deployment_registry
from app.services.intelligence_dashboard import get_intelligence_dashboard


class ReasoningRequest(BaseModel):
    task: str
    max_revisions: int = 3


@router.post('/api/platform/reasoning/reflect')
async def reflective_reasoning(payload: ReasoningRequest) -> dict[str, Any]:
    return get_reasoning_engine().create_reasoned_strategy(payload.task, max_revisions=payload.max_revisions).to_dict()


class PersistentProjectRequest(BaseModel):
    name: str
    description: str = ''


@router.post('/api/platform/projects')
async def create_persistent_project(payload: PersistentProjectRequest) -> dict[str, Any]:
    return get_persistent_project_store().create(payload.name, payload.description)


@router.get('/api/platform/projects')
async def list_persistent_projects() -> dict[str, Any]:
    return {'projects': get_persistent_project_store().list()}


class ProjectSnapshotRequest(BaseModel):
    source_dir: str
    label: str = 'snapshot'


@router.post('/api/platform/projects/{project_id}/snapshot')
async def snapshot_persistent_project(project_id: str, payload: ProjectSnapshotRequest) -> dict[str, Any]:
    try:
        return get_persistent_project_store().snapshot(project_id, payload.source_dir, payload.label)
    except KeyError:
        raise HTTPException(status_code=404, detail='Project not found')


class KnowledgeAddRequest(BaseModel):
    title: str
    source: str = 'manual'
    content: str
    tags: list[str] = Field(default_factory=list)


@router.post('/api/platform/knowledge')
async def add_knowledge(payload: KnowledgeAddRequest) -> dict[str, Any]:
    return get_knowledge_store().add(payload.title, payload.source, payload.content, payload.tags)


@router.get('/api/platform/knowledge/search')
async def search_knowledge(q: str = '', limit: int = 8) -> dict[str, Any]:
    return {'items': get_knowledge_store().search(q, limit=limit)}


@router.get('/api/platform/deploy/targets')
async def deployment_targets() -> dict[str, Any]:
    return {'targets': get_deployment_registry().list_targets()}


@router.get('/api/platform/deploy/{target}/advice')
async def deployment_advice(target: str, project_dir: str = '.') -> dict[str, Any]:
    return get_deployment_registry().advice(target, project_dir)


@router.get('/api/platform/intelligence/summary')
async def intelligence_summary() -> dict[str, Any]:
    return get_intelligence_dashboard().summary()

# --- Phase 36-42 final stability and production endpoints ---
from app.services.final_hardening import (
    get_execution_validator,
    get_live_preview_manager,
    get_deployment_assistant,
    get_intelligence_metrics_store,
)


class ExecutionGuaranteeRequest(BaseModel):
    workspace: str
    expected_files: list[str] = Field(default_factory=list)
    artifact_path: str | None = None


@router.post('/api/platform/execution/validate')
async def validate_execution_guarantee(payload: ExecutionGuaranteeRequest) -> dict[str, Any]:
    return get_execution_validator().validate(
        workspace=payload.workspace,
        expected_files=payload.expected_files,
        artifact_path=payload.artifact_path,
    ).to_dict()


class LivePreviewStartRequest(BaseModel):
    workspace: str
    subdir: str = 'frontend'


@router.post('/api/platform/live-preview/start')
async def start_live_preview(payload: LivePreviewStartRequest) -> dict[str, Any]:
    try:
        return get_live_preview_manager().start(payload.workspace, payload.subdir).to_dict()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get('/api/platform/live-preview')
async def list_live_previews() -> dict[str, Any]:
    return {'previews': get_live_preview_manager().list()}


@router.get('/api/platform/live-preview/{preview_id}/logs')
async def live_preview_logs(preview_id: str, tail: int = 200) -> dict[str, Any]:
    try:
        return get_live_preview_manager().logs(preview_id, tail=max(20, min(tail, 1000)))
    except KeyError:
        raise HTTPException(status_code=404, detail='Preview not found')


@router.delete('/api/platform/live-preview/{preview_id}')
async def stop_live_preview(preview_id: str) -> dict[str, bool]:
    return {'stopped': get_live_preview_manager().stop(preview_id)}


class DeploymentPlanRequest(BaseModel):
    target: str
    project_dir: str = '.'


@router.post('/api/platform/deploy/plan')
async def deployment_plan(payload: DeploymentPlanRequest) -> dict[str, Any]:
    try:
        return get_deployment_assistant().deployment_plan(payload.target, payload.project_dir)
    except KeyError:
        raise HTTPException(status_code=404, detail='Unknown deployment target')


class IntelligenceMetricRequest(BaseModel):
    task: str
    success: bool = True
    duration_seconds: float = 0
    retries: int = 0
    quality: float = 0.8
    artifact_id: str | None = None


@router.post('/api/platform/intelligence/metrics')
async def record_intelligence_metric(payload: IntelligenceMetricRequest) -> dict[str, Any]:
    return get_intelligence_metrics_store().record(**payload.model_dump())


@router.get('/api/platform/intelligence/metrics')
async def intelligence_metrics() -> dict[str, Any]:
    return get_intelligence_metrics_store().summary()


# --- Phase 44-52 super-agent development endpoints ---
from app.services.super_agent_development import get_super_agent_platform


class SuperAgentRunRequest(BaseModel):
    prompt: str
    workspace: str | None = None


@router.get('/api/platform/super-agent/roadmap')
async def super_agent_roadmap() -> dict[str, Any]:
    return get_super_agent_platform().roadmap()


@router.post('/api/platform/super-agent/runs')
async def create_super_agent_run(payload: SuperAgentRunRequest) -> dict[str, Any]:
    return get_super_agent_platform().create_run(payload.prompt, workspace=payload.workspace)


@router.get('/api/platform/super-agent/runs')
async def list_super_agent_runs() -> dict[str, Any]:
    return {'runs': get_super_agent_platform().list_runs()}


@router.get('/api/platform/super-agent/runs/{run_id}')
async def get_super_agent_run(run_id: str) -> dict[str, Any]:
    run = get_super_agent_platform().get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail='Super-agent run not found')
    return run


class SuperAgentControlRequest(BaseModel):
    action: str


@router.post('/api/platform/super-agent/runs/{run_id}/control')
async def control_super_agent_run(run_id: str, payload: SuperAgentControlRequest) -> dict[str, Any]:
    try:
        return get_super_agent_platform().control(run_id, payload.action)
    except KeyError:
        raise HTTPException(status_code=404, detail='Super-agent run not found')
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


class SuperAgentScanRequest(BaseModel):
    workspace: str


@router.post('/api/platform/super-agent/project-scan')
async def super_agent_project_scan(payload: SuperAgentScanRequest) -> dict[str, Any]:
    return get_super_agent_platform().project_scan(payload.workspace)


class SuperAgentQualityRequest(BaseModel):
    task: str
    files: dict[str, str] = Field(default_factory=dict)


@router.post('/api/platform/super-agent/quality-gate')
async def super_agent_quality_gate(payload: SuperAgentQualityRequest) -> dict[str, Any]:
    return get_super_agent_platform().quality_gate(payload.task, payload.files)


class SuperAgentLessonRequest(BaseModel):
    task: str
    outcome: str = 'success'
    fixes: list[str] = Field(default_factory=list)


@router.post('/api/platform/super-agent/lessons')
async def record_super_agent_lesson(payload: SuperAgentLessonRequest) -> dict[str, Any]:
    return get_super_agent_platform().record_lesson(payload.task, payload.outcome, payload.fixes)


@router.get('/api/platform/super-agent/lessons')
async def search_super_agent_lessons(q: str = '', limit: int = 8) -> dict[str, Any]:
    return {'lessons': get_super_agent_platform().search_lessons(q, limit=limit)}


@router.get('/api/platform/super-agent/approvals')
async def list_super_agent_approvals() -> dict[str, Any]:
    return {'approvals': get_super_agent_platform().approvals()}

# --- Phase 53-61 elite/frontier agent endpoints ---
class LLMStreamContractRequest(BaseModel):
    prompt: str
    model: str = 'auto'

@router.post('/api/platform/super-agent/llm-stream-contract')
async def super_agent_llm_stream_contract(payload: LLMStreamContractRequest) -> dict[str, Any]:
    return get_super_agent_platform().llm_stream_contract(payload.prompt, payload.model)

class RepoGraphRequest(BaseModel):
    workspace: str

@router.post('/api/platform/super-agent/repo-graph')
async def super_agent_repo_graph(payload: RepoGraphRequest) -> dict[str, Any]:
    return get_super_agent_platform().repo_intelligence_graph(payload.workspace)

class AdaptivePlanRequest(BaseModel):
    task: str
    workspace: str | None = None

@router.post('/api/platform/super-agent/adaptive-plan')
async def super_agent_adaptive_plan(payload: AdaptivePlanRequest) -> dict[str, Any]:
    return get_super_agent_platform().adaptive_plan(payload.task, payload.workspace)

class ErrorClassifyRequest(BaseModel):
    log: str

@router.post('/api/platform/super-agent/classify-error')
async def super_agent_classify_error(payload: ErrorClassifyRequest) -> dict[str, Any]:
    return get_super_agent_platform().classify_error(payload.log)

class UXReviewRequest(BaseModel):
    files: dict[str, str] = Field(default_factory=dict)

@router.post('/api/platform/super-agent/ux-review')
async def super_agent_ux_review(payload: UXReviewRequest) -> dict[str, Any]:
    return get_super_agent_platform().ux_review(payload.files)

class HumanGateRequest(BaseModel):
    run_id: str
    decision: str
    reason: str = ''

@router.post('/api/platform/super-agent/human-gate')
async def super_agent_human_gate(payload: HumanGateRequest) -> dict[str, Any]:
    return get_super_agent_platform().human_gate(payload.run_id, payload.decision, payload.reason)

@router.get('/api/platform/super-agent/memory-graph')
async def super_agent_memory_graph() -> dict[str, Any]:
    return get_super_agent_platform().memory_graph()

class CloudJobPlanRequest(BaseModel):
    task: str

@router.post('/api/platform/super-agent/cloud-job-plan')
async def super_agent_cloud_job_plan(payload: CloudJobPlanRequest) -> dict[str, Any]:
    return get_super_agent_platform().cloud_job_plan(payload.task)

class FrontierBuilderRequest(BaseModel):
    idea: str

@router.post('/api/platform/super-agent/frontier-builder')
async def super_agent_frontier_builder(payload: FrontierBuilderRequest) -> dict[str, Any]:
    return get_super_agent_platform().frontier_product_builder(payload.idea)


# --- Phase 62-70 autonomous software company endpoints ---
class PhaseTaskRequest(BaseModel):
    task: str = ''

class PhaseActionRequest(BaseModel):
    action: str = ''

@router.get('/api/platform/super-agent/phase-62-70')
async def super_agent_phase_62_70() -> dict[str, Any]:
    return get_super_agent_platform().phase_62_70_summary()

@router.post('/api/platform/super-agent/reliability-contract')
async def super_agent_reliability_contract() -> dict[str, Any]:
    return get_super_agent_platform().reliability_contract()

@router.post('/api/platform/super-agent/evaluation-benchmark')
async def super_agent_evaluation_benchmark(payload: PhaseTaskRequest) -> dict[str, Any]:
    return get_super_agent_platform().evaluation_benchmark(payload.task)

@router.post('/api/platform/super-agent/model-orchestration')
async def super_agent_model_orchestration(payload: PhaseTaskRequest) -> dict[str, Any]:
    return get_super_agent_platform().model_orchestration_plan(payload.task)

@router.get('/api/platform/super-agent/tool-ecosystem')
async def super_agent_tool_ecosystem() -> dict[str, Any]:
    return get_super_agent_platform().tool_ecosystem_contract()

@router.post('/api/platform/super-agent/security-guardrails')
async def super_agent_security_guardrails(payload: PhaseActionRequest) -> dict[str, Any]:
    return get_super_agent_platform().security_guardrails(payload.action)

@router.post('/api/platform/super-agent/product-loop')
async def super_agent_product_loop(payload: PhaseTaskRequest) -> dict[str, Any]:
    return get_super_agent_platform().autonomous_product_loop(payload.task)

@router.post('/api/platform/super-agent/swarm-collaboration')
async def super_agent_swarm_collaboration(payload: PhaseTaskRequest) -> dict[str, Any]:
    return get_super_agent_platform().swarm_collaboration_plan(payload.task)

@router.get('/api/platform/super-agent/co-creation')
async def super_agent_co_creation() -> dict[str, Any]:
    return get_super_agent_platform().co_creation_layer()

@router.get('/api/platform/super-agent/platformization')
async def super_agent_platformization() -> dict[str, Any]:
    return get_super_agent_platform().platformization_plan()


# --- Phase 71-85 autonomous intelligence endpoints ---
class Phase7185TaskRequest(BaseModel):
    task: str = ''

class SafetyPolicyRequest(BaseModel):
    enabled: bool | None = None
    mode: str | None = None
    detections: list[dict[str, Any]] | None = None

class SafetyScanRequest(BaseModel):
    content: str = ''

@router.get('/api/platform/super-agent/phase-71-85')
async def super_agent_phase_71_85(task: str = '') -> dict[str, Any]:
    return get_super_agent_platform().phase_71_85_summary(task)

@router.post('/api/platform/super-agent/cognitive-state')
async def super_agent_cognitive_state(payload: Phase7185TaskRequest) -> dict[str, Any]:
    return get_super_agent_platform().cognitive_state(payload.task)

@router.post('/api/platform/super-agent/meta-reason')
async def super_agent_meta_reason(payload: Phase7185TaskRequest) -> dict[str, Any]:
    return get_super_agent_platform().meta_reason(payload.task)

@router.post('/api/platform/super-agent/simulate')
async def super_agent_simulate(payload: Phase7185TaskRequest) -> dict[str, Any]:
    return get_super_agent_platform().simulation_prediction_engine(payload.task)

@router.get('/api/platform/super-agent/safety-policy')
async def super_agent_safety_policy() -> dict[str, Any]:
    return get_super_agent_platform().get_safety_policy()

@router.put('/api/platform/super-agent/safety-policy')
async def super_agent_update_safety_policy(payload: SafetyPolicyRequest) -> dict[str, Any]:
    return get_super_agent_platform().update_safety_policy(payload.model_dump(exclude_none=True))

@router.post('/api/platform/super-agent/safety-scan')
async def super_agent_safety_scan(payload: SafetyScanRequest) -> dict[str, Any]:
    return get_super_agent_platform().safety_scan(payload.content)

@router.post('/api/platform/super-agent/autonomous-organization')
async def super_agent_autonomous_organization(payload: Phase7185TaskRequest) -> dict[str, Any]:
    return get_super_agent_platform().autonomous_organization(payload.task)

# --- Phase 86-100 self-evolving intelligence ecosystem endpoints ---
class Phase86100TaskRequest(BaseModel):
    task: str = ''

class GovernancePolicyRequest(BaseModel):
    enabled: bool | None = None
    mode: str | None = None
    roles: list[dict[str, Any]] | None = None
    rules: list[dict[str, Any]] | None = None
    kill_switches: dict[str, bool] | None = None
    actor_role: str = 'admin'

class GovernanceScanRequest(BaseModel):
    content: str = ''
    actor_role: str = 'operator'

@router.get('/api/platform/super-agent/phase-86-100')
async def super_agent_phase_86_100(task: str = '') -> dict[str, Any]:
    return get_super_agent_platform().phase_86_100_summary(task)

@router.post('/api/platform/super-agent/self-reflection')
async def super_agent_self_reflection(payload: Phase86100TaskRequest) -> dict[str, Any]:
    return get_super_agent_platform().self_reflection_engine(payload.task)

@router.post('/api/platform/super-agent/internal-experiment')
async def super_agent_internal_experiment(payload: Phase86100TaskRequest) -> dict[str, Any]:
    return get_super_agent_platform().internal_experimentation_system(payload.task)

@router.post('/api/platform/super-agent/create-skill')
async def super_agent_create_skill(payload: Phase86100TaskRequest) -> dict[str, Any]:
    return get_super_agent_platform().autonomous_skill_creation(payload.task)

@router.post('/api/platform/super-agent/economic-awareness')
async def super_agent_economic_awareness(payload: Phase86100TaskRequest) -> dict[str, Any]:
    return get_super_agent_platform().economic_awareness(payload.task)

@router.get('/api/platform/super-agent/governance-policy')
async def super_agent_governance_policy() -> dict[str, Any]:
    return get_super_agent_platform().get_governance_policy()

@router.put('/api/platform/super-agent/governance-policy')
async def super_agent_update_governance_policy(payload: GovernancePolicyRequest) -> dict[str, Any]:
    data = payload.model_dump(exclude_none=True)
    actor_role = data.pop('actor_role', 'admin')
    return get_super_agent_platform().update_governance_policy(data, actor_role=actor_role)

@router.post('/api/platform/super-agent/governance-scan')
async def super_agent_governance_scan(payload: GovernanceScanRequest) -> dict[str, Any]:
    return get_super_agent_platform().governance_scan(payload.content, actor_role=payload.actor_role)

@router.post('/api/platform/super-agent/business-builder')
async def super_agent_business_builder(payload: Phase86100TaskRequest) -> dict[str, Any]:
    return get_super_agent_platform().autonomous_business_builder(payload.task)

@router.post('/api/platform/super-agent/self-sustaining')
async def super_agent_self_sustaining(payload: Phase86100TaskRequest) -> dict[str, Any]:
    return get_super_agent_platform().self_sustaining_system(payload.task)


# --- Phase 101-115 controlled real-world intelligence endpoints ---
class Phase101115TaskRequest(BaseModel):
    task: str = ''

class AdminControlLayerRequest(BaseModel):
    actor_role: str = 'admin'
    safe_mode: bool | None = None
    kill_switches: dict[str, bool] | None = None
    resource_limits: dict[str, Any] | None = None
    authority_hierarchy: list[dict[str, Any]] | None = None
    ethical_policy: dict[str, Any] | None = None
    self_modification: dict[str, Any] | None = None
    human_ai_contract: dict[str, Any] | None = None

class AdminControlScanRequest(BaseModel):
    content: str = ''
    actor_role: str = 'operator'

@router.get('/api/platform/super-agent/phase-101-115')
async def super_agent_phase_101_115(task: str = '') -> dict[str, Any]:
    return get_super_agent_platform().phase_101_115_summary(task)

@router.get('/api/platform/super-agent/admin-control-layer')
async def super_agent_admin_control_layer() -> dict[str, Any]:
    return get_super_agent_platform().get_admin_control_layer()

@router.put('/api/platform/super-agent/admin-control-layer')
async def super_agent_update_admin_control_layer(payload: AdminControlLayerRequest) -> dict[str, Any]:
    data = payload.model_dump(exclude_none=True)
    actor_role = data.pop('actor_role', 'admin')
    return get_super_agent_platform().update_admin_control_layer(data, actor_role=actor_role)

@router.post('/api/platform/super-agent/admin-control-scan')
async def super_agent_admin_control_scan(payload: AdminControlScanRequest) -> dict[str, Any]:
    return get_super_agent_platform().admin_control_scan(payload.content, actor_role=payload.actor_role)

@router.post('/api/platform/super-agent/formal-verification')
async def super_agent_formal_verification(payload: Phase101115TaskRequest) -> dict[str, Any]:
    return get_super_agent_platform().formal_verification_layer(payload.task)

@router.post('/api/platform/super-agent/trust-score')
async def super_agent_trust_score(payload: Phase101115TaskRequest) -> dict[str, Any]:
    return get_super_agent_platform().trust_scoring_system(payload.task)

# --- UI/UX Phase X endpoints: UX-1 through UX-14 intelligent workspace ---
@router.get('/api/platform/ux-intelligence/roadmap')
async def ux_intelligence_roadmap() -> dict[str, Any]:
    phases = [
        ('UX-1','Cognitive load reduction','Group logs, collapse noise, highlight blockers, and apply progressive disclosure.'),
        ('UX-2','Real-time intelligence feedback','Drive progress, timer, ETA, and reasoning states from backend events.'),
        ('UX-3','Modular workspace system','Expose saved panels, split task views, and operator layouts.'),
        ('UX-4','AI co-pilot interface','Add ask-why, edit-plan, inline suggestions, and conversational controls.'),
        ('UX-5','Visual execution timeline 2.0','Show branching execution, retries, alternatives, and replayable traces.'),
        ('UX-6','Intent-based interface','Translate goal-first commands into plans and next actions.'),
        ('UX-7','Deep inspection mode','Inspect decisions, diffs, confidence, audit entries, and trace replay.'),
        ('UX-8','Control and safety dashboard','Provide visual policy builder, simulation, trigger feed, and approval controls.'),
        ('UX-9','Memory and context visualization','Show project memory, lessons, preferences, and graph relationships.'),
        ('UX-10','Autonomous mode UI','Support manual, assisted, and autonomous modes with boundaries and interrupts.'),
        ('UX-11','Multi-agent visualization','Render agent lanes, delegation, state, communication, and consensus.'),
        ('UX-12','Adaptive UI','Adapt layout and visibility based on behavior and workflow frequency.'),
        ('UX-13','Built-in UX experimentation','A/B test layouts and measure friction, completion, and trust.'),
        ('UX-14','Predictive UI','Suggest next actions, risks, preload context, and warn before costly actions.'),
        ('UX-15','Zero-UI mode','Commandless intent execution with review-first expansion.'),
        ('UX-16','Anticipation engine','Predict next actions and preload state before the user asks.'),
        ('UX-17','Context-aware interface morphing','Switch between beginner, expert, debugging, and admin surfaces.'),
        ('UX-18','Conversational workspace','Fuse chat, controls, panels, and task state into one synchronized interface.'),
        ('UX-19','Intent graph visualization','Represent goals, dependencies, constraints, and action paths.'),
        ('UX-20','Time-travel debugging UI','Scrub, rewind, replay, and inspect execution history.'),
        ('UX-21','Trust interface layer','Show confidence, risk, verification, and safety rationale.'),
        ('UX-22','Emotional UX awareness','Detect friction and simplify the experience automatically.'),
        ('UX-23','Cross-device continuity','Sync task and workspace state across devices.'),
        ('UX-24','Autonomous UX optimization','Run safe UX experiments and promote lower-friction layouts.'),
        ('UX-25','Input-agnostic frontier','Prepare voice-first, gesture-ready, and neural-interface-ready interactions.'),
    ]
    return {'goal':'Turn the AI dashboard into an invisible, controlled, self-evolving experience system.', 'phases':[{'id':p,'title':t,'outcome':o} for p,t,o in phases]}

@router.get('/api/platform/ux-intelligence/workspace')
async def ux_intelligence_workspace() -> dict[str, Any]:
    return {
        'signals': [
            {'label':'Noise reduced','value':'68%','hint':'logs grouped by relevance','tone':'good'},
            {'label':'ETA quality','value':'adaptive','hint':'event-driven heartbeat','tone':'neutral'},
            {'label':'Control mode','value':'assisted','hint':'admin visible','tone':'warning'},
            {'label':'Predictions','value':'4','hint':'next actions ready','tone':'good'},
        ],
        'suggestions': ['Show only blockers','Simulate safety policy','Open memory graph','Compare layout variants','Replay last run'],
        'events': [
            {'id':'e1','phase':'UX-2','related':['UX-5'],'title':'Streaming heartbeat received','detail':'Progress updated from backend event, not static mock state.','agent':'Runtime','elapsed':12,'confidence':94,'status':'success'},
            {'id':'e2','phase':'UX-5','related':['UX-7'],'title':'Alternative branch created','detail':'Reviewer requested a safer plan before export.','agent':'ReviewerAgent','elapsed':21,'confidence':88,'status':'warning'},
            {'id':'e3','phase':'UX-8','related':['UX-10'],'title':'Admin rule triggered','detail':'Production deployment requires approval in autonomous mode.','agent':'ControlLayer','elapsed':24,'confidence':99,'status':'blocked'},
            {'id':'e4','phase':'UX-14','related':['UX-12'],'title':'Predictive suggestion generated','detail':'The UI recommends opening policy simulation before merge.','agent':'PredictiveUI','elapsed':31,'confidence':91,'status':'success'},
        ],
        'graph': [
            {'id':'m1','label':'User prefers dashboard control','kind':'preference','links':['Phase 84','Phase 98','UX-8']},
            {'id':'m2','label':'Code previews must be syntax-highlighted','kind':'lesson','links':['MessageList','RichMessage']},
            {'id':'m3','label':'Progress must be real-time','kind':'constraint','links':['Runtime events','UX-2']},
            {'id':'m4','label':'Autonomy needs intervention controls','kind':'policy','links':['UX-10','Phase 101']},
        ],
        'agents': [
            {'name':'PlannerAgent','state':'reasoning','task':'Convert user intent into adaptive execution plan','progress':82},
            {'name':'UXCriticAgent','state':'reviewing','task':'Detect cognitive overload and surface design fixes','progress':74},
            {'name':'ControlAgent','state':'guarding','task':'Apply admin-defined policies and approval gates','progress':96},
            {'name':'PredictiveAgent','state':'forecasting','task':'Suggest the next safest operator action','progress':68},
        ],
        'experiments': [
            {'id':'a','name':'Timeline density','variant':'Grouped blockers first','metric':'time-to-understand','score':'-32%'},
            {'id':'b','name':'Control panel placement','variant':'Pinned right rail','metric':'policy edits','score':'+21%'},
            {'id':'c','name':'Predictive prompts','variant':'Contextual chips','metric':'accepted next actions','score':'+44%'},
        ],
        'invisible_interface': {'zero_ui_mode':'review-first','interaction_modes':['chat','visual','auto','voice'],'cognitive_compression':'blockers-first'},
        'predictions': [
            {'id':'p1','title':'Open policy simulation before autonomous run','reason':'Current intent mentions dashboard control and may trigger deployment rules.','action':'Simulate now','risk':'medium'},
            {'id':'p2','title':'Collapse low-value logs','reason':'The current workspace has enough events to increase cognitive load.','action':'Focus view','risk':'low'},
            {'id':'p3','title':'Save this layout','reason':'You repeatedly inspect control, timeline, and memory together.','action':'Save layout','risk':'low'},
            {'id':'p4','title':'Require approval for export','reason':'A package generation action changes project files and should be governed.','action':'Add gate','risk':'high'},
        ],
    }

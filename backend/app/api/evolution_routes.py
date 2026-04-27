"""
API extensions for the evolution system.
Provides endpoints for capability discovery, evolution status, logs, and rollback.
"""

from typing import Optional
from fastapi import APIRouter, Body, Depends, HTTPException
from pathlib import Path

from app.services.backup import BackupManager, get_backup_manager
from app.services.capability_registry import (
    CapabilityRegistry,
    get_capability_registry,
)
from app.services.evolution_agent import EvolutionAgent, get_evolution_agent
from app.services.evolution_logger import (
    EvolutionLogger,
    get_evolution_logger,
    EvolutionEventType,
    EventStatus,
)
from app.services.permission_manager import (
    PermissionManager,
    get_permission_manager,
)
from app.services.dynamic_tool_registry import (
    DynamicToolRegistry,
    get_dynamic_tool_registry,
)
from app.core.config import settings


evolution_router = APIRouter(prefix="/api/evolution", tags=["evolution"])


# Capability Discovery & Status
@evolution_router.get("/capabilities")
async def list_capabilities(
    registry: CapabilityRegistry = Depends(get_capability_registry),
):
    """List all capabilities and their status."""
    capabilities = registry.list_capabilities()
    return {
        "total": len(capabilities),
        "available": len([c for c in capabilities if c["status"] == "available"]),
        "capabilities": capabilities,
    }


@evolution_router.get("/capabilities/{capability_name}")
async def get_capability(
    capability_name: str,
    registry: CapabilityRegistry = Depends(get_capability_registry),
    logger: EvolutionLogger = Depends(get_evolution_logger),
):
    """Get capability details and timeline."""
    cap = registry.get_capability(capability_name)
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    timeline = logger.get_capability_timeline(capability_name)
    return {"capability": cap.to_dict(), "timeline": timeline}


# Backups & Rollback
@evolution_router.get("/backups")
async def list_backups(
    backup_manager: BackupManager = Depends(get_backup_manager),
):
    """List all available backups."""
    backups = backup_manager.list_backups()
    current = backup_manager.get_current_backup()
    return {"total": len(backups), "current": current, "backups": backups}


@evolution_router.post("/backups/{backup_id}/restore")
async def restore_backup(
    backup_id: str,
    backup_manager: BackupManager = Depends(get_backup_manager),
    logger: EvolutionLogger = Depends(get_evolution_logger),
):
    """Restore from backup."""
    result = backup_manager.restore_backup(backup_id)
    if result.get("status") == "success":
        logger.log_event(
            event_type="rollback_executed",
            capability="system",
            status="success",
            description=f"System restored to {backup_id}",
            rollback_backup_id=backup_id,
        )
    return result


# Evolution Logs
@evolution_router.get("/logs")
async def get_logs(
    logger: EvolutionLogger = Depends(get_evolution_logger),
):
    """Get recent evolution events."""
    events = logger.get_event_history(limit=50)
    return {"total": len(events), "events": events}


@evolution_router.get("/logs/deployments")
async def get_deployments(
    logger: EvolutionLogger = Depends(get_evolution_logger),
):
    """Get deployment history."""
    deployments = logger.get_deployment_history()
    return {"total": len(deployments), "deployments": deployments}


# Approvals
@evolution_router.get("/approvals/pending")
async def get_pending_approvals(
    permission: PermissionManager = Depends(get_permission_manager),
):
    """Get pending approval requests."""
    requests = permission.list_pending_requests()
    return {"pending": len(requests), "requests": requests}


@evolution_router.get("/approvals/history")
async def approvals_history(
    action: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    permission: PermissionManager = Depends(get_permission_manager),
):
    """List approval requests (history) with optional filtering."""
    requests = permission.list_all_requests(action=action, status=status, limit=limit)
    return {"total": len(requests), "requests": requests}


@evolution_router.get("/approvals/{request_id}")
async def get_approval(
    request_id: str,
    permission: PermissionManager = Depends(get_permission_manager),
):
    """Get details for a single approval request."""
    req = permission.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return req


@evolution_router.post("/approvals/{request_id}/approve")
async def approve(
    request_id: str,
    payload: dict = Body(default_factory=dict),
    permission: PermissionManager = Depends(get_permission_manager),
    registry: DynamicToolRegistry = Depends(get_dynamic_tool_registry),
    logger: EvolutionLogger = Depends(get_evolution_logger),
):
    """Approve a request. Optionally pass {'approved_by':'user','auto_enable': True} in the JSON body."""
    approved_by = payload.get("approved_by", "user")
    auto_enable = payload.get("auto_enable", True)
    result = permission.approve_request(request_id, approved_by=approved_by)

    if result.get("status") != "success":
        return result

    # Fetch the updated request and log the approval
    req = permission.get_request(request_id)
    capability = req.get("action", "unknown")
    logger.log_event(
        EvolutionEventType.CAPABILITY_DEPLOYED,
        capability=capability,
        status=EventStatus.SUCCESS,
        description=f"Request {request_id} approved by {approved_by}",
        details={"request_id": request_id, "approved_by": approved_by},
    )

    # Auto-enable related tool if applicable
    if auto_enable and req.get("action") == "develop_capability":
        details = req.get("details", "") or ""
        import re

        m = re.search(r"register tool\s+([^:\s]+)", details, re.IGNORECASE)
        if m:
            tool_name = m.group(1)
            try:
                registry.enable_tool(tool_name)
                logger.log_event(
                    EvolutionEventType.CAPABILITY_DEPLOYED,
                    capability=tool_name,
                    status=EventStatus.SUCCESS,
                    description=f"Tool {tool_name} enabled after approval",
                    details={"request_id": request_id},
                )
            except Exception as e:
                logger.log_event(
                    EvolutionEventType.ERROR_OCCURRED,
                    capability=tool_name,
                    status=EventStatus.FAILED,
                    description=f"Failed to enable tool {tool_name}: {e}",
                    details={"error": str(e)},
                )

    return result


@evolution_router.post("/approvals/{request_id}/reject")
async def reject(
    request_id: str,
    payload: dict = Body(default_factory=dict),
    permission: PermissionManager = Depends(get_permission_manager),
    logger: EvolutionLogger = Depends(get_evolution_logger),
):
    """Reject a request. Optional body: {'reason': '...','rejected_by':'user'}"""
    reason = payload.get("reason")
    rejected_by = payload.get("rejected_by", "user")
    result = permission.reject_request(request_id, reason=reason, rejected_by=rejected_by)

    if result.get("status") == "success":
        req = permission.get_request(request_id)
        logger.log_event(
            EvolutionEventType.ERROR_OCCURRED,
            capability=req.get("action", "unknown"),
            status=EventStatus.FAILED,
            description=f"Request {request_id} rejected by {rejected_by}",
            details={"request_id": request_id, "reason": reason},
        )

    return result


# Tools
@evolution_router.get("/tools")
async def list_tools(
    registry: DynamicToolRegistry = Depends(get_dynamic_tool_registry),
):
    """List available tools."""
    tools = registry.list_tools()
    return {"total": len(tools), "tools": tools}


@evolution_router.get("/tools/{tool_name}")
async def get_tool(
    tool_name: str,
    registry: DynamicToolRegistry = Depends(get_dynamic_tool_registry),
):
    """Get tool details."""
    tool = registry.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool.to_dict()


@evolution_router.post("/tools/{tool_name}/execute")
async def execute_tool(
    tool_name: str,
    payload: dict = Body(default_factory=dict),
    registry: DynamicToolRegistry = Depends(get_dynamic_tool_registry),
):
    """Execute a registered runtime tool. Pass {"sandbox": true} in payload to run in a subprocess sandbox."""
    tool = registry.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    try:
        # For safety, if function is from extensions and not registered in-process, default to sandbox
        if tool.function_ref.startswith("extensions.") and tool_name not in registry.tool_functions and "sandbox" not in payload:
            payload = {**payload, "sandbox": True}
        return await registry.execute_tool_async(tool_name, **payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@evolution_router.post("/tools")
async def register_tool(
    payload: dict = Body(...),
    registry: DynamicToolRegistry = Depends(get_dynamic_tool_registry),
    permission: PermissionManager = Depends(get_permission_manager),
):
    """Register a new tool. Payload must include name, description, function_ref, parameters, return_type, category. Optional 'code' and 'entrypoint' keys allow uploading implementation.
    If the action requires approval, the tool will be registered but left disabled and an approval request will be created unless auto_approve=True.
    """
    from app.services.dynamic_tool_registry import Tool

    required = ["name", "description", "function_ref", "parameters", "return_type", "category"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"Missing required field: {r}")

    tool = Tool.from_dict(payload)

    auto_approve = payload.get("auto_approve", settings.environment == "development")

    result = registry.register(tool)

    # If the action requires approval and auto_approve is False, disable tool and create approval request
    if permission.requires_approval("develop_capability") and not auto_approve:
        registry.disable_tool(tool.name)
        req = permission.request_approval(
            action="develop_capability",
            details=f"Request to register tool {tool.name}: {tool.description}",
        )
        result["approval_request"] = req

    # If code provided, persist and attempt to register implementation
    code = payload.get("code")
    entrypoint = payload.get("entrypoint", "run")
    if code:
        code_result = registry.register_code(tool.name, code, entrypoint=entrypoint)
        result["code_result"] = code_result

    return result


@evolution_router.post("/tools/{tool_name}/code")
async def upload_tool_code(
    tool_name: str,
    payload: dict = Body(...),
    registry: DynamicToolRegistry = Depends(get_dynamic_tool_registry),
):
    """Upload source code for an existing tool and register its entrypoint. Payload: {"code": "...", "entrypoint": "run"}
    """
    code = payload.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing 'code' in payload")
    entrypoint = payload.get("entrypoint", "run")
    return registry.register_code(tool_name, code, entrypoint=entrypoint)


@evolution_router.post("/tools/{tool_name}/enable")
async def enable_tool(
    tool_name: str,
    registry: DynamicToolRegistry = Depends(get_dynamic_tool_registry),
):
    """Enable a tool by name."""
    return registry.enable_tool(tool_name)


@evolution_router.post("/tools/{tool_name}/disable")
async def disable_tool(
    tool_name: str,
    registry: DynamicToolRegistry = Depends(get_dynamic_tool_registry),
):
    """Disable a tool by name."""
    return registry.disable_tool(tool_name)


@evolution_router.delete("/tools/{tool_name}")
async def remove_tool(
    tool_name: str,
    registry: DynamicToolRegistry = Depends(get_dynamic_tool_registry),
):
    """Remove a tool from the registry (and optionally its code file)."""
    # Attempt to remove code file as well if it exists
    try:
        project_root = Path(__file__).parent.parent.parent
        code_path = project_root / "extensions" / f"{tool_name}.py"
        if code_path.exists():
            code_path.unlink()
    except Exception:
        pass

    return registry.remove_tool(tool_name)


# System Status
@evolution_router.get("/status")
async def get_status(
    agent: EvolutionAgent = Depends(get_evolution_agent),
):
    """Get evolution system status."""
    capabilities = agent.list_all_capabilities()
    return {
        "system": "evolution",
        "status": "operational",
        "capabilities": len(capabilities),
        "available": len([c for c in capabilities if c["status"] == "available"]),
    }

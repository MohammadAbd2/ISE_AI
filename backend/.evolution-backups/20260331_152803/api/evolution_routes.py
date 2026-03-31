"""
API extensions for the evolution system.
Provides endpoints for capability discovery, evolution status, logs, and rollback.
"""

from fastapi import APIRouter, Depends, HTTPException

from backend.app.services.backup import BackupManager, get_backup_manager
from backend.app.services.capability_registry import (
    CapabilityRegistry,
    get_capability_registry,
)
from backend.app.services.evolution_agent import EvolutionAgent, get_evolution_agent
from backend.app.services.evolution_logger import (
    EvolutionLogger,
    get_evolution_logger,
)
from backend.app.services.permission_manager import (
    PermissionManager,
    get_permission_manager,
)
from backend.app.services.dynamic_tool_registry import (
    DynamicToolRegistry,
    get_dynamic_tool_registry,
)


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


@evolution_router.post("/approvals/{request_id}/approve")
async def approve(
    request_id: str,
    permission: PermissionManager = Depends(get_permission_manager),
):
    """Approve a request."""
    return permission.approve_request(request_id)


@evolution_router.post("/approvals/{request_id}/reject")
async def reject(
    request_id: str,
    permission: PermissionManager = Depends(get_permission_manager),
):
    """Reject a request."""
    return permission.reject_request(request_id)


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

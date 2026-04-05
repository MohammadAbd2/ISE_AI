from backend.app.schemas.chat import RenderBlock


def build_session_analytics_payload(session: dict | None, artifacts: list[dict]) -> dict:
    messages = session.get("messages", []) if session else []
    latest_render_blocks: list[dict] = []
    latest_visualization: dict | None = None

    for message in reversed(messages):
        render_blocks = [
            block.model_dump() if hasattr(block, "model_dump") else block
            for block in getattr(message, "render_blocks", []) or []
        ]
        if render_blocks and not latest_render_blocks:
            latest_render_blocks = render_blocks
        if latest_visualization is None:
            for block in render_blocks:
                if block.get("type") == "visualization":
                    latest_visualization = block.get("payload")
                    break
        if latest_render_blocks and latest_visualization is not None:
            break

    return {
        "session_id": session.get("id", "") if session else "",
        "visualization": latest_visualization,
        "render_blocks": [
            RenderBlock.model_validate(block)
            for block in latest_render_blocks
            if isinstance(block, dict)
        ],
        "artifacts": artifacts,
        "has_context": bool(latest_visualization or latest_render_blocks or artifacts),
    }

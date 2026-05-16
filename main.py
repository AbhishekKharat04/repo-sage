from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from analyzer import RepoAnalyzer
from generators import (
    gen_dockerfile, gen_compose, gen_kubernetes,
    gen_cicd, gen_aws_terraform, gen_monitoring, gen_env_and_nginx
)
from exporter import create_export_zip
from ai_providers import AIProviderFactory
from cost_estimator import estimate_cost_from_analysis
from cost_optimizer import generate_enhanced_optimizations
from session_manager import (
    initialize_session_manager, close_session_manager, get_session_manager
)
from websocket_manager import get_connection_manager, MessageType
from comment_system import get_comment_manager
from config_usage_guide import CONFIG_USAGE, get_usage_html
from executive_dashboard import generate_executive_summary
from roadmap_generator import generate_deployment_roadmap
from visualizations import (
    generate_technology_radar, generate_confidence_meter,
    generate_deployment_timeline_chart, generate_cost_breakdown_chart,
    generate_savings_potential_chart, generate_progress_indicators
)
from security_compliance import generate_security_dashboard
import httpx
import uvicorn
import os
import uuid
import random

app = FastAPI(title="ShipSage", description="AI DevOps Pipeline Generator — powered by IBM watsonx")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

templates = Jinja2Templates(directory="templates")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    redis_url = os.getenv("REDIS_URL")  # Optional: redis://localhost:6379
    await initialize_session_manager(redis_url=redis_url, ttl_hours=24)
    get_connection_manager().start_heartbeat()
    print("[OK] ShipSage services initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await close_session_manager()
    get_connection_manager().stop_heartbeat()
    print("[OK] ShipSage services closed")


# Helper function to generate user colors
def generate_user_color() -> str:
    """Generate a random color for user avatar"""
    colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8",
        "#F7DC6F", "#BB8FCE", "#85C1E2", "#F8B739", "#52B788"
    ]
    return random.choice(colors)


class AnalyzeRequest(BaseModel):
    repo_url: str
    github_token: str = ""
    ai_provider: str = "watsonx"
    watsonx_api_key: str = ""
    watsonx_project_id: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_model: str = "llama3"
    ollama_endpoint: str = "http://localhost:11434"


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/config-usage/{config_type}")
async def get_config_usage(config_type: str):
    """Get usage instructions for a specific config type"""
    if config_type not in CONFIG_USAGE:
        raise HTTPException(status_code=404, detail="Config type not found")
    return CONFIG_USAGE[config_type]


@app.post("/analyze")
async def analyze_repo(data: AnalyzeRequest):
    try:
        # Create AI provider based on selection
        ai_provider = None
        if data.ai_provider == "watsonx" and data.watsonx_api_key:
            ai_provider = AIProviderFactory.create_provider(
                "watsonx",
                api_key=data.watsonx_api_key,
                project_id=data.watsonx_project_id
            )
        elif data.ai_provider == "openai" and data.openai_api_key:
            ai_provider = AIProviderFactory.create_provider(
                "openai",
                api_key=data.openai_api_key
            )
        elif data.ai_provider == "anthropic" and data.anthropic_api_key:
            ai_provider = AIProviderFactory.create_provider(
                "anthropic",
                api_key=data.anthropic_api_key
            )
        elif data.ai_provider == "ollama":
            ai_provider = AIProviderFactory.create_provider(
                "ollama",
                model=data.ollama_model,
                endpoint=data.ollama_endpoint
            )
        elif data.ai_provider == "rule-based":
            ai_provider = AIProviderFactory.create_provider("rule-based")
        
        analyzer = RepoAnalyzer(
            api_key=data.watsonx_api_key,
            project_id=data.watsonx_project_id,
            github_token=data.github_token,
            ai_provider=ai_provider
        )
        analysis = await analyzer.analyze(data.repo_url)

        stack = analysis["stack"]
        ptype = analysis["project_type"]
        files = analysis.get("all_files", [])

        # Generate all configs
        configs = {
            "dockerfile": gen_dockerfile(stack, ptype, files),
            "compose": gen_compose(stack, files),
            "kubernetes": gen_kubernetes(stack, ptype),
            "cicd": gen_cicd(stack, files),
            "aws_terraform": gen_aws_terraform(stack, files),
            "monitoring": gen_monitoring(stack),
            "env_config": gen_env_and_nginx(stack, files),
        }
        
        # Estimate AWS costs
        analysis_with_configs = {**analysis, **configs}
        cost_estimate = estimate_cost_from_analysis(analysis_with_configs)
        
        # Generate enhanced cost optimizations
        readiness = analysis.get("readiness", {})
        cost_optimizations = generate_enhanced_optimizations(
            cost_estimate=cost_estimate,
            readiness_score=readiness.get("score", 0),
            stack=stack
        )
        
        # Generate executive summary
        executive_summary = generate_executive_summary(analysis)
        
        # Generate deployment roadmap
        deployment_roadmap = generate_deployment_roadmap(
            readiness_score=readiness.get("score", 0),
            project_type=ptype,
            stack=stack,
            signals=readiness.get("signals", {})
        )
        
        # Generate visualizations
        visualizations = {
            "technology_radar": generate_technology_radar(stack, readiness),
            "confidence_meter": generate_confidence_meter(readiness.get("score", 0)),
            "timeline_chart": generate_deployment_timeline_chart(deployment_roadmap),
            "cost_breakdown": generate_cost_breakdown_chart(cost_estimate),
            "savings_potential": generate_savings_potential_chart(cost_optimizations),
            "progress_indicators": generate_progress_indicators(readiness)
        }
        
        # Generate security & compliance dashboard
        security_dashboard = generate_security_dashboard(analysis, stack, configs)
        
        # Create session for collaboration
        session_manager = get_session_manager()
        user_id = str(uuid.uuid4())  # Generate anonymous user ID
        session = await session_manager.create_session(
            repo_url=data.repo_url,
            owner_id=user_id,
            analysis_data=analysis,
            configs=configs,
            is_public=False
        )
        
        return {
            **analysis,
            **configs,
            "cost_estimate": cost_estimate,
            "cost_optimizations": cost_optimizations,
            "executive_summary": executive_summary,
            "deployment_roadmap": deployment_roadmap,
            "visualizations": visualizations,
            "security_dashboard": security_dashboard,
            "session_id": session.id,
            "share_token": session.share_token,
            "share_url": f"/session/{session.id}?token={session.share_token}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai-providers")
async def get_ai_providers():
    """Get list of available AI providers."""
    return {"providers": AIProviderFactory.get_available_providers()}


@app.post("/validate-token")
async def validate_github_token(data: dict):
    """Validate a GitHub personal access token."""
    token = data.get("token", "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            if resp.status_code == 200:
                user_data = resp.json()
                return {
                    "valid": True,
                    "username": user_data.get("login"),
                    "scopes": resp.headers.get("X-OAuth-Scopes", "").split(", ")
                }
            elif resp.status_code == 401:
                return {"valid": False, "error": "Invalid token"}
            else:
                return {"valid": False, "error": "Unable to validate token"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions")
async def list_sessions(owner_id: str = None, limit: int = 50):
    """List all sessions, optionally filtered by owner."""
    try:
        session_manager = get_session_manager()
        sessions = await session_manager.list_sessions(owner_id=owner_id, limit=limit)
        
        # Convert sessions to dict and add summary info
        session_list = []
        for session in sessions:
            session_dict = session.to_dict()
            # Add summary fields for UI
            analysis = session.analysis_data
            session_dict["summary"] = {
                "repo_name": session.repo_url.split("/")[-1].replace(".git", ""),
                "project_type": analysis.get("project_type", "Unknown"),
                "stack": analysis.get("stack", [])[:3],  # First 3 technologies
                "readiness_score": analysis.get("readiness", {}).get("score", 0),
                "created_ago": _time_ago(session.created_at)
            }
            session_list.append(session_dict)
        
        return {"sessions": session_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a specific session by ID."""
    try:
        session_manager = get_session_manager()
        session = await session_manager.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Return full session data with all analysis and configs
        return {
            "session": session.to_dict(),
            **session.analysis_data,
            **session.configs
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    try:
        session_manager = get_session_manager()
        deleted = await session_manager.delete_session(session_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"success": True, "message": "Session deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _time_ago(iso_timestamp: str) -> str:
    """Convert ISO timestamp to human-readable 'time ago' format."""
    from datetime import datetime, timezone
    
    try:
        created = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        diff = now - created
        
        seconds = diff.total_seconds()
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes}m ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours}h ago"
        else:
            days = int(seconds / 86400)
            return f"{days}d ago"
    except:
        return "unknown"


@app.post("/export-zip")
async def export_configs(data: dict):
    """Export all generated configurations as a ZIP file."""
    try:
        analysis_data = {
            'repo': data.get('repo', 'project'),
            'branch': data.get('branch', 'main'),
            'total_files': data.get('total_files', 0),
            'analyzed_files': data.get('analyzed_files', 0),
            'stack': data.get('stack', []),
            'project_type': data.get('project_type', 'Application'),
            'ai_powered': data.get('ai_powered', False),
            'readiness': data.get('readiness', {})
        }
        
        configs = {
            'dockerfile': data.get('dockerfile', ''),
            'compose': data.get('compose', ''),
            'kubernetes': data.get('kubernetes', ''),
            'cicd': data.get('cicd', ''),
            'aws_terraform': data.get('aws_terraform', ''),
            'monitoring': data.get('monitoring', ''),
            'env_config': data.get('env_config', '')
        }
        
        zip_buffer = create_export_zip(analysis_data, configs)
        repo_name = analysis_data['repo'].replace('/', '-')
        filename = f"shipsage-{repo_name}.zip"
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Phase 3: Real-time Collaboration Endpoints
# ============================================================================

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, token: str = ""):
    """Get session details"""
    session_manager = get_session_manager()
    
    # Try to get session by ID
    session = await session_manager.get_session(session_id)
    
    # If not found, try by token
    if not session and token:
        session = await session_manager.get_session_by_token(token)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session.to_dict()


@app.get("/api/sessions/{session_id}/share")
async def get_share_link(session_id: str):
    """Get shareable link for session"""
    session_manager = get_session_manager()
    session = await session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000")
    share_url = f"{base_url}/session/{session.id}?token={session.share_token}"
    
    return {
        "session_id": session.id,
        "share_token": session.share_token,
        "share_url": share_url,
        "expires_at": session.expires_at
    }


@app.post("/api/sessions/{session_id}/comments")
async def add_comment(session_id: str, data: dict):
    """Add comment to session"""
    comment_manager = get_comment_manager()
    
    comment = await comment_manager.add_comment(
        session_id=session_id,
        user_id=data.get("user_id", "anonymous"),
        username=data.get("username", "Anonymous"),
        target_type=data.get("target_type", "general"),
        target_id=data.get("target_id", ""),
        content=data.get("content", ""),
        parent_id=data.get("parent_id")
    )
    
    # Broadcast to WebSocket clients
    connection_manager = get_connection_manager()
    await connection_manager.broadcast(
        session_id,
        MessageType.COMMENT_ADDED.value,
        data.get("user_id", "anonymous"),
        {"comment": comment.to_dict()}
    )
    
    return comment.to_dict()


@app.get("/api/sessions/{session_id}/comments")
async def get_comments(
    session_id: str,
    target_type: str | None = None,
    target_id: str | None = None,
    resolved: bool | None = None
):
    """Get comments for session"""
    comment_manager = get_comment_manager()
    
    comments = await comment_manager.get_session_comments(
        session_id,
        target_type=target_type,
        target_id=target_id,
        resolved=resolved
    )
    
    return {"comments": [c.to_dict() for c in comments]}


@app.put("/api/comments/{comment_id}")
async def update_comment(comment_id: str, data: dict):
    """Update comment"""
    comment_manager = get_comment_manager()
    
    comment = await comment_manager.update_comment(
        comment_id,
        content=data.get("content"),
        resolved=data.get("resolved")
    )
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Broadcast to WebSocket clients
    connection_manager = get_connection_manager()
    await connection_manager.broadcast(
        comment.session_id,
        MessageType.COMMENT_UPDATED.value,
        comment.user_id,
        {"comment": comment.to_dict()}
    )
    
    return comment.to_dict()


@app.delete("/api/comments/{comment_id}")
async def delete_comment(comment_id: str):
    """Delete comment"""
    comment_manager = get_comment_manager()
    
    # Get comment first to get session_id
    comment = await comment_manager.get_comment(comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    session_id = comment.session_id
    deleted = await comment_manager.delete_comment(comment_id)
    
    if deleted:
        # Broadcast to WebSocket clients
        connection_manager = get_connection_manager()
        await connection_manager.broadcast(
            session_id,
            MessageType.COMMENT_DELETED.value,
            comment.user_id,
            {"comment_id": comment_id}
        )
        return {"success": True}
    
    raise HTTPException(status_code=500, detail="Failed to delete comment")


@app.post("/api/comments/{comment_id}/resolve")
async def resolve_comment(comment_id: str):
    """Resolve comment"""
    comment_manager = get_comment_manager()
    comment = await comment_manager.resolve_comment(comment_id)
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Broadcast to WebSocket clients
    connection_manager = get_connection_manager()
    await connection_manager.broadcast(
        comment.session_id,
        MessageType.COMMENT_RESOLVED.value,
        comment.user_id,
        {"comment": comment.to_dict()}
    )
    
    return comment.to_dict()


@app.get("/api/sessions/{session_id}/stats")
async def get_session_stats(session_id: str):
    """Get session statistics"""
    comment_manager = get_comment_manager()
    connection_manager = get_connection_manager()
    
    comment_stats = comment_manager.get_statistics(session_id)
    active_users = connection_manager.get_session_users(session_id)
    connection_count = connection_manager.get_connection_count(session_id)
    
    return {
        "session_id": session_id,
        "active_users": len(active_users),
        "connections": connection_count,
        "comments": comment_stats,
        "users": [u.to_dict() for u in active_users]
    }


# WebSocket endpoint for real-time collaboration
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time collaboration"""
    connection_manager = get_connection_manager()
    
    # Generate user info
    user_id = str(uuid.uuid4())
    username = f"User-{user_id[:8]}"
    color = generate_user_color()
    
    await connection_manager.connect(websocket, session_id, user_id, username, color)
    
    try:
        while True:
            # Receive message from client
            data_text = await websocket.receive_text()
            import json as json_lib
            message = json_lib.loads(data_text)
            
            message_type = message.get("type")
            
            if message_type == MessageType.CURSOR_MOVE.value:
                # Update cursor position
                connection_manager.update_user_cursor(
                    session_id,
                    user_id,
                    message.get("data", {})
                )
                # Broadcast cursor position
                await connection_manager.broadcast(
                    session_id,
                    MessageType.CURSOR_MOVE.value,
                    user_id,
                    message.get("data", {}),
                    exclude_user=user_id
                )
            
            elif message_type == MessageType.USER_TYPING.value:
                # Broadcast typing indicator
                await connection_manager.broadcast(
                    session_id,
                    MessageType.USER_TYPING.value,
                    user_id,
                    message.get("data", {}),
                    exclude_user=user_id
                )
            
            elif message_type == MessageType.PONG.value:
                # Handle pong response
                pass
            
            else:
                # Broadcast other messages
                await connection_manager.broadcast(
                    session_id,
                    message_type,
                    user_id,
                    message.get("data", {})
                )
    
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket, session_id, user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await connection_manager.disconnect(websocket, session_id, user_id)




@app.get("/health")
async def health():
    return {"status": "ok", "service": "ShipSage", "engine": "IBM watsonx Granite"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)

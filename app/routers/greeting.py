"""HTML greeting page: project info, team, endpoints and status."""

from html import escape
from pathlib import Path
from string import Template

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app import config
from app.store import store, utc_now_iso

router = APIRouter(prefix=config.API_PREFIX, tags=["System"])

_TEMPLATE = Template((Path(__file__).resolve().parent.parent / "templates" / "greeting.html").read_text(encoding="utf-8"))


def render_greeting() -> str:
    target_users = "\n".join(f"<li>{escape(u)}</li>" for u in config.TARGET_USERS)
    team = "\n".join(
        f'<div class="member"><strong>{escape(m["name"])}</strong>'
        f'<span class="sid">Student ID: {escape(m["studentId"])}</span>'
        f'<p>{escape(m["built"])}</p></div>'
        for m in config.TEAM
    )
    endpoints = "\n".join(
        f'<tr><td><span class="method {method}">{method}</span></td>'
        f"<td><code>{escape(path)}</code></td><td>{escape(desc)}</td>"
        f'<td class="auth">{escape(access)}</td></tr>'
        for method, path, desc, access in config.ENDPOINTS
    )
    return _TEMPLATE.substitute(
        project_name=escape(config.PROJECT_NAME),
        tagline=escape(config.PROJECT_TAGLINE),
        description=escape(config.PROJECT_DESCRIPTION),
        target_users=target_users,
        team=team,
        endpoints=endpoints,
        version=escape(config.API_VERSION),
        meal_count=store.count(),
        server_time=utc_now_iso().replace("T", " ").rstrip("Z"),
    )


@router.get("/greeting", response_class=HTMLResponse, summary="HTML greeting page")
async def greeting():
    return HTMLResponse(content=render_greeting(), media_type="text/html; charset=utf-8")

"""
title: Lemonade Control Panel
author: Open WebUI
version: 0.3.3
description: Interactive panel. Empty input runs a full system overview. Smart timeouts for Pull (30m) and Delete (3m).
"""

import json
import asyncio
from typing import Optional, Callable, Awaitable, List, Dict, Any

import httpx
from pydantic import BaseModel, Field


class Action:
    class Valves(BaseModel):
        BASE_URL: str = Field(
            default="http://localhost:8000",
            description="Lemonade server base URL (without /api/v1).",
        )
        TIMEOUT_SECONDS: int = Field(
            default=20,
            description="Default timeout for standard API requests (health, stats, listing).",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def _emit_status(self, emitter, description: str, done: bool = False):
        if emitter:
            await emitter(
                {"type": "status", "data": {"description": description, "done": done}}
            )

    async def _emit_notification(self, emitter, content: str, ntype: str = "info"):
        if emitter:
            await emitter(
                {"type": "notification", "data": {"type": ntype, "content": content}}
            )

    def _format_model_list(self, data: dict) -> str:
        """Helper to format model JSON into a readable string for the input dialog."""
        try:
            models = data.get("data", [])
            if not models:
                return "No models found."

            lines = []
            for m in models:
                size = m.get("size", "?")
                m_id = m.get("id", "Unknown")
                downloaded = "[DL]" if m.get("downloaded") else ""
                lines.append(f"• {m_id} ({size}GB) {downloaded}")

            limit = 30
            return "\n".join(lines[:limit]) + (
                "\n... (and more)" if len(lines) > limit else ""
            )
        except Exception:
            return "Could not parse model list."

    async def action(
        self,
        body: dict,
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
        __event_call__: Callable[[dict], Awaitable[dict]] = None,
        **kwargs,
    ):
        base_url = self.valves.BASE_URL.rstrip("/")
        base_v1 = f"{base_url}/api/v1"
        endpoint_key = ""

        await self._emit_status(__event_emitter__, "Waiting for input...", False)

        if __event_call__:
            try:
                user_input = await __event_call__(
                    {
                        "type": "input",
                        "data": {
                            "title": "Lemonade Control",
                            "message": "Enter command (pull, delete, health, stats) or leave EMPTY for Overview:",
                            "placeholder": "Leave empty for full system report",
                        },
                    }
                )
                if isinstance(user_input, str):
                    endpoint_key = user_input.strip().lower()
            except Exception as e:
                await self._emit_notification(
                    __event_emitter__, f"Input error: {e}", "error"
                )
                return body

        if not endpoint_key:
            await self._emit_status(
                __event_emitter__, "Fetching System Overview...", False
            )

            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT_SECONDS) as client:
                results = await asyncio.gather(
                    client.get(f"{base_v1}/health"),
                    client.get(f"{base_v1}/stats"),
                    client.get(f"{base_v1}/system-info"),
                    client.get(f"{base_url}/live"),
                    client.get(f"{base_v1}/models"),
                    return_exceptions=True,
                )

                labels = ["Health", "Stats", "System", "Live", "Models"]
                overview_html_parts = []

                for i, res in enumerate(results):
                    label = labels[i]
                    content = ""
                    status_class = "ok"

                    if isinstance(res, Exception):
                        content = f"Error: {str(res)}"
                        status_class = "error"
                    elif res.status_code >= 400:
                        content = f"Error {res.status_code}: {res.text}"
                        status_class = "error"
                    else:
                        try:
                            json_obj = res.json()
                            content = json.dumps(json_obj, indent=2)
                        except:
                            content = res.text

                    overview_html_parts.append(
                        f"""
                        <div class="card">
                            <div class="card-header">
                                <span class="card-title">{label}</span>
                                <span class="indicator {status_class}"></span>
                            </div>
                            <pre>{content}</pre>
                        </div>
                    """
                    )

            html_block = self._build_html_wrapper(
                title="System Overview",
                badge="Report",
                content="".join(overview_html_parts),
                is_grid=True,
            )

            await self._append_to_chat(body, html_block)
            await self._emit_status(__event_emitter__, "Overview Ready", True)
            return body

        payload: Optional[dict] = None
        target_url = ""
        method = "GET"

        # Determine specific timeout for the final execution
        execution_timeout = self.valves.TIMEOUT_SECONDS

        if endpoint_key == "pull":
            execution_timeout = 1800  # 30 minutes for large file downloads
        elif endpoint_key == "delete":
            execution_timeout = 180  # 3 minutes for deletion operations

        async with httpx.AsyncClient(timeout=self.valves.TIMEOUT_SECONDS) as client:

            if endpoint_key == "pull":
                await self._emit_status(
                    __event_emitter__, "Fetching available models...", False
                )
                try:
                    list_resp = await client.get(f"{base_v1}/models?show_all=true")
                    if list_resp.status_code == 200:
                        model_list_str = self._format_model_list(list_resp.json())
                    else:
                        model_list_str = f"Error fetching list: {list_resp.status_code}"

                    if __event_call__:
                        model_name = await __event_call__(
                            {
                                "type": "input",
                                "data": {
                                    "title": "Pull Model",
                                    "message": f"Available Models to Download:\n\n{model_list_str}\n\nEnter ID to pull:",
                                    "placeholder": "Qwen3-14B-GGUF",
                                },
                            }
                        )
                        if model_name:
                            payload = {"model_name": model_name.strip()}
                            target_url = f"{base_v1}/pull"
                            method = "POST"
                        else:
                            return body
                except Exception as e:
                    await self._emit_notification(
                        __event_emitter__, f"Failed to list models: {e}", "error"
                    )
                    return body

            elif endpoint_key == "delete":
                await self._emit_status(
                    __event_emitter__, "Fetching installed models...", False
                )
                try:
                    list_resp = await client.get(f"{base_v1}/models")
                    if list_resp.status_code == 200:
                        model_list_str = self._format_model_list(list_resp.json())
                    else:
                        model_list_str = f"Error fetching list: {list_resp.status_code}"

                    if __event_call__:
                        model_name = await __event_call__(
                            {
                                "type": "input",
                                "data": {
                                    "title": "Delete Model",
                                    "message": f"Installed Models:\n\n{model_list_str}\n\nEnter ID to delete:",
                                    "placeholder": "Qwen3-14B-GGUF",
                                },
                            }
                        )
                        if model_name:
                            payload = {"model_name": model_name.strip()}
                            target_url = f"{base_v1}/delete"
                            method = "POST"
                        else:
                            return body
                except Exception as e:
                    await self._emit_notification(
                        __event_emitter__, f"Failed to list models: {e}", "error"
                    )
                    return body

            else:
                route_map = {
                    "models": f"{base_v1}/models",
                    "health": f"{base_v1}/health",
                    "stats": f"{base_v1}/stats",
                    "system": f"{base_v1}/system-info",
                    "live": f"{base_url}/live",
                }
                target_url = route_map.get(endpoint_key, f"{base_v1}/{endpoint_key}")

            await self._emit_status(
                __event_emitter__, f"Executing {endpoint_key}...", False
            )

            try:
                if method == "GET":
                    resp = await client.get(target_url, timeout=execution_timeout)
                else:
                    resp = await client.post(
                        target_url, json=payload, timeout=execution_timeout
                    )

                status_line = f"Status: {resp.status_code}"
                try:
                    response_text = json.dumps(resp.json(), indent=2)
                except:
                    response_text = resp.text

                html_block = self._build_html_wrapper(
                    title="Lemonade Panel",
                    badge=endpoint_key,
                    content=f"""
                        <div class="card">
                            <div class="card-header"><span class="card-title">Response</span></div>
                            <pre>{response_text}</pre>
                        </div>
                    """,
                )

                await self._append_to_chat(body, html_block)
                await self._emit_notification(
                    __event_emitter__,
                    f"Request completed ({resp.status_code})",
                    "success" if resp.status_code < 400 else "warning",
                )

            except Exception as e:
                err_html = self._build_html_wrapper(
                    title="Error",
                    badge="Fail",
                    content=f"<div class='card'><pre style='color:#ef4444'>{str(e)}</pre></div>",
                )
                await self._append_to_chat(body, err_html)
                await self._emit_notification(
                    __event_emitter__, "Connection Failed", "error"
                )

        await self._emit_status(__event_emitter__, "Done", True)
        return body

    def _build_html_wrapper(self, title, badge, content, is_grid=False):
        """Generates the CSS/HTML for the plugin output."""
        layout_css = (
            """
            .layout { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 10px; }
        """
            if is_grid
            else """
            .layout { display: flex; flex-direction: column; gap: 10px; }
        """
        )

        return f"""```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: sans-serif; background: transparent; margin: 0; color: #e2e8f0; }}
        .panel {{ background: #0f172a; border: 1px solid #1f2937; border-radius: 8px; padding: 12px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #1f2937; padding-bottom: 8px; }}
        .title {{ font-weight: 600; }}
        .badge {{ font-size: 0.75rem; background: #1e293b; padding: 2px 8px; border-radius: 99px; color: #94a3b8; text-transform: uppercase; }}
        
        {layout_css}
        
        .card {{ background: #1e293b50; border: 1px solid #334155; border-radius: 6px; overflow: hidden; }}
        .card-header {{ background: #1e293b; padding: 6px 10px; display: flex; justify-content: space-between; align-items: center; }}
        .card-title {{ font-size: 0.75rem; color: #94a3b8; font-weight: bold; text-transform: uppercase; }}
        .indicator {{ width: 8px; height: 8px; border-radius: 50%; background: #64748b; }}
        .indicator.ok {{ background: #22c55e; box-shadow: 0 0 5px #22c55e40; }}
        .indicator.error {{ background: #ef4444; }}
        
        pre {{ margin: 0; padding: 10px; font-family: monospace; font-size: 0.7rem; white-space: pre-wrap; word-wrap: break-word; color: #cbd5e1; max-height: 300px; overflow-y: auto; }}
        
        /* Custom scrollbar for pre */
        pre::-webkit-scrollbar {{ width: 6px; height: 6px; }}
        pre::-webkit-scrollbar-thumb {{ background: #475569; border-radius: 3px; }}
        pre::-webkit-scrollbar-track {{ background: #0f172a; }}
    </style>
</head>
<body>
    <div class="panel">
        <div class="header">
            <span class="title">🍋 {title}</span>
            <span class="badge">{badge}</span>
        </div>
        <div class="layout">
            {content}
        </div>
    </div>
</body>
</html>
```"""

    async def _append_to_chat(self, body, content):
        if body.get("messages") and isinstance(body["messages"], list):
            body["messages"][-1]["content"] += f"\n\n{content}"

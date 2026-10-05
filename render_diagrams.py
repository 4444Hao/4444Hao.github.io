"""Convert fenced Mermaid source into static SVGs before replacing docs/."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def _cli(root: Path) -> str:
    explicit = os.environ.get("MERMAID_CLI")
    if explicit:
        if Path(explicit).is_file():
            return explicit
        raise ValueError(f"MERMAID_CLI does not exist: {explicit}")
    local = root / "node_modules" / ".bin" / ("mmdc.cmd" if os.name == "nt" else "mmdc")
    if local.is_file():
        return str(local)
    found = shutil.which("mmdc")
    if found:
        return found
    raise ValueError("Mermaid 图表需要先运行 npm ci，再执行 python build.py")


def _browser() -> str | None:
    explicit = os.environ.get("MERMAID_BROWSER")
    if explicit:
        if Path(explicit).is_file():
            return explicit
        raise ValueError(f"MERMAID_BROWSER does not exist: {explicit}")
    for name in ("google-chrome", "chromium", "msedge"):
        found = shutil.which(name)
        if found:
            return found
    edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    return str(edge) if edge.is_file() else None


def render_diagrams(root: Path, sources: dict[str, list[str]]) -> dict[str, bytes]:
    """Return assets only after every graph succeeds, keeping the prior preview intact."""
    if not any(sources.values()):
        return {}
    cli = _cli(root)
    browser = _browser()
    assets: dict[str, bytes] = {}
    with tempfile.TemporaryDirectory(prefix="blog-mermaid-") as temporary:
        work = Path(temporary)
        config = work / "mermaid.json"
        config.write_text(json.dumps({
            "securityLevel": "strict",
            "theme": "base",
            "themeVariables": {
                "fontFamily": "Microsoft YaHei, PingFang SC, sans-serif",
                "primaryColor": "#e8f0e5",
                "primaryTextColor": "#263d2e",
                "primaryBorderColor": "#91aa89",
                "lineColor": "#64846b",
                "secondaryColor": "#f7f6ef",
                "tertiaryColor": "#eef3e9",
            },
        }, ensure_ascii=False), encoding="utf-8")
        launch = work / "puppeteer.json"
        if browser:
            launch.write_text(json.dumps({
                "executablePath": browser,
                "args": ["--no-sandbox"],
            }), encoding="utf-8")
        for slug, diagrams in sources.items():
            for number, source in enumerate(diagrams, 1):
                name = f"{slug}-{number}.svg"
                input_file = work / f"{slug}-{number}.mmd"
                output_file = work / name
                input_file.write_text(source, encoding="utf-8")
                command = [cli, "-i", str(input_file), "-o", str(output_file),
                           "-c", str(config), "-b", "transparent", "--no-font-embed", "-q"]
                if browser:
                    command.extend(["-p", str(launch)])
                try:
                    result = subprocess.run(command, cwd=root, capture_output=True, text=True,
                                            encoding="utf-8", errors="replace", timeout=120)
                except subprocess.TimeoutExpired as exc:
                    raise ValueError(f"{slug}: Mermaid 图表 {number} 渲染超时") from exc
                if result.returncode or not output_file.is_file():
                    detail = (result.stderr or result.stdout).strip()
                    raise ValueError(f"{slug}: Mermaid 图表 {number} 渲染失败\n{detail}")
                svg = output_file.read_bytes()
                if b"<svg" not in svg[:500]:
                    raise ValueError(f"{slug}: Mermaid 图表 {number} 没有生成有效 SVG")
                assets[name] = svg
    return assets

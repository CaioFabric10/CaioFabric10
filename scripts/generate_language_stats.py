"""Generate an SVG language summary from repositories visible to a GitHub token."""

from __future__ import annotations

import html
import json
import os
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen


API_ROOT = "https://api.github.com"
TOKEN = os.environ["METRICS_TOKEN"]
OUTPUT = Path("language-stats.svg")


def request_json(path: str):
    request = Request(
        f"{API_ROOT}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {TOKEN}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def format_size(value: int) -> str:
    return f"{value / 1024:.0f} KB" if value < 1024 * 1024 else f"{value / 1024 / 1024:.1f} MB"


def main() -> None:
    repositories = []
    page = 1
    while True:
        batch = request_json(f"/user/repos?affiliation=owner&per_page=100&page={page}")
        if not batch:
            break
        repositories.extend(repo for repo in batch if not repo["fork"])
        page += 1

    languages: Counter[str] = Counter()
    for repository in repositories:
        data = request_json(f"/repos/{repository['full_name']}/languages")
        languages.update(data)

    total = sum(languages.values())
    top_languages = languages.most_common(8)
    height = 104 + 32 * len(top_languages)
    rows = []
    for index, (language, size) in enumerate(top_languages):
        percent = (size / total * 100) if total else 0
        y = 96 + index * 32
        color = ["#3572A5", "#b07219", "#f34b7d", "#178600", "#f1e05a", "#563d7c", "#e34c26", "#00ADD8"][index]
        rows.append(
            f'<text x="28" y="{y}" class="label">{html.escape(language)}</text>'
            f'<rect x="160" y="{y - 12}" width="250" height="10" rx="5" class="track"/>'
            f'<rect x="160" y="{y - 12}" width="{max(3, 250 * percent / 100):.1f}" height="10" rx="5" fill="{color}"/>'
            f'<text x="470" y="{y}" text-anchor="end" class="percent">{percent:.1f}%</text>'
        )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="500" height="{height}" viewBox="0 0 500 {height}" role="img" aria-label="Linguagens por codigo dos repositorios">
  <style>
    .title {{ fill: #24292f; font: 700 18px -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif; }}
    .subtitle {{ fill: #57606a; font: 12px -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif; }}
    .label {{ fill: #24292f; font: 13px -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif; }}
    .percent {{ fill: #57606a; font: 12px -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif; }}
    .track {{ fill: #d0d7de; }}
    @media (prefers-color-scheme: dark) {{ .title,.label {{ fill: #f0f6fc; }} .subtitle,.percent {{ fill: #8b949e; }} .track {{ fill: #30363d; }} }}
  </style>
  <rect width="100%" height="100%" rx="8" fill="none" stroke="#d0d7de"/>
  <text x="24" y="34" class="title">Linguagens por codigo</text>
  <text x="24" y="56" class="subtitle">{len(repositories)} repositorios analisados · {format_size(total)} de codigo</text>
  {''.join(rows)}
</svg>'''
    OUTPUT.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()

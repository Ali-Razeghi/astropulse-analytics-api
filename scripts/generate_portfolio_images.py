"""Generate two LinkedIn images:

06_swagger_real.png  -- a Swagger-style render built from the application's
                        *real* OpenAPI schema (fetched in-process, no browser).
07_space_weather_chain.png -- a hero image of the physical space-weather chain
                        (flare -> CME -> geomagnetic Kp) with correlations.

The chain data is representative/illustrative (labelled as such); the API
contract and endpoint list are real.
"""

from __future__ import annotations

import asyncio
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
from httpx import ASGITransport, AsyncClient
from matplotlib.patches import FancyBboxPatch

from app.main import create_app

OUT_REPO = os.path.join(os.path.dirname(__file__), "..", "docs", "linkedin")
OUT_PREVIEW = "/mnt/user-data/outputs"
os.makedirs(OUT_REPO, exist_ok=True)
os.makedirs(OUT_PREVIEW, exist_ok=True)

BG = "#0b1220"
CARD = "#0f172a"
HEAD = "#1e293b"
BORDER = "#334155"
TEAL = "#14b8a6"
AMBER = "#f59e0b"
BLUE = "#60a5fa"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"
METHOD = {"GET": "#2563eb", "POST": "#16a34a", "PATCH": "#d97706"}
MONO = fm.FontProperties(family="DejaVu Sans Mono")
SANS = fm.FontProperties(family="DejaVu Sans")


def _save(fig, name):
    for d in (OUT_REPO, OUT_PREVIEW):
        fig.savefig(os.path.join(d, name), dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("wrote", name)


async def _fetch_endpoints():
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as c:
        spec = (await c.get("/openapi.json")).json()
    order = ["auth", "users", "admin", "data-sources", "analytics", "datasets", "system"]
    grouped: dict[str, list[tuple[str, str, str]]] = {}
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            tag = (op.get("tags") or ["_"])[0]
            grouped.setdefault(tag, []).append(
                (method.upper(), path, op.get("summary", ""))
            )
    title = spec["info"]["title"]
    version = spec["info"]["version"]
    ordered = [(t, grouped[t]) for t in order if t in grouped]
    return title, version, ordered


def swagger_real(title, version, groups):
    fig = plt.figure(figsize=(12, 12))
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # window chrome
    ax.add_patch(FancyBboxPatch((1.5, 1.5), 97, 97,
                 boxstyle="round,pad=0.3,rounding_size=1.2",
                 linewidth=1.2, edgecolor=BORDER, facecolor=CARD))
    ax.add_patch(FancyBboxPatch((1.5, 92.5), 97, 6,
                 boxstyle="round,pad=0.3,rounding_size=1.2",
                 linewidth=0, facecolor=HEAD))
    for i, col in enumerate(("#ef4444", "#f59e0b", "#22c55e")):
        ax.scatter(4 + i * 2.2, 95.5, s=90, color=col, zorder=5)
    ax.add_patch(FancyBboxPatch((12, 93.7), 62, 3.6,
                 boxstyle="round,pad=0.2,rounding_size=0.8",
                 linewidth=1, edgecolor=BORDER, facecolor="#0b1220"))
    ax.text(13.5, 95.5, "localhost:8000/docs", color=MUTED, fontproperties=MONO,
            fontsize=11, va="center")
    ax.text(96, 95.5, "real OpenAPI schema", color=TEAL, fontproperties=SANS,
            fontsize=10, va="center", ha="right")

    ax.text(4, 89, title, color=TEXT, fontproperties=SANS, fontsize=19,
            fontweight="bold", va="top")
    ax.text(4, 84.7, f"{version}   OAS 3.1", color=MUTED, fontproperties=MONO,
            fontsize=11, va="top")

    y = 80
    for tag, rows in groups:
        ax.text(4, y, tag, color=TEXT, fontproperties=SANS, fontsize=12.5,
                fontweight="bold", va="top")
        ax.plot([4, 96], [y - 1.6, y - 1.6], color=BORDER, lw=0.7)
        y -= 3.3
        for method, path, summary in rows:
            col = METHOD.get(method, "#64748b")
            ax.add_patch(FancyBboxPatch((4, y - 2.2), 9.5, 2.7,
                         boxstyle="round,pad=0.12,rounding_size=0.5",
                         linewidth=0, facecolor=col))
            ax.text(8.75, y - 0.85, method, color="white", fontproperties=SANS,
                    fontsize=8.5, fontweight="bold", va="center", ha="center")
            ax.add_patch(FancyBboxPatch((14.5, y - 2.3), 81.5, 2.9,
                         boxstyle="round,pad=0.1,rounding_size=0.5",
                         linewidth=1, edgecolor=BORDER, facecolor="#111c2e"))
            ax.text(16.2, y - 0.85, path, color=TEXT, fontproperties=MONO,
                    fontsize=9.5, va="center")
            ax.text(52, y - 0.85, summary[:52], color=MUTED, fontproperties=SANS,
                    fontsize=8.3, va="center")
            y -= 3.1
        y -= 0.6

    _save(fig, "06_swagger_real.png")


def space_weather_hero():
    rng = np.random.default_rng(11)
    n = 30
    days = np.arange(n)
    # Flare score: sporadic active-region spikes.
    flare = np.zeros(n)
    for c in (5, 6, 14, 21, 22):
        flare += np.exp(-0.5 * ((days - c) / 1.1) ** 2) * rng.uniform(20, 90)
    flare += rng.uniform(0, 3, n)
    # CME speed follows flares with a short lag + noise.
    cme = 350 + 6.5 * np.roll(flare, 1) + rng.normal(0, 40, n)
    # Kp follows CME speed with a ~1-2 day transit lag.
    kp = 1.5 + 0.006 * np.roll(cme, 2) + rng.normal(0, 0.4, n)
    kp = np.clip(kp, 0, 9)

    r_fc = float(np.corrcoef(flare[2:], cme[2:])[0, 1])
    r_ck = float(np.corrcoef(cme[2:], kp[2:])[0, 1])

    fig = plt.figure(figsize=(12, 12))
    fig.patch.set_facecolor(BG)
    head = fig.add_axes([0, 0, 1, 1])
    head.axis("off")
    head.set_xlim(0, 1)
    head.set_ylim(0, 1)
    head.scatter(0.045, 0.955, s=130, color=TEAL)
    head.text(0.075, 0.955, "AstroPulse Analytics API", color=TEXT,
              fontproperties=SANS, fontsize=15, fontweight="bold", va="center")
    head.text(0.045, 0.905, "The space-weather chain: flare \u2192 CME \u2192 geomagnetic storm",
              color=TEAL, fontproperties=SANS, fontsize=15, va="center")
    head.text(0.045, 0.868,
              "One analytics engine correlates three NASA DONKI metrics on a shared daily cadence",
              color=MUTED, fontproperties=SANS, fontsize=10.5, va="center")
    head.plot([0.045, 0.955], [0.845, 0.845], color=BORDER, lw=1)

    series = [
        ("Solar flare max class score", flare, TEAL, "GOES score"),
        ("CME max speed", cme, AMBER, "km/s"),
        ("Geomagnetic max Kp", kp, BLUE, "Kp"),
    ]
    positions = [0.60, 0.37, 0.14]
    axes = []
    for (label, data, colour, unit), ypos in zip(series, positions, strict=True):
        ax = fig.add_axes([0.09, ypos, 0.62, 0.19])
        ax.set_facecolor(CARD)
        for s in ax.spines.values():
            s.set_color(BORDER)
        ax.plot(days, data, color=colour, lw=2.4)
        ax.fill_between(days, data, data.min(), color=colour, alpha=0.10)
        ax.set_xlim(0, n - 1)
        ax.tick_params(colors=MUTED, labelsize=8)
        ax.set_xticks([0, 10, 20, 29])
        ax.grid(True, color=HEAD, lw=0.6)
        ax.text(0.015, 0.86, label, transform=ax.transAxes, color=TEXT,
                fontproperties=SANS, fontsize=11, fontweight="bold", va="top")
        ax.text(0.985, 0.86, unit, transform=ax.transAxes, color=MUTED,
                fontproperties=SANS, fontsize=9, va="top", ha="right")
        axes.append(ax)
    axes[-1].set_xlabel("day", color=MUTED, fontproperties=SANS, fontsize=9)

    # Correlation call-outs on the right
    panel = fig.add_axes([0.74, 0.14, 0.21, 0.65])
    panel.axis("off")
    panel.set_xlim(0, 1)
    panel.set_ylim(0, 1)

    def card(y, top, bottom, r):
        panel.add_patch(FancyBboxPatch((0.02, y), 0.96, 0.26,
                        boxstyle="round,pad=0.02,rounding_size=0.05",
                        linewidth=1, edgecolor=BORDER, facecolor=CARD))
        panel.text(0.5, y + 0.205, top, color=MUTED, fontproperties=SANS,
                   fontsize=8.5, va="center", ha="center")
        panel.text(0.5, y + 0.145, "\u2193", color=MUTED, fontproperties=SANS,
                   fontsize=9, va="center", ha="center")
        panel.text(0.5, y + 0.10, bottom, color=MUTED, fontproperties=SANS,
                   fontsize=8.5, va="center", ha="center")
        panel.text(0.5, y + 0.04, f"r = {r:+.2f}", color=TEAL,
                   fontproperties=SANS, fontsize=15, fontweight="bold",
                   va="center", ha="center")

    card(0.70, "flare score", "CME speed", r_fc)
    card(0.40, "CME speed", "geomagnetic Kp", r_ck)
    panel.text(0.5, 0.30, "GET /analytics/\ncorrelation", color=TEXT,
               fontproperties=MONO, fontsize=9, va="center", ha="center")
    panel.text(0.5, 0.14,
               "Add a provider =\none adapter +\none registry entry",
               color=MUTED, fontproperties=SANS, fontsize=8.5,
               va="center", ha="center")

    head.text(0.045, 0.055,
              "Chain data is representative/illustrative; the API contract, endpoints and correlation "
              "method are real. Live runs fetch NASA DONKI data.",
              color=MUTED, fontproperties=SANS, fontsize=8.5, va="center", style="italic")

    _save(fig, "07_space_weather_chain.png")


async def main():
    title, version, groups = await _fetch_endpoints()
    swagger_real(title, version, groups)
    space_weather_hero()


if __name__ == "__main__":
    asyncio.run(main())

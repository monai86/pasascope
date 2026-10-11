"""Radar / Spider chart renderer for one session's measured language-sample values."""

from __future__ import annotations

import math
from typing import Any
import tkinter as tk


# Full-scale value of each axis. These are drawing ranges chosen so the six
# measures fit one chart; they are not norms, targets or expected values.
AXIS_FULL_SCALE = {
    "mlu_words": 6.0,
    "ttr": 1.0,
    "turn_taking_ratio": 1.0,
    "intelligibility_rate": 1.0,
    "speech_rate_wpm": 150.0,
    "f0_iqr_hz": 100.0,
}


def _measured(metrics: dict[str, Any], key: str) -> float | None:
    value = metrics.get(key)
    return float(value) if value is not None and value != "N/A" else None


def _has_child_data(metrics: dict[str, Any]) -> bool:
    return bool(metrics and (metrics.get("total_child_utterances") or 0) > 0)


def _axes(metrics: dict[str, Any], labels: dict[str, str]) -> list[dict[str, Any]]:
    has_child_data = _has_child_data(metrics)
    units = {"mlu_words": "words", "speech_rate_wpm": "wpm", "f0_iqr_hz": "Hz"}
    return [
        {
            "label": labels[key],
            "val": _measured(metrics, key) if has_child_data else None,
            "full_scale": full_scale,
            "unit": units.get(key, ""),
        }
        for key, full_scale in AXIS_FULL_SCALE.items()
    ]


def _fraction(axis: dict[str, Any]) -> float:
    """Position of the value along its axis, 0 (centre) to 1 (outer ring)."""
    if axis["val"] is None:
        return 0.0
    return max(0.0, min(1.0, axis["val"] / axis["full_scale"]))


_CANVAS_LABELS = {
    "mlu_words": "MLU-w\n(Sentence)",
    "ttr": "TTR\n(Vocab)",
    "turn_taking_ratio": "Turn-Taking\n(Reciprocity)",
    "intelligibility_rate": "Intelligibility\n(Clarity)",
    "speech_rate_wpm": "Speech Rate\n(WPM)",
    "f0_iqr_hz": "Prosody IQR\n(F0 Range)",
}
_SVG_LABELS = {
    "mlu_words": "MLU-w",
    "ttr": "TTR",
    "turn_taking_ratio": "Turn-Taking",
    "intelligibility_rate": "Intelligibility",
    "speech_rate_wpm": "Speech Rate",
    "f0_iqr_hz": "Prosody IQR",
}
_RING_FRACTIONS = [0.25, 0.5, 0.75, 1.0]


class RadarChartRenderer:
    """Renders a radar chart of one session's measured values. No norm is drawn."""

    def __init__(
        self,
        canvas: tk.Canvas,
        summary_widget: tk.Text | None = None,
        font_family: str = "Helvetica",
    ) -> None:
        self.canvas = canvas
        self.summary_widget = summary_widget
        self.font_family = font_family

    def draw(self, metrics: dict[str, Any]) -> None:
        """Render the session's measured values on fixed display scales."""
        self.canvas.delete("all")
        self.canvas.update_idletasks()
        width = max(280, self.canvas.winfo_width()) if self.canvas.winfo_width() > 1 else 380
        height = max(240, self.canvas.winfo_height()) if self.canvas.winfo_height() > 1 else 330
        cx, cy = width / 2, height / 2 - 5
        radius = max(60, min(cx, cy) - 45)

        has_child_data = _has_child_data(metrics)
        axes = _axes(metrics, _CANVAS_LABELS)
        n = len(axes)

        # Concentric grid rings
        for r_ratio in _RING_FRACTIONS:
            r = radius * r_ratio
            pts = []
            for i in range(n):
                angle = -math.pi / 2 + (2 * math.pi * i / n)
                pts.extend([cx + r * math.cos(angle), cy + r * math.sin(angle)])
            self.canvas.create_polygon(pts, fill="", outline="#e2e8f0", width=1)

        # Spokes and labels
        for i, ax in enumerate(axes):
            angle = -math.pi / 2 + (2 * math.pi * i / n)
            self.canvas.create_line(
                cx, cy, cx + radius * math.cos(angle), cy + radius * math.sin(angle),
                fill="#e2e8f0", width=1
            )
            x_lbl = cx + (radius + 22) * math.cos(angle)
            y_lbl = cy + (radius + 22) * math.sin(angle)
            self.canvas.create_text(
                x_lbl, y_lbl,
                text=ax["label"],
                font=(self.font_family, 8, "bold"),
                fill="#475569",
                justify=tk.CENTER,
            )

        # Child Session Data Polygon
        if has_child_data:
            child_pts = []
            for i, ax in enumerate(axes):
                angle = -math.pi / 2 + (2 * math.pi * i / n)
                r_child = radius * _fraction(ax)
                child_pts.extend([cx + r_child * math.cos(angle), cy + r_child * math.sin(angle)])

            if len(child_pts) >= 6:
                self.canvas.create_polygon(child_pts, fill="#e0f2fe", outline="#0284c7", width=2.5)

            for i, ax in enumerate(axes):
                if ax["val"] is not None:
                    px, py = child_pts[i * 2], child_pts[i * 2 + 1]
                    self.canvas.create_oval(
                        px - 3.5, py - 3.5, px + 3.5, py + 3.5,
                        fill="#0369a1", outline="white", width=1
                    )

            # Summary text
            if self.summary_widget:
                self.summary_widget.config(state=tk.NORMAL)
                self.summary_widget.delete("1.0", tk.END)
                self.summary_widget.insert(tk.END, "Session Profile (measured values):\n\n", "title")
                self.summary_widget.insert(tk.END, "■ Blue Shaded Area: This Session\n\n", "blue")
                for ax in axes:
                    lbl_clean = ax["label"].split("\n")[0]
                    unit_str = f" {ax['unit']}" if ax["unit"] else ""
                    if ax["val"] is not None:
                        self.summary_widget.insert(
                            tk.END,
                            f"● {lbl_clean}: {ax['val']}{unit_str} (axis 0–{ax['full_scale']:g}{unit_str})\n",
                        )
                    else:
                        self.summary_widget.insert(tk.END, f"○ {lbl_clean}: not measured\n")
                self.summary_widget.insert(
                    tk.END,
                    "\nAxis ranges are drawing scales only. No Thai reference norm exists, "
                    "so this chart does not compare the child with other children.\n",
                )
                self.summary_widget.config(state=tk.DISABLED)
        else:
            # Clean Empty State
            self.canvas.create_rectangle(
                cx - 130, cy - 26, cx + 130, cy + 26,
                fill="#f8fafc", outline="#cbd5e1", width=1
            )
            self.canvas.create_text(
                cx, cy - 7,
                text="No evaluation data in this session",
                font=(self.font_family, 9, "bold"),
                fill="#64748b",
            )
            self.canvas.create_text(
                cx, cy + 10,
                text="(Ingest audio or transcript in Tab 2)",
                font=(self.font_family, 8),
                fill="#94a3b8",
            )

            if self.summary_widget:
                self.summary_widget.config(state=tk.NORMAL)
                self.summary_widget.delete("1.0", tk.END)
                self.summary_widget.insert(tk.END, "Session Profile (measured values):\n\n", "title")
                self.summary_widget.insert(tk.END, "No Evaluation Data Available\n\n", "title")
                self.summary_widget.insert(
                    tk.END,
                    "Please ingest session audio or dialogue transcript in Tab 2 (Ingest Material) to compute LSA metrics and acoustic prosody profile.",
                )
                self.summary_widget.config(state=tk.DISABLED)

    @staticmethod
    def render_svg(metrics: dict[str, Any], width: int = 520, height: int = 340) -> str:
        """Generate a standalone SVG of the session profile for printable HTML reports.

        The default width leaves room for the side axis labels, which are
        anchored outward from the chart and were clipped at 400.
        """
        cx, cy = width / 2, height / 2 - 12
        radius = max(60, min(cx, cy) - 45)

        has_child_data = _has_child_data(metrics)
        axes = _axes(metrics, _SVG_LABELS)
        n = len(axes)
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" style="font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; display: inline-block;">',
            f'<rect width="{width}" height="{height}" fill="#ffffff" rx="8" />',
        ]

        # Background grid rings
        for r_ratio in _RING_FRACTIONS:
            r = radius * r_ratio
            pts = []
            for i in range(n):
                angle = -math.pi / 2 + (2 * math.pi * i / n)
                pts.append(f"{cx + r * math.cos(angle):.1f},{cy + r * math.sin(angle):.1f}")
            svg_parts.append(f'<polygon points="{" ".join(pts)}" fill="none" stroke="#e2e8f0" stroke-width="1" />')

        # Axis rays & labels
        for i, ax in enumerate(axes):
            angle = -math.pi / 2 + (2 * math.pi * i / n)
            x_end = cx + radius * math.cos(angle)
            y_end = cy + radius * math.sin(angle)
            svg_parts.append(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{x_end:.1f}" y2="{y_end:.1f}" stroke="#cbd5e1" stroke-width="1" />')

            lbl_r = radius + 22
            lx = cx + lbl_r * math.cos(angle)
            ly = cy + lbl_r * math.sin(angle)
            anchor = "middle" if abs(math.cos(angle)) < 0.2 else ("start" if math.cos(angle) > 0 else "end")
            val_str = f" ({ax['val']:.1f})" if ax["val"] is not None else ""
            svg_parts.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-size="11" font-weight="600" fill="#475569">{ax["label"]}{val_str}</text>')

        # Child polygon
        if has_child_data:
            child_pts = []
            for i, ax in enumerate(axes):
                angle = -math.pi / 2 + (2 * math.pi * i / n)
                r = radius * _fraction(ax)
                px = cx + r * math.cos(angle)
                py = cy + r * math.sin(angle)
                child_pts.append((px, py))
            pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in child_pts)
            svg_parts.append(f'<polygon points="{pts_str}" fill="rgba(3, 105, 161, 0.25)" stroke="#0284c7" stroke-width="2.5" />')
            for px, py in child_pts:
                svg_parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="#0369a1" stroke="#ffffff" stroke-width="1.5" />')
        else:
            svg_parts.append(f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" font-size="12" fill="#94a3b8">No session evaluation data</text>')

        # Legend
        svg_parts.append(f'<g transform="translate({cx - 150}, {height - 18})">')
        svg_parts.append('<rect x="0" y="2" width="16" height="8" fill="rgba(3, 105, 161, 0.4)" stroke="#0284c7" stroke-width="1.5" />')
        svg_parts.append('<text x="22" y="10" font-size="10" fill="#0369a1">This session — measured values, no norm comparison</text>')
        svg_parts.append('</g>')

        svg_parts.append('</svg>')
        return "\n".join(svg_parts)

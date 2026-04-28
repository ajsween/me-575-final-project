"""Generate a clean, centered architecture diagram for SafeJudge."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# ── Canvas ──
fig, ax = plt.subplots(figsize=(16, 24))
ax.set_xlim(0, 16)
ax.set_ylim(0, 24)
ax.axis("off")
fig.patch.set_facecolor("white")

# ── Palette ──
PAL = {
    "blue":    ("#1565c0", "#e3f2fd"),
    "purple":  ("#6a1b9a", "#f3e5f5"),
    "green":   ("#2e7d32", "#e8f5e9"),
    "orange":  ("#e65100", "#fff3e0"),
    "red":     ("#c62828", "#ffebee"),
    "teal":    ("#00695c", "#e0f2f1"),
    "amber":   ("#f57f17", "#fffde7"),
    "gray":    ("#455a64", "#eceff1"),
}
CX = 8.0  # center x


def rbox(x, y, w, h, title, subtitle=None, pal="blue", title_size=11, sub_size=8):
    fg, bg = PAL[pal]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                                 facecolor=bg, edgecolor=fg, linewidth=2))
    if subtitle:
        ax.text(x + w / 2, y + h / 2 + 0.22, title, ha="center", va="center",
                fontsize=title_size, fontweight="bold", color=fg)
        ax.text(x + w / 2, y + h / 2 - 0.22, subtitle, ha="center", va="center",
                fontsize=sub_size, color="#616161", style="italic")
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
                fontsize=title_size, fontweight="bold", color=fg)


def varrow(x, y_top, y_bot, label=None):
    ax.annotate("", xy=(x, y_bot), xytext=(x, y_top),
                arrowprops=dict(arrowstyle="-|>", color="#455a64", lw=2))
    if label:
        ax.text(x + 0.15, (y_top + y_bot) / 2, label, fontsize=8,
                color="#455a64", style="italic", va="center")


def harrow(x_l, x_r, y):
    ax.annotate("", xy=(x_r, y), xytext=(x_l, y),
                arrowprops=dict(arrowstyle="-|>", color="#455a64", lw=2))


def darrow(x1, y1, x2, y2, color="#455a64", dashed=False):
    style = "dashed" if dashed else "solid"
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.5, linestyle=style))


# ═══════════════════════════════════════════════════
# TITLE
# ═══════════════════════════════════════════════════
ax.text(CX, 23.4, "SafeJudge Evaluation Pipeline", ha="center",
        fontsize=20, fontweight="bold", color=PAL["blue"][0])
ax.text(CX, 22.9, "Multi-Model LLM-as-a-Judge for Automated AI Safety Evaluation",
        ha="center", fontsize=10, color="#757575", style="italic")

# ═══════════════════════════════════════════════════
# ROW 1 — Dataset → Eval Runner
# ═══════════════════════════════════════════════════
Y1 = 21.5
rbox(2.0, Y1, 4.0, 1.0, "Labeled Test Dataset", "105 cases · 7 categories", pal="blue")
rbox(10.0, Y1, 4.0, 1.0, "Eval Runner", "sequential batch execution", pal="blue")
harrow(6.0, 10.0, Y1 + 0.5)

# ═══════════════════════════════════════════════════
# ROW 2 — Mode Selection (centered badges)
# ═══════════════════════════════════════════════════
Y2 = 20.1
varrow(CX, Y1, Y2 + 0.6)
ax.text(CX, Y2 + 0.25, "Runs each test case through the SUT in each selected mode:",
        ha="center", fontsize=9, color="#616161")

mw, mh, mg = 3.0, 0.55, 0.4
total_w = 3 * mw + 2 * mg
mx_start = CX - total_w / 2
for i, (mode, pn) in enumerate([("single", "purple"), ("ensemble", "orange"),
                                 ("safety_classifier", "red")]):
    mx = mx_start + i * (mw + mg)
    fg, bg = PAL[pn]
    ax.add_patch(FancyBboxPatch((mx, Y2 - 0.55), mw, mh, boxstyle="round,pad=0.1",
                                 facecolor=bg, edgecolor=fg, linewidth=1.5))
    ax.text(mx + mw / 2, Y2 - 0.55 + mh / 2, mode, ha="center", va="center",
            fontsize=9, fontweight="bold", color=fg, family="monospace")

# ═══════════════════════════════════════════════════
# ROW 3 — SUT (large container)
# ═══════════════════════════════════════════════════
SUT_Y, SUT_H = 14.5, 4.8
ax.add_patch(FancyBboxPatch((1.0, SUT_Y), 14.0, SUT_H, boxstyle="round,pad=0.2",
                             facecolor="#fafafa", edgecolor=PAL["purple"][0], linewidth=2.5))
ax.text(CX, SUT_Y + SUT_H - 0.35, "analyze-prompt-intent  (System Under Test)",
        ha="center", fontsize=13, fontweight="bold", color=PAL["purple"][0])
varrow(CX, Y2 - 0.55, SUT_Y + SUT_H)

# Internal: Rule → Deobfuscation → Primary LLM
PIPE_Y = 17.4
bw, bh = 3.2, 1.0
rbox(1.8, PIPE_Y, bw, bh, "Rule-Based\nFast Pass", "keywords, entropy",
     pal="purple", title_size=9, sub_size=7)
rbox(6.4, PIPE_Y, bw, bh, "Deobfuscation\nPreprocessing", "15 decoders",
     pal="purple", title_size=9, sub_size=7)
rbox(11.0, PIPE_Y, bw, bh, "Primary LLM", "gpt-oss:latest",
     pal="purple", title_size=9, sub_size=7)
harrow(1.8 + bw, 6.4, PIPE_Y + bh / 2)
harrow(6.4 + bw, 11.0, PIPE_Y + bh / 2)

# Optional branches
BR_Y = 15.3
br_bw, br_bh = 4.5, 1.1
rbox(1.5, BR_Y, br_bw, br_bh, "Secondary LLM  (qwen3:32b)",
     "OR-merge with primary result", pal="orange", title_size=9, sub_size=7)
rbox(10.0, BR_Y, br_bw, br_bh, "GPT-OSS-Safeguard",
     "can force harmful_content=True", pal="red", title_size=9, sub_size=7)
darrow(12.0, PIPE_Y, 3.75, BR_Y + br_bh, color=PAL["orange"][0], dashed=True)
darrow(12.8, PIPE_Y, 12.25, BR_Y + br_bh, color=PAL["red"][0], dashed=True)
ax.text(3.75, BR_Y + br_bh + 0.15, "ensemble mode", fontsize=7,
        ha="center", color=PAL["orange"][0], fontweight="bold")
ax.text(12.25, BR_Y + br_bh + 0.15, "safety_classifier mode", fontsize=7,
        ha="center", color=PAL["red"][0], fontweight="bold")

# Output schema
ax.text(CX, SUT_Y + 0.25,
        "Output:  { jailbreak, prompt_injection, harmful_content, confidence, reasoning, attack_types }",
        ha="center", fontsize=7.5, color="#616161", family="monospace",
        bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="#bdbdbd", linewidth=0.5))

# ═══════════════════════════════════════════════════
# ARROW — SUT → Judge
# ═══════════════════════════════════════════════════
JUDGE_Y, JUDGE_H = 12.2, 1.8
varrow(CX, SUT_Y, JUDGE_Y + JUDGE_H, label="JSON via stdout")

# ═══════════════════════════════════════════════════
# ROW 4 — LLM-as-a-Judge
# ═══════════════════════════════════════════════════
ax.add_patch(FancyBboxPatch((2.0, JUDGE_Y), 12.0, JUDGE_H, boxstyle="round,pad=0.15",
                             facecolor=PAL["green"][1], edgecolor=PAL["green"][0], linewidth=2))
ax.text(CX, JUDGE_Y + JUDGE_H - 0.4, "LLM-as-a-Judge", ha="center",
        fontsize=13, fontweight="bold", color=PAL["green"][0])
ax.text(CX, JUDGE_Y + JUDGE_H - 0.85, "(gpt-oss:latest  ·  temperature=0)", ha="center",
        fontsize=9, color="#616161", style="italic")
ax.text(CX, JUDGE_Y + 0.3,
        "Scores on 5 dimensions (0\u20135):  correctness · reasoning · calibration · completeness · overall",
        ha="center", fontsize=8, color=PAL["green"][0])

# ═══════════════════════════════════════════════════
# ARROWS — Judge → 3 outputs
# ═══════════════════════════════════════════════════
OUT_Y, OUT_H = 8.7, 1.8
out_cx = [3.5, 8.0, 12.5]
out_w = 3.8
darrow(CX - 2, JUDGE_Y, out_cx[0], OUT_Y + OUT_H)
varrow(CX, JUDGE_Y, OUT_Y + OUT_H)
darrow(CX + 2, JUDGE_Y, out_cx[2], OUT_Y + OUT_H)

# ═══════════════════════════════════════════════════
# ROW 5 — Three output boxes
# ═══════════════════════════════════════════════════
rbox(out_cx[0] - out_w / 2, OUT_Y, out_w, OUT_H,
     "Metric\nAggregation", "accuracy, F1, recall, FPR,\ncalibration, cross-model",
     pal="teal", title_size=10, sub_size=8)
rbox(out_cx[1] - out_w / 2, OUT_Y, out_w, OUT_H,
     "Evidently AI\nReports", "classification, drift,\nconfusion, radar, dashboards",
     pal="teal", title_size=10, sub_size=8)
rbox(out_cx[2] - out_w / 2, OUT_Y, out_w, OUT_H,
     "Release Gate\nLogic", "4 blocking gates +\n2 advisory gates",
     pal="teal", title_size=10, sub_size=8)

# ═══════════════════════════════════════════════════
# ROW 6 — GO / NO GO decision (centered)
# ═══════════════════════════════════════════════════
DEC_Y, DEC_H = 6.8, 1.2
dec_w = 7.0
varrow(out_cx[2], OUT_Y, DEC_Y + DEC_H)
ax.add_patch(FancyBboxPatch((CX - dec_w / 2, DEC_Y), dec_w, DEC_H,
                             boxstyle="round,pad=0.15",
                             facecolor=PAL["amber"][1], edgecolor=PAL["amber"][0], linewidth=2))
ax.text(CX, DEC_Y + DEC_H / 2 + 0.15, "GO  /  NO GO  /  GO WITH MITIGATION",
        ha="center", va="center", fontsize=11, fontweight="bold", color=PAL["orange"][0])
ax.text(CX, DEC_Y + DEC_H / 2 - 0.25, "Session 6 two-tier threshold system",
        ha="center", va="center", fontsize=8, color="#757575", style="italic")

# ═══════════════════════════════════════════════════
# ROW 7 — Evidence Package (centered)
# ═══════════════════════════════════════════════════
EVD_Y, EVD_H = 5.0, 1.2
evd_w = 7.0
varrow(CX, DEC_Y, EVD_Y + EVD_H)
rbox(CX - evd_w / 2, EVD_Y, evd_w, EVD_H,
     "Evidence Package", "run ID  \u00b7  SHA-256 hashes  \u00b7  config snapshot",
     pal="blue", title_size=11, sub_size=9)

# ═══════════════════════════════════════════════════
# LEGEND
# ═══════════════════════════════════════════════════
leg_x, leg_y = 1.0, 3.8
ax.text(leg_x, leg_y, "Legend", fontsize=10, fontweight="bold", color="#455a64")
items = [
    ("blue",   "SafeJudge pipeline components"),
    ("purple", "System Under Test \u2014 always active"),
    ("green",  "LLM-as-a-Judge evaluator"),
    ("orange", "Optional: ensemble mode (--ensemble)"),
    ("red",    "Optional: safety classifier mode (--use-safety-classifier)"),
    ("teal",   "Output, reporting & gates"),
    ("amber",  "Release decision"),
]
for i, (pn, label) in enumerate(items):
    iy = leg_y - 0.45 * (i + 1)
    fg, bg = PAL[pn]
    ax.add_patch(FancyBboxPatch((leg_x, iy - 0.1), 0.4, 0.25,
                                 boxstyle="round,pad=0.04", facecolor=bg, edgecolor=fg, linewidth=1))
    ax.text(leg_x + 0.55, iy + 0.02, label, fontsize=8, va="center", color="#455a64")

# ═══════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════
out_path = "evidence/architecture_diagram.png"
fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Saved: {out_path}")

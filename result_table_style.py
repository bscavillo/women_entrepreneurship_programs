"""Styled result-table graphics for the thesis.

`save_result_table` renders a regression or F-test summary as a PNG in the style
of the WES Female Founder Rates paper (the old ``add_heading(title, 0)`` docx
output): a plain dark-blue title, a thin blue rule separating it from the body,
then the *unchanged* statsmodels summary text (monospace). No background fill.

Colors match Word's "Title" style used by the original notebooks:
title text ``#17365D`` and the bottom-border rule ``#4F81BD`` (theme accent 1).

The body is passed straight through from ``model.summary()`` / ``f_test.summary()``
so the table is imported unchanged from the notebook output, as the thesis states.
Only matplotlib is required.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

TITLE_COLOR = "#17365D"   # dark blue title text
RULE_COLOR = "#C6C6C6"    # thin light-gray rule under the title (matches WES paper)
BODY_COLOR = "#111111"


def _measure(fig, txt, **kw):
    """Return (width_in, height_in) of a text string on ``fig``'s canvas."""
    t = fig.text(0, 0, txt, ha="left", va="bottom", **kw)
    fig.canvas.draw()
    bb = t.get_window_extent(fig.canvas.get_renderer())
    t.remove()
    return bb.width / fig.dpi, bb.height / fig.dpi


def save_result_table(title, summary, out_path, *, fontsize=11, title_fontsize=25):
    """Render ``summary`` under a blue ``title`` and thin rule; save to ``out_path``.

    Parameters
    ----------
    title : str
        Plain heading naming what is tested, e.g. "OLS Regression: Canadian DiD".
    summary : object
        A statsmodels ``Summary`` (``res.summary()``) or the ``f_test.summary()``
        string. Converted with ``str()`` and rendered unchanged.
    out_path : str | os.PathLike
        Destination PNG path.
    fontsize : int
        Point size of the monospace body text.
    title_fontsize : int
        Maximum point size of the title (shrunk to fit the body width if needed).
    """
    body = str(summary)
    lines = body.split("\n")
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and lines[-1].strip() == "":
        lines.pop()
    text = "\n".join(lines)

    dpi = 200
    left = right = 0.34

    # Measure body and title on a scratch canvas so the figure fits exactly.
    scratch = plt.figure(figsize=(80, 80), dpi=dpi)
    body_w, body_h = _measure(scratch, text, family="monospace", fontsize=fontsize)
    title_w, _ = _measure(scratch, title, family="DejaVu Sans", fontsize=title_fontsize)

    # Keep the figure as wide as the table; shrink the title to fit that width.
    if title_w > body_w and title_w > 0:
        title_fontsize = max(11.0, title_fontsize * body_w / title_w)
    _, title_h = _measure(scratch, title, family="DejaVu Sans", fontsize=title_fontsize)
    # Final title width may still exceed body width only if it hit the 11pt floor.
    title_w, _ = _measure(scratch, title, family="DejaVu Sans", fontsize=title_fontsize)
    plt.close(scratch)

    content_w = max(body_w, title_w)
    fig_w = content_w + left + right

    top_pad = 0.24
    rule_gap_above = 0.12
    rule_gap_below = 0.20
    bottom_pad = 0.26
    fig_h = top_pad + title_h + rule_gap_above + rule_gap_below + body_h + bottom_pad

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
    trans = fig.dpi_scale_trans

    # Title: plain dark-blue text, left aligned, not bold.
    y = fig_h - top_pad
    fig.text(left, y, title, transform=trans, ha="left", va="top",
             color=TITLE_COLOR, fontsize=title_fontsize, family="DejaVu Sans")

    # Thin light-gray hairline under the title, spanning the content width.
    rule_y = y - title_h - rule_gap_above
    fig.add_artist(Line2D([left, left + content_w], [rule_y, rule_y],
                          transform=trans, color=RULE_COLOR, linewidth=0.8,
                          solid_capstyle="butt", zorder=2))

    # Body: unchanged summary, monospace, top-left.
    fig.text(left, rule_y - rule_gap_below, text, transform=trans,
             ha="left", va="top", family="monospace",
             fontsize=fontsize, color=BODY_COLOR)

    fig.savefig(out_path, dpi=dpi, facecolor="white")
    plt.close(fig)
    return out_path

#!/usr/bin/env python3
"""Build the MPC Codex excerpt PDF from verified local Markdown drafts."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
import shutil


TITLE = "The MPC Codex: First Track Fast"
SUBTITLE = (
    "A Field Guide for Akai MPC 3.5+ -- Get Your First Complete Sketch "
    "Done Without Getting Lost in Menus"
)
AUTHOR = "Frank Jarczynski"
URL_PLACEHOLDER = "[gumroad-url]"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def require_file(path: Path) -> None:
    if not path.exists():
        fail(f"Required input file missing: {path}")
    if not path.is_file():
        fail(f"Required input is not a file: {path}")
    if path.stat().st_size == 0:
        fail(f"Required input file is empty: {path}")


def require_command(command: str) -> str:
    found = shutil.which(command)
    if not found:
        fail(f"Required command not found: {command}")
    return found


def read_markdown(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        fail(f"Markdown input has no text: {path}")
    return text


def cover_page() -> str:
    return rf"""\begin{{titlepage}}
\thispagestyle{{empty}}
\begin{{center}}
\vspace*{{1.6in}}

{{\Huge\bfseries {TITLE}\par}}

\vspace{{0.35in}}

{{\Large {SUBTITLE}\par}}

\vspace{{0.65in}}

{{\large {AUTHOR}\par}}

\vspace{{0.25in}}

{{\large {URL_PLACEHOLDER}\par}}

\vfill

{{\small Built from The MPC Codex source chapters: Modern MPC Foundations and Your First Complete Track Fast.\par}}

\end{{center}}
\end{{titlepage}}
"""


def intro_page() -> str:
    return """# How to Use This Guide

This excerpt is built for one job: help you stop wandering through MPC menus and finish a complete first sketch with a repeatable workflow.

Read Chapter 1 first if you need orientation. It explains the modern MPC landscape, what different standalone models have in common, which hardware differences actually matter, and how to choose a starting workflow without overthinking the machine.

Read Chapter 2 with your MPC nearby. The goal is not to memorize every feature. The goal is to move from a blank project into a saved, recoverable 60-second sketch using a simple creation loop: set the session, build the drums, add bass or harmony, create a variation, add one transition move, and save the project properly.

Use the checklists and boss battles as action prompts. If a section gives you a choice, make the choice quickly and keep building. The first win is not a perfect beat. The first win is proving that you can start, structure, save, and reopen a real idea without losing momentum.

\\newpage
"""


def outro_page() -> str:
    return """# What Comes Next

When your first sketch is saved, the next problem is keeping your MPC world usable. A creative setup gets slower when projects, samples, expansions, exports, and copied folders pile up without a system.

The next MPC Codex release will go deeper into sampling, drum programs, arrangement, effects, export workflow, performance control, troubleshooting, and power-user templates.

If your MPC drive is already cluttered, Frank also offers a $79 MPC Library Cleanup Audit. It is a read-only, safety-first review of an MPC content drive. The audit is designed to show duplicate clutter, protected project areas, cleanup opportunities, and risk notes before anything is deleted.

Use this line on the Gumroad thank-you page:

Need your MPC drive cleaned up without risking projects? Ask about the $79 MPC Library Cleanup Audit.

\\newpage
"""


def build_combined_markdown(ch01: Path, ch02: Path) -> str:
    return "\n\n".join(
        [
            intro_page(),
            read_markdown(ch01),
            "\\newpage\n",
            read_markdown(ch02),
            "\\newpage\n",
            outro_page(),
        ]
    )


def latex_document(body: str) -> str:
    return rf"""\documentclass[11pt]{{article}}
\usepackage[margin=0.82in]{{geometry}}
\usepackage{{fontspec}}
\setmainfont{{Helvetica}}
\usepackage{{hyperref}}
\usepackage{{longtable,booktabs,array,calc}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\usepackage{{parskip}}
\newcounter{{none}}
\hypersetup{{colorlinks=true,linkcolor=black,urlcolor=blue}}
\titleformat{{\section}}{{\Large\bfseries}}{{}}{{0pt}}{{}}
\titleformat{{\subsection}}{{\large\bfseries}}{{}}{{0pt}}{{}}
\titleformat{{\subsubsection}}{{\normalsize\bfseries}}{{}}{{0pt}}{{}}
\begin{{document}}
{cover_page()}
{body}
\end{{document}}
"""


def run_pandoc(source_md: Path, output_pdf: Path, build_dir: Path) -> None:
    require_command("pandoc")
    require_command("xelatex")
    body_tex = build_dir / "mpc-codex-first-track-fast-v1-body.tex"
    full_tex = build_dir / "mpc-codex-first-track-fast-v1.tex"
    cmd = [
        "pandoc",
        str(source_md),
        "--from",
        "markdown+raw_tex",
        "--to",
        "latex",
        "-o",
        str(body_tex),
    ]
    try:
        subprocess.run(cmd, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        print(exc.stdout, file=sys.stderr)
        print(exc.stderr, file=sys.stderr)
        fail(f"pandoc LaTeX conversion failed with exit code {exc.returncode}")

    full_tex.write_text(latex_document(body_tex.read_text(encoding="utf-8")), encoding="utf-8")
    for _ in range(2):
        try:
            subprocess.run(
                ["xelatex", "-interaction=nonstopmode", "-halt-on-error", full_tex.name],
                cwd=build_dir,
                check=True,
                text=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as exc:
            print(exc.stdout, file=sys.stderr)
            print(exc.stderr, file=sys.stderr)
            fail(f"xelatex PDF build failed with exit code {exc.returncode}")

    built_pdf = build_dir / "mpc-codex-first-track-fast-v1.pdf"
    if not built_pdf.exists():
        fail(f"xelatex did not create expected PDF: {built_pdf}")
    shutil.copy2(built_pdf, output_pdf)


def parse_args() -> argparse.Namespace:
    home = Path.home()
    return argparse.ArgumentParser(description="Build the MPC Codex excerpt PDF.").parse_args(
        namespace=argparse.Namespace(
            ch01=home / "digital-product-engine/drafts/ch01.md",
            ch02=home / "digital-product-engine/drafts/ch02.md",
            dist=home / "digital-product-engine/dist",
            build=home / "digital-product-engine/build",
        )
    )


def main() -> None:
    args = parse_args()
    ch01 = Path(args.ch01)
    ch02 = Path(args.ch02)
    dist = Path(args.dist)
    build = Path(args.build)
    output_pdf = dist / "mpc-codex-first-track-fast-v1.pdf"
    combined_md = build / "mpc-codex-first-track-fast-v1.md"

    require_file(ch01)
    require_file(ch02)
    dist.mkdir(parents=True, exist_ok=True)
    build.mkdir(parents=True, exist_ok=True)

    combined_md.write_text(build_combined_markdown(ch01, ch02), encoding="utf-8")
    run_pandoc(combined_md, output_pdf, build)

    if not output_pdf.exists() or output_pdf.stat().st_size == 0:
        fail(f"PDF was not created: {output_pdf}")

    print(f"Built PDF: {output_pdf}")
    print(f"Source bundle: {combined_md}")


if __name__ == "__main__":
    main()

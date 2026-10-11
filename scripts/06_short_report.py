"""Builds a short, plain PDF from my_report.txt. Edit the text file in Notepad, then run this again.

Text file rules:  # Title   ~ subtitle   ## Heading   - bullet   > small print
                  [figure: path | caption | width 0-1]   **bold**   blank line = new paragraph"""
import re, sys
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, KeepTogether
from PIL import Image as PI

SRC = sys.argv[1] if len(sys.argv) > 1 else "my_report.txt"
OUT = sys.argv[2] if len(sys.argv) > 2 else "Peach_Project_Summary.pdf"
ink = colors.HexColor("#222222"); grey = colors.HexColor("#666666")
S = dict(
    title=ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=ink, spaceAfter=3),
    sub=ParagraphStyle("s", fontName="Helvetica", fontSize=9, leading=12, textColor=grey, spaceAfter=8),
    h=ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=ink, spaceBefore=9, spaceAfter=3),
    p=ParagraphStyle("p", fontName="Helvetica", fontSize=9.6, leading=13.4, textColor=ink, spaceAfter=5),
    b=ParagraphStyle("b", fontName="Helvetica", fontSize=9.6, leading=13.4, textColor=ink, leftIndent=11, firstLineIndent=-8, spaceAfter=2.5),
    cap=ParagraphStyle("c", fontName="Helvetica-Oblique", fontSize=8, leading=10.5, textColor=grey, spaceAfter=7),
    small=ParagraphStyle("m", fontName="Helvetica", fontSize=7.6, leading=10, textColor=grey, spaceBefore=6))
fmt = lambda t: re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escape(t))
W = A4[0] - 40 * mm
lines = open(SRC, encoding="utf-8").read().split("\n")
story, buf, todo = [], [], []


def flush():
    global buf
    if buf:
        story.append(Paragraph(fmt(" ".join(buf)), S["p"])); buf = []


for ln in lines:
    s = ln.strip()
    if "TODO" in s:
        todo.append(s[:70])
    if not s:
        flush(); continue
    if s.startswith("# "):
        flush(); story.append(Paragraph(fmt(s[2:]), S["title"]))
    elif s.startswith("~ "):
        flush(); story.append(Paragraph(fmt(s[2:]), S["sub"]))
    elif s.startswith("## "):
        flush(); story.append(Paragraph(fmt(s[3:]), S["h"]))
    elif s.startswith("- "):
        flush(); story.append(Paragraph("&bull;&nbsp; " + fmt(s[2:]), S["b"]))
    elif s.startswith("> "):
        flush(); story.append(Paragraph(fmt(s[2:]), S["small"]))
    elif s.startswith("[figure:"):
        flush()
        parts = [x.strip() for x in s[8:].rstrip("]").split("|")]
        path, cap, frac = parts[0], parts[1] if len(parts) > 1 else "", float(parts[2]) if len(parts) > 2 else 0.9
        try:
            w, h = PI.open(path).size
        except FileNotFoundError:
            sys.exit(f"Figure not found: {path}. Run Step 4 first (it draws the figures).")
        story.append(KeepTogether([Image(path, width=W * frac, height=W * frac * h / w), Paragraph(fmt(cap), S["cap"])]))
    else:
        buf.append(s)
flush()
SimpleDocTemplate(OUT, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=17 * mm, bottomMargin=16 * mm,
                  title=lines[0].lstrip("# ").strip(), author="Zahin Tasnim Ridita").build(story)
try:
    from pypdf import PdfReader
    print(f"Built {OUT}  ({len(PdfReader(OUT).pages)} pages)")
except ImportError:
    print(f"Built {OUT}")
if todo:
    print("\nWARNING: your text still has TODO notes - replace them with your own writing before sharing:")
    for t in todo:
        print("   ", t)

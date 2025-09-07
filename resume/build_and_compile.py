#!/usr/bin/env python3
# pip install requests
import csv, io, re, requests
from pathlib import Path
from collections import defaultdict

# === Your published CSVs ===
PUBS_CSV  = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTbczS5lAOV8I8NLH4srTn72hmEEEjsS10aIqMRIu7ogTKiMYhqrEYBnUfWXw77M8bnQBNKMUoucVJl/pub?gid=0&single=true&output=csv"
PATENTS_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTbczS5lAOV8I8NLH4srTn72hmEEEjsS10aIqMRIu7ogTKiMYhqrEYBnUfWXw77M8bnQBNKMUoucVJl/pub?gid=1250559449&single=true&output=csv"
ACHIEVEMENTS_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTbczS5lAOV8I8NLH4srTn72hmEEEjsS10aIqMRIu7ogTKiMYhqrEYBnUfWXw77M8bnQBNKMUoucVJl/pub?gid=262204434&single=true&output=csv"
EDUCATION_CSV    = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTbczS5lAOV8I8NLH4srTn72hmEEEjsS10aIqMRIu7ogTKiMYhqrEYBnUfWXw77M8bnQBNKMUoucVJl/pub?gid=308131037&single=true&output=csv"
RESEARCH_CSV     = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTbczS5lAOV8I8NLH4srTn72hmEEEjsS10aIqMRIu7ogTKiMYhqrEYBnUfWXw77M8bnQBNKMUoucVJl/pub?gid=309578428&single=true&output=csv"
EXPERIENCE_CSV   = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTbczS5lAOV8I8NLH4srTn72hmEEEjsS10aIqMRIu7ogTKiMYhqrEYBnUfWXw77M8bnQBNKMUoucVJl/pub?gid=322365384&single=true&output=csv"  # e.g., ".../pub?gid=123456789&single=true&output=csv"

# === Output paths (match your \input{}s) ===
PUBS_TEX = Path("sections/publications.tex")
ACHV_TEX = Path("sections/achievments.tex")
EDU_TEX  = Path("sections/education.tex")
RES_TEX  = Path("sections/research.tex")
# NEW:
EXP_TEX  = Path("sections/experience.tex")

# === Formatting knobs ===
MY_NAME = "Rwik Rana"
INCLUDE_LINK = True
MERGE_MODE   = "pubs_then_patents"

# === Helpers ===
LATEX_ESC_PLAIN = [
    ("\\", r"\\textbackslash{}"),
    ("&",  r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_"),
    ("{",  r"\{"), ("}",  r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"),
]
def esc_plain(s:str)->str:
    s = (s or "").strip()
    for a,b in LATEX_ESC_PLAIN: s = s.replace(a,b)
    return s

LATEX_ESC_EDU = [
    ("&",  r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_"),
    ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"),
]
def esc_edu(s:str)->str:
    s = (s or "").strip()
    for a,b in LATEX_ESC_EDU: s = s.replace(a,b)
    return s

def bold_name(s:str)->str:
    return re.sub(r"(Rwik Rana|Rwik R\. Rana)", r"\\textbf{\1}", s or "")

def tag_has_resume(tag:str)->bool:
    return any(p.strip().lower()=="resume" for p in re.split(r"[;,]", tag or ""))

def fetch_rows(url:str):
    r = requests.get(url, timeout=30); r.raise_for_status()
    text = r.content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))

# --- normalize rows (existing) ---
def norm_pub_row(row:dict):
    return {
        "title":   (row.get("title")   or row.get("Title")   or "").strip(),
        "authors": (row.get("authors") or row.get("Authors") or "").strip(),
        "venue":   (row.get("venue")   or row.get("Venue")   or "").strip(),
        "link":    (row.get("link")    or row.get("URL")     or row.get("Link") or "").strip(),
        "tag":     (row.get("tag")     or row.get("Tag")     or "").strip(),
    }

def norm_ach_row(row:dict):
    def g(*keys):
        for k in keys:
            if k in row and row[k] is not None:
                return str(row[k])
        return ""
    return {
        "latex_update": g("latex update","latex_update","Latex update","Latex Update").strip(),
        "tag": g("tag","Tag").strip(),
    }

def norm_edu_row(row:dict):
    def g(k): return (row.get(k) or "").strip()
    return {
        "Institution": g("Institution"),
        "Program":     g("Program"),
        "Affiliations":g("Affiliations"),
        "Courses":     g("Courses"),
        "Dates":       g("Dates"),
        "Location":    g("Location"),
    }

def norm_research_row(row: dict):
    text = (row.get("Research Interest") or row.get("Research Interests") or
            row.get("research interest") or row.get("research interests") or "")
    text = re.sub(r"\s*\n\s*", " ", text).strip()
    tag  = (row.get("tag") or row.get("Tag") or "").strip()
    return {"text": text, "tag": tag}

# NEW: normalize experience rows
def norm_experience_row(row:dict):
    def g(*names):
        for n in names:
            if n in row and row[n] is not None:
                return str(row[n]).strip()
        return ""
    return {
        "company":     g("Company"),
        "team":        g("Team"),
        "experience":  g("Experience", "Role", "Project"),
        "advisors":    g("Advisors", "Advisor"),
        "description": g("Description", "Bullets"),
        "position":    g("Position", "Title"),
        # company-date can be named either "Company Date" or just "Date"
        "company_date": g("Company Date", "Date"),
        "tag":         g("tag","Tag"),
    }

# --- builders (existing) ---
def make_pub_item(r):
    title   = esc_plain(r["title"])
    authors = bold_name(esc_plain(r["authors"]))
    venue   = esc_plain(r["venue"])
    link    = r["link"]
    linkpart = (f" \\quad \\href{{{link}}}{{link}}" if (INCLUDE_LINK and link) else "")
    return (
f"""    \\item \\textbf{{{title}}} \\\\
        {authors},
        {{\\\\ \\textit{{{venue}}}}}{linkpart}"""
    )

def build_publications_tex(pubs, pats):
    lines = [
        r"% AUTO-GENERATED — do not edit manually",
        r"\noindent {\large \bf PUBLICATIONS \& PATENTS} \\ [-5pt]",
        r"\rule{\textwidth}{1.5pt}",
        r"\vspace{-10pt}",
        r"\begin{enumerate}",
        r"    \itemsep-0.3em",
    ]
    for r in pubs: lines.append(make_pub_item(r))
    for r in pats: lines.append(make_pub_item(r))
    lines += [r"\end{enumerate}", ""]
    return "\n".join(lines)

def build_achievements_tex(items):
    lines = [
        r"% AUTO-GENERATED — do not edit manually",
        r"\noindent {\large \bf ACHIEVEMENTS} \\[-5pt]",
        r"\rule{\textwidth}{1.5pt}",
        r"\vspace{-18pt}",
        r"",
        r"\begin{enumerate}",
        r"    \itemsep-0.3em",
    ]
    for txt in items:
        lines.append(f"    \\item {esc_edu(txt)}")
    lines += [r"\end{enumerate}", ""]
    return "\n".join(lines)

def split_program_lines(program:str)->str:
    if ";" in program:
        first, rest = program.split(";", 1)
        return esc_edu(first.strip()) + r"\\ " + esc_edu(rest.strip())
    return esc_edu(program)

def build_education_tex(rows):
    lines = [
        r"% AUTO-GENERATED — do not edit manually",
        r"\noindent {\bf EDUCATION} \\[-7.5pt]",
        r"\rule{\textwidth}{1.5pt}",
        r"",
    ]
    for r in rows:
        inst  = esc_edu(r["Institution"])
        loc   = esc_edu(r["Location"])
        dates = esc_edu(r["Dates"])
        prog  = split_program_lines(r["Program"])
        aff   = esc_edu(r["Affiliations"])
        crs   = esc_edu(r["Courses"])
        lines.append(
f"""{{\\bf {inst}}}{{  \\hfill \\textit{{{loc}}} \\\\[0pt]
\\small{{{prog}\\hfill \\textit{{{dates}}} \\\\
{aff}""" + (f""" \\\\
\\textbf{{Relevant coursework}}: {crs}""" if crs else "") + """}}
"""
        )
    lines.append("")
    return "\n".join(lines)

def build_research_tex(paragraphs):
    lines = [
        r"% AUTO-GENERATED — do not edit manually",
        r"\noindent {\bf RESEARCH INTERESTS} \\[-7.5pt]",
        r"\rule{\textwidth}{1.5pt}",
        r"\vspace{-6pt}",
        "",
    ]
    for i, para in enumerate(paragraphs):
        if i > 0:
            lines.append(r"\par\medskip")
        lines.append(esc_edu(para))
    lines.append("")
    return "\n".join(lines)

def _desc_to_itemize(desc_raw: str) -> str:
    """Zero-vertical-space itemize; accepts '\item ...' or plain/semicolon text."""
    d = (desc_raw or "").strip()
    if not d:
        return ""
    has_item = r"\item" in d
    items = d if has_item else " \\item ".join([s.strip() for s in re.split(r";|\n", d) if s.strip()])
    if not has_item:
        items = r"\item " + items

    # Absolutely no vertical padding above/below or between items
    return (
        "% tight list\n"
        "\\vspace{-10pt}\n"
        "\\begin{itemize}\n"
        "  \\setlength{\\itemsep}{0pt}\n"
        "  \\setlength{\\parskip}{0pt}\n"
        "  \\setlength{\\parsep}{0pt}\n"
        "  \\setlength{\\topsep}{0pt}\n"
        "  \\setlength{\\partopsep}{0pt}\n"
        f"  {items}\n"
        "\\end{itemize}\n"
        # "\\vspace{-2pt}\n"
    )



def build_experience_tex(rows):
    """
    Exact sheet order; zero spacing within a company block.
    Only adds a small gap between different (company, position, date) blocks.
    """
    out = [
        r"% AUTO-GENERATED — do not edit manually",
        r"\noindent {\bf EXPERIENCE} \\[-7.5pt]",
        r"\rule{\textwidth}{1.5pt}",
        r"{\setlength{\parskip}{0pt}\setlength{\parsep}{0pt}",  # no paragraph gaps
    ]

    current_key = None
    first_block = True

    for r in rows:
        if not tag_has_resume(r.get("tag", "")):
            continue

        comp_raw = r.get("company", "")
        pos_raw  = r.get("position", "")
        dt_raw   = r.get("company_date", "")
        key = (comp_raw, pos_raw, dt_raw)

        comp = esc_edu(comp_raw)
        pos  = esc_edu(pos_raw)
        dt   = esc_edu(dt_raw)

        # New company/position/date heading
        if key != current_key:
            if not first_block:
                out.append(r"\vspace{4pt}")  # ONLY spacing between different companies/positions/dates
            left  = f"{{\\bf {comp}}}" + (f", \\textit{{{pos}}}" if pos else "")
            right = f" \\hfill \\textit{{{dt}}}" if dt else ""
            out.append(left + right + r"\\")   # plain line break; no [-pt] tweaks
            current_key = key
            first_block = False

        # Experience subheading (flush to bullets)
        exp  = esc_edu(r.get("experience", ""))
        team = esc_edu(r.get("team", ""))
        adv  = esc_edu(r.get("advisors", ""))

        left_line = f"\\textit{{{exp}}}" if not team else f"\\textit{{{exp}}} --- {team}"
        if left_line.strip():
            line = left_line + (f" \\hfill {adv}" if adv else "")
            out.append(line + r"\\")  # plain line break directly into itemize

        # Bullets (already zero top/bottom spacing)
        dblock = _desc_to_itemize(r.get("description", ""))
        if dblock:
            out.append(dblock)

    out.append("}")  # end local spacing group
    out.append("")   # single trailing newline
    return "\n".join(out)



# --- main ---
def main():
    # pubs + patents
    pubs_all = [norm_pub_row(r) for r in fetch_rows(PUBS_CSV)]
    pats_all = [norm_pub_row(r) for r in fetch_rows(PATENTS_CSV)]
    pubs = [r for r in pubs_all if tag_has_resume(r["tag"])]
    pats = [r for r in pats_all if tag_has_resume(r["tag"])]
    if MERGE_MODE == "pubs_then_patents":
        pubs_out, pats_out = pubs, pats
    else:
        pubs_out, pats_out = pats, pubs
    PUBS_TEX.parent.mkdir(parents=True, exist_ok=True)
    PUBS_TEX.write_text(build_publications_tex(pubs_out, pats_out), encoding="utf-8")

    # achievements
    if not ACHIEVEMENTS_CSV.startswith("PASTE_"):
        ach_rows = [norm_ach_row(r) for r in fetch_rows(ACHIEVEMENTS_CSV)]
        ach_items = [r["latex_update"] for r in ach_rows if r["latex_update"] and tag_has_resume(r["tag"])]
        ACHV_TEX.parent.mkdir(parents=True, exist_ok=True)
        ACHV_TEX.write_text(build_achievements_tex(ach_items), encoding="utf-8")

    # education
    if not EDUCATION_CSV.startswith("PASTE_"):
        edu_rows = [norm_edu_row(r) for r in fetch_rows(EDUCATION_CSV)]
        EDU_TEX.parent.mkdir(parents=True, exist_ok=True)
        EDU_TEX.write_text(build_education_tex(edu_rows), encoding="utf-8")

    # research
    if not RESEARCH_CSV.startswith("PASTE_"):
        research_rows = [norm_research_row(r) for r in fetch_rows(RESEARCH_CSV)]
        paragraphs = [r["text"] for r in research_rows if r["text"] and tag_has_resume(r["tag"])]
        RES_TEX.parent.mkdir(parents=True, exist_ok=True)
        text = build_research_tex(paragraphs) + r"\par\medskip" + "\n"
        RES_TEX.write_text(text, encoding="utf-8")

    # NEW: experience
    if not EXPERIENCE_CSV.startswith("PASTE_"):
        exp_rows_all = [norm_experience_row(r) for r in fetch_rows(EXPERIENCE_CSV)]
        EXP_TEX.parent.mkdir(parents=True, exist_ok=True)
        EXP_TEX.write_text(build_experience_tex(exp_rows_all), encoding="utf-8")

    print(f"Wrote {PUBS_TEX}.")
    if not ACHIEVEMENTS_CSV.startswith("PASTE_"):
        print(f"Wrote {ACHV_TEX}.")
    if not EDUCATION_CSV.startswith("PASTE_"):
        print(f"Wrote {EDU_TEX}.")
    if not RESEARCH_CSV.startswith("PASTE_"):
        print(f"Wrote {RES_TEX}.")
    if not EXPERIENCE_CSV.startswith("PASTE_"):
        print(f"Wrote {EXP_TEX}.")

if __name__ == "__main__":
    main()

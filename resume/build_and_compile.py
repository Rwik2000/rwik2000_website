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
SKILLS_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTbczS5lAOV8I8NLH4srTn72hmEEEjsS10aIqMRIu7ogTKiMYhqrEYBnUfWXw77M8bnQBNKMUoucVJl/pub?gid=2062416334&single=true&output=csv"

# === Output paths (match your \input{}s) ===
PUBS_TEX = Path("sections/publications.tex")
ACHV_TEX = Path("sections/achievments.tex")
EDU_TEX  = Path("sections/education.tex")
RES_TEX  = Path("sections/research.tex")
EXP_TEX  = Path("sections/experience.tex")
SKL_TEX  = Path("sections/skills.tex")

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
        "company":      g("Company"),
        "team":         g("Team"),
        "experience":   g("Experience", "Role", "Project"),
        "advisors":     g("Advisors", "Advisor"),
        "description":  g("Description", "Bullets"),
        "position":     g("Position", "Title"),
        "company_date": g("Company Date", "Date"),
        "tag":          g("tag","Tag"),
        # NEW link fields
        "paper_link":   g("Paper Link", "Paper", "Paper URL"),
        "code_link":    g("Code Link", "Code", "Code URL", "Github", "GitHub"),
        "website_link": g("Project Website", "Website", "Project URL"),
        "video_link":   g("Video Link", "Video", "Demo Video"),
        "image_link":   g("Image Link", "Image", "Demo Image"),
    }

def _format_exp_links(r: dict) -> str:
    """Builds space-separated [paper] [code] [website] [video] hyperlinks if present."""
    links = []
    if r.get("paper_link"):
        links.append(rf"\href{{{esc_edu(r['paper_link'])}}}{{[Paper]}}")
    if r.get("code_link"):
        links.append(rf"\href{{{esc_edu(r['code_link'])}}}{{[Code]}}")
    if r.get("website_link"):
        links.append(rf"\href{{{esc_edu(r['website_link'])}}}{{[Website]}}")
    if r.get("video_link"):
        links.append(rf"\href{{{esc_edu(r['video_link'])}}}{{[Video]}}")
    if r.get("image_link"):
        links.append(rf"\href{{{esc_edu(r['image_link'])}}}{{[Image]}}")
    return " ".join(links)


# --- builders (existing) ---
def make_pub_item(r):
    title   = esc_plain(r["title"])
    authors = bold_name(esc_plain(r["authors"]))
    venue   = esc_plain(r["venue"])
    link    = r["link"]
    linkpart = (f" \\quad \\href{{{link}}}{{[link]}}" if (INCLUDE_LINK and link) else "")
    return (
f"""    \\item \\textbf{{{title}}} \\\\
        {authors},
        {{\\\\ \\textit{{{venue}}}}}{linkpart}\\"""
    )

def build_publications_tex(pubs, pats):
    lines = [
        r"% AUTO-GENERATED — do not edit manually",
        r"\vspace{5pt}",
        r"\noindent {\large \bf PUBLICATIONS \& PATENTS} \\ [-5pt]",
        r"\rule{\textwidth}{1.5pt}",
        # r"\vspace{-10pt}",
        r"\begin{enumerate}",
        # r"    \itemsep-0.3em",
    ]
    for r in pubs: lines.append(make_pub_item(r))
    for r in pats: lines.append(make_pub_item(r))
    lines += [r"\end{enumerate}", ""]
    return "\n".join(lines)

def build_achievements_tex(items):
    lines = [
        r"% AUTO-GENERATED — do not edit manually",
        r"\noindent {\large \bf ACHIEVEMENTS} \\[-5pt]",
        r"\rule{\textwidth}{1.5pt}\\",
        r"\vspace{-12pt}",
        # r"",
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
        r"\noindent {\large \bf EDUCATION} \\[-5pt]",
        r"\rule{\textwidth}{1.5pt}\\",
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
        lines.append(r"\vspace{5pt}")
    return "\n".join(lines)

def build_research_tex(paragraphs):
    lines = [
        r"% AUTO-GENERATED — do not edit manually",
        r"\noindent {\large \bf RESEARCH INTERESTS} \\[-5pt]",
        r"\rule{\textwidth}{1.5pt}\\",
        # r"\vspace{0.5pt}",
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

    # Absolutely no vertical padding above/below or between items, with left indent
    return (
        "% tight list\n"
        "\\vspace{-8pt}\n"
        "\\begin{itemize}[leftmargin=3.0em,labelsep=0.6em]\n"
        "  \\setlength{\\itemsep}{0pt}\n"
        "  \\setlength{\\parskip}{0pt}\n"
        "  \\setlength{\\parsep}{0pt}\n"
        "  \\setlength{\\topsep}{0pt}\n"
        "  \\setlength{\\partopsep}{0pt}\n"
        f"  {items}\n"
        "\\end{itemize}\n"
    )


def build_experience_tex(rows):
    """
    Exact sheet order; zero spacing within a company block.
    Heading:  {Company}, \textit{Position} \hfill \textit{CompanyDate}\\
    Subline:  \textit{Experience} --- Team [paper] [code] [website] [video] \hfill Advisors\\
    Bullets:  compact itemize produced by _desc_to_itemize()
    """
    out = [
        r"% AUTO-GENERATED — do not edit manually",
        r"\vspace{5pt}",
        r"\noindent {\large \bf EXPERIENCE} \\[-5pt]",
        r"\rule{\textwidth}{1.5pt}",
        r"\vspace{1pt}\\"
        # r"{\setlength{\parskip}{0pt}\setlength{\parsep}{0pt}",  # suppress paragraph gaps locally
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

        # New (company, position, date) heading
        if key != current_key:
            # if not first_block:
            #     out.append(r"\vspace{10pt}")  # spacing between companies, if desired
            left  = f"{{\\bf {comp}}}" + (f", \\textit{{{pos}}}" if pos else "")
            right = f" \\hfill \\textit{{{dt}}}" if dt else ""
            out.append(left + right + r"\\")
            # out.append(r"\vspace{30pt}")  # tighten space after heading
            current_key = key
            first_block = False

        # Subheading line: Experience --- Team + optional links, advisors on right
        exp  = esc_edu(r.get("experience", ""))
        team = esc_edu(r.get("team", ""))
        adv  = esc_edu(r.get("advisors", ""))

        # left_core = rf"\textit{{{exp}}}" if not team else rf"\textit{{{exp}}} --- {team}"
        left_indent = r"\hspace*{0.8em}"  # tweak amount to taste

        left_core = (
            rf"{left_indent}\textit{{{exp}}}"
            if not team
            else rf"{left_indent}\textit{{{exp}}} --- {team}"
        )
        links_str = _format_exp_links(r)  # builds \href{...}{[paper]} etc. when present
        if links_str:
            left_core = f"{left_core} {links_str}"

        if left_core.strip():
            out.append(left_core + (f" \\hfill {adv}" if adv else "") + r"\\")

        # Bullets (already compact/indented via _desc_to_itemize)
        dblock = _desc_to_itemize(r.get("description", ""))
        if dblock:
            out.append(dblock)
            out.append(r"\vspace{7pt}")  # uncomment if you want space after each entry

    # out.append("}")   # end local spacing group
    out.append("")    # trailing newline
    return "\n".join(out)

def build_skills_tex(rows):
    """
    Input: rows from the Skills tab where columns are categories (Libraries, Coding, ...)
           and each column has items down the rows (cells can be blank).
    Output: a compact SKILLS section with one line per category.
    """
    if not rows:
        return "% No skills rows"

    # preserve column order exactly as in the sheet
    columns = list(rows[0].keys())

    # collect non-empty cells per column (skip completely empty column names if any)
    col_to_items = []
    for col in columns:
        if not (col or "").strip():
            continue
        items = []
        for r in rows:
            cell = (r.get(col) or "").strip()
            if cell:
                items.append(esc_edu(cell))
        # keep the category even if empty, but usually there are items
        col_to_items.append((esc_edu(col), items))

    lines = [
        r"% AUTO-GENERATED — do not edit manually",
        # r"\vspace{5pt}",
        r"\noindent {\large \bf SKILLS} \\[-5pt]",
        r"\rule{\textwidth}{1.5pt}",
        r"\vspace{-6pt}",
        "",
    ]
    lines.append(r"\begin{itemize}[leftmargin=2.5em,labelsep=1em]")
    for (cat, items) in col_to_items:
        if not cat:
            continue
        joined = ", ".join(items)
        # one tight line per category
        lines.append(rf"\item \textbf{{{cat}}}: {joined}")
    lines.append(r"\end{itemize}")
    return "\n".join(lines)


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
    
    if not SKILLS_CSV.startswith("PASTE_"):
        skills_rows = fetch_rows(SKILLS_CSV)
        SKL_TEX.parent.mkdir(parents=True, exist_ok=True)
        SKL_TEX.write_text(build_skills_tex(skills_rows), encoding="utf-8")

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

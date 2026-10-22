import os
import re
try:
    from fpdf import FPDF
except ImportError:
    from fpdf2 import FPDF

from agents.report_agent import clean_latex_math_and_artifacts

class MarkdownPDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

def sanitize_text_for_pdf(text: str) -> str:
    """
    Normalizes Unicode characters into Latin-1 compliant equivalents
    so that no question marks or mangled glyphs appear in the generated PDF.
    """
    replacements = {
        '\u2019': "'",
        '\u2018': "'",
        '\u201c': '"',
        '\u201d': '"',
        '\u2013': '-',
        '\u2014': '-',
        '\u2265': '>=',
        '\u2264': '<=',
        '\u2192': '->',
        '\u2190': '<-',
        '\u2194': '<->',
        '\u2022': '-',
        '\u00b1': '+/-',
        '\u2248': '~',
        '\u223c': '~',
        '\u00d7': 'x',
        '\u00b0': ' deg',
        '\u2206': 'Delta',
        '\u0394': 'Delta',
        '\u03bc': 'mu',
        '\u03c4': 'tau',
        '\u03c3': 'sigma',
        '\u03bb': 'lambda',
        '\u2260': '!=',
        '\u221e': 'infinity',
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    # Encode as latin-1, dropping any non-convertible characters rather than replacing with '?'
    return text.encode('latin-1', 'replace').decode('latin-1').replace('?', '')

def convert_markdown_to_pdf_bytes(markdown_text: str, title: str = "Research Report") -> bytes:
    # 1. Clean all LaTeX math, raw equations, ASCII box art, and leading commas
    markdown_text = clean_latex_math_and_artifacts(markdown_text)

    pdf = MarkdownPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.alias_nb_pages()
    pdf.add_page()

    lines = markdown_text.split("\n")
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        raw_line = lines[i]
        stripped = raw_line.strip()

        if not stripped:
            pdf.ln(2.5)
            i += 1
            continue

        # Detect Markdown Tables (lines starting with | and containing another |)
        if stripped.startswith('|') and '|' in stripped[1:]:
            table_lines = []
            while i < total_lines and lines[i].strip().startswith('|') and '|' in lines[i].strip()[1:]:
                table_lines.append(lines[i].strip())
                i += 1

            parsed_rows = []
            for t_line in table_lines:
                inner = t_line.strip('|')
                cells = [c.strip() for c in inner.split('|')]
                # Skip markdown separator line |---|---|
                if all(re.match(r'^:?-+:?$', c) for c in cells if c):
                    continue
                clean_cells = [
                    sanitize_text_for_pdf(c.replace('**', '').replace('*', '').replace('`', ''))
                    for c in cells
                ]
                if clean_cells:
                    parsed_rows.append(clean_cells)

            if parsed_rows:
                max_cols = max(len(r) for r in parsed_rows)
                for r in parsed_rows:
                    while len(r) < max_cols:
                        r.append("")

                usable_width = 180 # Standard printable width on A4
                col_width = usable_width / max_cols

                pdf.ln(2)
                try:
                    with pdf.table(col_widths=[col_width]*max_cols, line_height=5, text_align="LEFT") as table:
                        # Table Header
                        hdr = table.row()
                        pdf.set_font("helvetica", "B", 8.5)
                        pdf.set_text_color(24, 24, 27)
                        for cell_text in parsed_rows[0]:
                            hdr.cell(cell_text)

                        # Table Data Rows
                        pdf.set_font("helvetica", "", 8)
                        pdf.set_text_color(55, 65, 81)
                        for row in parsed_rows[1:]:
                            r = table.row()
                            for cell_text in row:
                                r.cell(cell_text)
                except Exception:
                    # Fallback row printing
                    pdf.set_font("helvetica", "", 8.5)
                    pdf.set_text_color(55, 65, 81)
                    for row in parsed_rows:
                        pdf.multi_cell(0, 5, " | ".join(row))
                pdf.ln(3)
            continue

        # Clean inline markdown bold, italic, and backticks for clean PDF typography
        clean_line = stripped
        clean_line = clean_line.replace("**", "")
        clean_line = clean_line.replace("*", "")
        clean_line = clean_line.replace("`", "")
        clean_line = sanitize_text_for_pdf(clean_line)

        # Headings
        if stripped.startswith("# "):
            title_text = clean_line[2:].strip()
            pdf.set_font("helvetica", "B", 18)
            pdf.set_text_color(24, 24, 27)
            pdf.ln(5)
            pdf.multi_cell(0, 8, title_text)
            pdf.ln(3)
        elif stripped.startswith("## "):
            h1_text = clean_line[3:].strip()
            pdf.set_font("helvetica", "B", 13)
            pdf.set_text_color(39, 39, 42)
            pdf.ln(4)
            pdf.multi_cell(0, 7, h1_text)
            pdf.ln(2)
        elif stripped.startswith("### "):
            h2_text = clean_line[4:].strip()
            pdf.set_font("helvetica", "B", 10.5)
            pdf.set_text_color(63, 63, 70)
            pdf.ln(3)
            pdf.multi_cell(0, 6, h2_text)
            pdf.ln(1)
        elif stripped.startswith("#### "):
            h3_text = clean_line[5:].strip()
            pdf.set_font("helvetica", "B", 9.5)
            pdf.set_text_color(75, 85, 99)
            pdf.ln(2)
            pdf.multi_cell(0, 5, h3_text)
            pdf.ln(1)
        elif stripped.startswith("> "):
            quote_text = clean_line[2:].strip()
            pdf.set_font("helvetica", "I", 9)
            pdf.set_text_color(100, 116, 139)
            cur_x = pdf.get_x()
            pdf.set_x(cur_x + 8)
            pdf.multi_cell(0, 5, quote_text)
            pdf.set_x(cur_x)
            pdf.ln(1.5)
        elif stripped.startswith("- ") or stripped.startswith("* "):
            bullet_text = clean_line[2:].strip()
            pdf.set_font("helvetica", "", 9.5)
            pdf.set_text_color(63, 63, 70)
            cur_x = pdf.get_x()
            pdf.set_x(cur_x + 8)
            pdf.cell(5, 5, "- ")
            pdf.multi_cell(0, 5, bullet_text)
            pdf.set_x(cur_x)
            pdf.ln(1)
        elif re.match(r'^\d+\.\s+', stripped):
            parts = clean_line.split(".", 1)
            num = parts[0].strip() + "."
            text = parts[1].strip()
            pdf.set_font("helvetica", "", 9.5)
            pdf.set_text_color(63, 63, 70)
            cur_x = pdf.get_x()
            pdf.set_x(cur_x + 8)
            pdf.cell(8, 5, num)
            pdf.multi_cell(0, 5, text)
            pdf.set_x(cur_x)
            pdf.ln(1)
        else:
            pdf.set_font("helvetica", "", 9.5)
            pdf.set_text_color(63, 63, 70)
            pdf.multi_cell(0, 5, clean_line)
            pdf.ln(1.5)

        i += 1

    return bytes(pdf.output())

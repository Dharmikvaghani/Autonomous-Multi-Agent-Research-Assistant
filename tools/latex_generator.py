"""
LaTeX and BibTeX Generator Module for Prism AI
Converts research report markdown into clean, compilable academic LaTeX (.tex)
and generates formatted BibTeX (.bib) bibliographies.
"""

import re
from typing import List, Dict, Any, Optional

def escape_latex(text: str) -> str:
    """
    Escapes special LaTeX characters outside of math and commands.
    """
    if not text:
        return ""
    
    # Characters that must be escaped in LaTeX
    conv = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    
    # Don't escape backslashes blindly
    regex = re.compile('|'.join(re.escape(str(key)) for key in sorted(conv.keys(), key=lambda item: -len(item))))
    return regex.sub(lambda match: conv[match.group()], text)

def convert_markdown_to_latex(markdown_text: str, title: str = "Autonomous Research Report", author: str = "Prism AI Research Assistant") -> str:
    """
    Converts full markdown research report into a standard, compilable LaTeX article.
    """
    lines = markdown_text.split("\n")
    latex_body = []
    in_itemize = False
    in_enumerate = False
    in_codeblock = False
    
    for line in lines:
        stripped = line.strip()
        
        # Code blocks
        if stripped.startswith("```"):
            if in_codeblock:
                latex_body.append(r"\end{verbatim}")
                in_codeblock = False
            else:
                if in_itemize:
                    latex_body.append(r"\end{itemize}")
                    in_itemize = False
                if in_enumerate:
                    latex_body.append(r"\end{enumerate}")
                    in_enumerate = False
                latex_body.append(r"\begin{verbatim}")
                in_codeblock = True
            continue
            
        if in_codeblock:
            latex_body.append(line)
            continue
            
        # Empty lines
        if not stripped:
            if in_itemize:
                latex_body.append(r"\end{itemize}")
                in_itemize = False
            if in_enumerate:
                latex_body.append(r"\end{enumerate}")
                in_enumerate = False
            latex_body.append("")
            continue
            
        # Headers
        if stripped.startswith("# "):
            if in_itemize: latex_body.append(r"\end{itemize}"); in_itemize = False
            h_text = escape_latex(stripped[2:].strip())
            latex_body.append(f"\\section*{{{h_text}}}")
            continue
        elif stripped.startswith("## "):
            if in_itemize: latex_body.append(r"\end{itemize}"); in_itemize = False
            h_text = escape_latex(stripped[3:].strip())
            latex_body.append(f"\\section{{{h_text}}}")
            continue
        elif stripped.startswith("### "):
            if in_itemize: latex_body.append(r"\end{itemize}"); in_itemize = False
            h_text = escape_latex(stripped[4:].strip())
            latex_body.append(f"\\subsection{{{h_text}}}")
            continue
        elif stripped.startswith("#### "):
            if in_itemize: latex_body.append(r"\end{itemize}"); in_itemize = False
            h_text = escape_latex(stripped[5:].strip())
            latex_body.append(f"\\subsubsection{{{h_text}}}")
            continue
            
        # List items
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_itemize:
                latex_body.append(r"\begin{itemize}")
                in_itemize = True
            item_text = stripped[2:].strip()
            # Inline bold and italics
            item_text = _format_inline_markdown(item_text)
            latex_body.append(f"  \\item {item_text}")
            continue
            
        # Numbered list items
        num_match = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if num_match:
            if not in_enumerate:
                latex_body.append(r"\begin{enumerate}")
                in_enumerate = True
            item_text = num_match.group(2).strip()
            item_text = _format_inline_markdown(item_text)
            latex_body.append(f"  \\item {item_text}")
            continue
            
        # Close lists if regular text
        if in_itemize:
            latex_body.append(r"\end{itemize}")
            in_itemize = False
        if in_enumerate:
            latex_body.append(r"\end{enumerate}")
            in_enumerate = False
            
        # Horizontal rules
        if stripped in ["---", "***", "___"]:
            latex_body.append(r"\bigskip\hrule\bigskip")
            continue
            
        # Blockquotes
        if stripped.startswith("> "):
            quote_text = _format_inline_markdown(stripped[2:].strip())
            latex_body.append(f"\\begin{{quote}}\n{quote_text}\n\\end{{quote}}")
            continue
            
        # Standard paragraph
        p_text = _format_inline_markdown(stripped)
        latex_body.append(f"{p_text}\n")
        
    if in_itemize:
        latex_body.append(r"\end{itemize}")
    if in_enumerate:
        latex_body.append(r"\end{enumerate}")
    if in_codeblock:
        latex_body.append(r"\end{verbatim}")
        
    body_content = "\n".join(latex_body)
    escaped_title = escape_latex(title)
    escaped_author = escape_latex(author)
    
    latex_document = f"""\\documentclass[11pt,a4paper]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{amsmath,amssymb}}
\\usepackage{{booktabs}}
\\usepackage{{hyperref}}
\\usepackage{{xcolor}}
\\usepackage{{microtype}}

\\hypersetup{{
    colorlinks=true,
    linkcolor=blue!80!black,
    urlcolor=blue!70!black,
    citecolor=green!60!black
}}

\\title{{\\textbf{{{escaped_title}}}}}
\\author{{{escaped_author}\\\\ \\small Autonomous Multi-Agent Research Framework}}
\\date{{\\today}}

\\begin{{document}}

\\maketitle
\\begin{{abstract}}
This academic research report was autonomously compiled by the Prism AI multi-agent research pipeline. 
The system integrates strategic planning, academic literature collection (arXiv, CrossRef), real-time web retrieval, 
and ChromaDB vector-memory synthesis with automated peer-critic refinement.
\\end{{abstract}}

\\vspace{{1em}}

{body_content}

\\end{{document}}
"""
    return latex_document

def _format_inline_markdown(text: str) -> str:
    """
    Handles bold, italics, inline code, and URLs while safely escaping other characters.
    """
    # 1. Links: [title](url)
    def link_repl(match):
        label = escape_latex(match.group(1))
        url = match.group(2)
        return f"\\href{{{url}}}{{{label}}}"
    
    text = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', link_repl, text)
    
    # 2. Inline code: `code`
    def code_repl(match):
        code_content = match.group(1)
        return f"\\texttt{{{code_content}}}"
    
    text = re.sub(r'`([^`]+)`', code_repl, text)
    
    # 3. Bold: **text**
    def bold_repl(match):
        inner = escape_latex(match.group(1))
        return f"\\textbf{{{inner}}}"
        
    # Split out already processed LaTeX macros before general escaping
    parts = re.split(r'(\\\w+\{[^}]*\}(?:\{[^}]*\})?)', text)
    new_parts = []
    for part in parts:
        if part.startswith("\\"):
            new_parts.append(part)
        else:
            # Handle bold in non-macro parts
            part_bold = re.sub(r'\*\*([^*]+)\*\*', r'\\textbf{\1}', part)
            part_italic = re.sub(r'\*([^*]+)\*', r'\\textit{\1}', part_bold)
            # Escape remaining special characters
            escaped = ""
            # Simple escape for characters not already part of markup
            for ch in part_italic:
                if ch in ['&', '%', '$', '#', '_']:
                    escaped += '\\' + ch
                else:
                    escaped += ch
            new_parts.append(escaped)
            
    return "".join(new_parts)

def generate_bibtex(sources: Optional[List[Dict[str, Any]]] = None, markdown_content: str = "", title: str = "Research Sources") -> str:
    """
    Generates a valid BibTeX (.bib) bibliography file from source objects or extracted markdown links.
    """
    bib_entries = []
    seen_keys = set()
    
    # 1. Parse from structured sources list
    if sources and isinstance(sources, list):
        for idx, src in enumerate(sources, start=1):
            s_title = src.get("title") or f"Source {idx}"
            s_url = src.get("url") or ""
            authors = src.get("authors") or ["Prism AI Research Contributor"]
            if isinstance(authors, list):
                authors_str = " and ".join(authors)
            else:
                authors_str = str(authors)
                
            year = src.get("year") or "2026"
            venue = src.get("venue") or src.get("source") or "Online Repository"
            doi = src.get("doi") or ""
            
            # Create citation key
            clean_first_author = re.sub(r'[^a-zA-Z]', '', authors[0] if isinstance(authors, list) and authors else "source")
            clean_year = re.sub(r'[^0-9]', '', str(year)) or "2026"
            cite_key = f"{clean_first_author.lower()}_{clean_year}_{idx}"
            if cite_key in seen_keys:
                cite_key = f"{cite_key}_{idx}"
            seen_keys.add(cite_key)
            
            entry = f"""@article{{{cite_key},
  author    = {{{authors_str}}},
  title     = {{{s_title}}},
  journal   = {{{venue}}},
  year      = {{{year}}},
  url       = {{{s_url}}}{f',\n  doi       = {{{doi}}}' if doi else ''}
}}"""
            bib_entries.append(entry)
            
    # 2. Fallback: Parse markdown URLs if structured sources list is empty
    if not bib_entries and markdown_content:
        links = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', markdown_content)
        for idx, (link_title, link_url) in enumerate(links[:15], start=1):
            cite_key = f"ref_{idx}_{clean_first_author if 'clean_first_author' in locals() else 'prism'}"
            if cite_key in seen_keys:
                cite_key += f"_{idx}"
            seen_keys.add(cite_key)
            
            entry = f"""@misc{{{cite_key},
  title        = {{{link_title}}},
  howpublished = {{\\url{{{link_url}}}}},
  year         = {{2026}},
  note         = {{Accessed via Prism AI Research Engine}}
}}"""
            bib_entries.append(entry)
            
    if not bib_entries:
        # Default starter entry
        bib_entries.append("""@misc{prism_ai_2026,
  author       = {Prism AI Multi-Agent Research System},
  title        = {Autonomous Multi-Agent Literature Synthesizer},
  year         = {2026},
  url          = {https://github.com/SahilSurani/Autonomous-Multi-Agent-Research-Assistant}
}""")
        
    header = f"% BibTeX Bibliography generated by Prism AI\n% Title: {title}\n\n"
    return header + "\n\n".join(bib_entries) + "\n"

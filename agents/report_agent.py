import os
import sys
import re

# Ensure project root is in the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.groq_client import ask_groq
from agents.researcher_agent import clean_report_headings

import json

def clean_latex_math_and_artifacts(text: str) -> str:
    """
    Cleans raw LaTeX math notation, stray equations, ASCII pseudo-boxes, and leading punctuation artifacts
    to produce clean, readable, publication-grade text for UI viewing and PDF export.
    """
    if not text:
        return ""

    text = text.replace('\r\n', '\n')

    # Fix leading stray commas/colons/semicolons at line starts or sentence boundaries
    text = re.sub(r'(?m)^\s*[,;:]\s*', '', text)
    text = re.sub(r'\(\s*[,;:]\s*', '(', text)
    text = re.sub(r'\.\s*,\s*(?=[A-Z])', '. ', text)

    # Currency protection: Replace \$ with $ first
    text = re.sub(r'\\+\$', '$', text)

    def protect_currency(m):
        full = m.group(0)
        after = text[m.end():m.end()+15]
        if re.match(r'^\s*\\?text\b|^\s*(?:km|m|s|Hz|yr|deg|°)', after):
            return full
        return full.replace('$', '__CURRENCY__')

    text = re.sub(r'[><]?\s*\$[0-9,]+(?:\.[0-9]+)?\s*(?:k|M|B|million|billion|trillion)?\b', protect_currency, text)

    # Remove common LaTeX wrapper commands while preserving spacing
    for cmd in ['text', 'mathrm', 'mathbf', 'mathit', 'mathcal', 'boldsymbol', 'operatorname']:
        text = re.sub(rf'\\{cmd}\{{\s*([^}}]+?)\s*\}}', r' \1 ', text, flags=re.DOTALL)

    # Replace common LaTeX operators and symbols
    replacements = [
        (r'\\approx', ' ~ '),
        (r'\\sim', ' ~ '),
        (r'\\le\b', ' <= '),
        (r'\\leq\b', ' <= '),
        (r'\\ge\b', ' >= '),
        (r'\\geq\b', ' >= '),
        (r'\\pm\b', ' +/- '),
        (r'\\times\b', ' x '),
        (r'\\cdot\b', ' * '),
        (r'\\circ\b', '°'),
        (r'\\equiv\b', ' = '),
        (r'\\Delta\b', 'Delta '),
        (r'\\mu\b', 'mu'),
        (r'\\tau\b', 'tau'),
        (r'\\sigma\b', 'sigma'),
        (r'\\lambda\b', 'lambda'),
        (r'\\alpha\b', 'alpha'),
        (r'\\beta\b', 'beta'),
        (r'\\gamma\b', 'gamma'),
        (r'\\theta\b', 'theta'),
        (r'\\sum\b', 'sum'),
        (r'\\infty\b', 'infinity'),
        (r'\\to\b', ' -> '),
        (r'\\log_\{10\}', 'log10'),
        (r'\\log_10\b', 'log10'),
        (r'\\ln\b', 'ln'),
        (r'\\left\(', '('),
        (r'\\right\)', ')'),
        (r'\\left\[', '['),
        (r'\\right\]', ']'),
        (r'\\mid\b', ' | '),
        (r'\\!', ''),
        (r'\\;', ' '),
        (r'\\,', ' '),
        (r'\\quad\b', ' '),
        (r'\\qquad\b', '  '),
        (r'\\%', '%'),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text)

    # Handle \frac{a}{b} -> (a/b)
    text = re.sub(r'\\frac\{\s*([^}]+)\s*\}\{\s*([^}]+)\s*\}', r'(\1/\2)', text, flags=re.DOTALL)

    # Specific seismic/geophysical magnitude & parameter conversions:
    text = re.sub(r'\$?M_[cC]\$?', 'Mc', text)
    text = re.sub(r'\$?M_\{[cC]\}\$?', 'Mc', text)
    text = re.sub(r'\$?M_[wW]\$?', 'Mw', text)
    text = re.sub(r'\$?M_\{[wW]\}\$?', 'Mw', text)
    text = re.sub(r'\$?M_[lL]\$?', 'ML', text)
    text = re.sub(r'\$?M_\{[lL]\}\$?', 'ML', text)
    text = re.sub(r'\$?m_[bB]\$?', 'mb', text)
    text = re.sub(r'\$?m_\{[bB]\}\$?', 'mb', text)
    text = re.sub(r'\$?M_[sS]\$?', 'Ms', text)
    text = re.sub(r'\$?M_\{[sS]\}\$?', 'Ms', text)
    text = re.sub(r'\$?M_[eE]\$?', 'Me', text)
    text = re.sub(r'\$?M_\{[eE]\}\$?', 'Me', text)
    text = re.sub(r'\$?M_0\$?', 'M0', text)
    text = re.sub(r'\$?M_\{0\}\$?', 'M0', text)
    text = re.sub(r'\$?M_\{max\}\$?', 'Mmax', text)
    text = re.sub(r'\$?M_max\$?', 'Mmax', text)
    text = re.sub(r'\$?M_\{ij\}\$?', 'M_ij', text)
    text = re.sub(r'\$?M_ij\$?', 'M_ij', text)
    text = re.sub(r'\$?t_0\$?', 't0', text)
    text = re.sub(r'\$?t_\{0\}\$?', 't0', text)
    text = re.sub(r'\$?P_[dD]\$?', 'Pd', text)
    text = re.sub(r'\$?P_d\$?', 'Pd', text)
    text = re.sub(r'\$?tau_[cC]\$?', 'tau_c', text)
    text = re.sub(r'\$?tau_c\$?', 'tau_c', text)

    # $b$-value / $a$-value
    text = re.sub(r'\$([ab])\$-([vV]alues?)', r'\1-\2', text)
    text = re.sub(r'\$([ab])\$\s*([vV]alues?)', r'\1 \2', text)

    # $P$-wave / $S$-wave / $P$- and $S$-wave
    text = re.sub(r'\$([PS])\$-([wW]aves?)', r'\1-\2', text)
    text = re.sub(r'\$([PS])\$\s*([wW]aves?)', r'\1 \2', text)
    text = re.sub(r'\$([pPsS])P\$', r'\1P', text)
    text = re.sub(r'\$SH\$', 'SH', text)

    # Clean display equations $$ ... $$ -> formatted block
    def clean_display_math(match):
        eq = match.group(1).strip()
        eq = re.sub(r'\s+', ' ', eq)
        return f"\n\n> {eq}\n\n"
    text = re.sub(r'\$\$(.*?)\$\$', clean_display_math, text, flags=re.DOTALL)

    # Clean inline math: $ ... $ (including multi-line spans up to 150 chars)
    def clean_inline_math(match):
        content = match.group(1).strip()
        content = re.sub(r'\s+', ' ', content)
        return content

    text = re.sub(r'\$([^$]{1,150}?)\$', clean_inline_math, text, flags=re.DOTALL)

    # Remove any remaining lone '$'
    text = text.replace('$', '')

    # Restore true currency symbols
    text = text.replace('__CURRENCY__', '$')

    # Remove any leftover backslashes before plain words
    text = re.sub(r'\\([a-zA-Z]+)', r'\1', text)

    # Clean up double/multiple spaces
    text = re.sub(r'[ \t]{2,}', ' ', text)
    # Fix spacing around punctuation: " ," -> ",", " ." -> "."
    text = re.sub(r'\s+([,.:;?!])', r'\1', text)
    # Fix missing space after closing parenthesis if followed by a letter
    text = re.sub(r'\)([a-zA-Z])', r') \1', text)

    # Strip ASCII box-drawing diagrams & pseudo-diagram lines
    lines = text.split('\n')
    cleaned_lines = []
    in_ascii_box = False
    for line in lines:
        s = line.strip()
        # Detect ASCII box border lines like +---------+
        if re.match(r'^\+[+\-=~|#\s]{5,}\+$', s) or re.match(r'^[+\-=~]{10,}$', s):
            in_ascii_box = True
            continue
        if in_ascii_box:
            # If line is inside an ASCII diagram
            if (s.startswith('|') and s.endswith('|')) or re.match(r'^[\s\?\|\/\\]{5,}$', s) or re.match(r'^\?[ \?]{5,}\?$', s):
                inner = s.strip('|').strip()
                inner = re.sub(r'[\?]{2,}', '', inner).strip()
                alphanumeric = re.sub(r'[^a-zA-Z0-9]', '', inner)
                if len(alphanumeric) > 3 and not alphanumeric.startswith('---'):
                    cleaned_lines.append(f"- {inner}")
                continue
            else:
                in_ascii_box = False

        # Filter out standalone lines consisting of repeated question marks, slashes, or dashes
        if re.match(r'^[\?\s\/\\]{4,}$', s) or re.match(r'^\?{3,}', s):
            continue

        cleaned_lines.append(line)

    result = '\n'.join(cleaned_lines)
    result = re.sub(r'(?m)^\s*,\s*', '', result)
    return result.strip()


def clean_report_formatting(text: str) -> str:
    """
    Post-processes LLM-generated report markdown to fix common formatting issues:
    1. LaTeX math notation and equations ($M_c$, $b$-values, >12 km, etc.)
    2. ASCII pseudo-diagram boxes and repeated question marks
    3. Encoding artifacts: '?' used instead of hyphens/dashes in compound words
    4. Broken markdown tables with stray '- |' prefixes
    5. Truncated reference field labels (e.g., 'uthors' → 'Authors')
    6. Malformed bullet points and list items
    7. Stray page markers like '_Page N/M_'
    8. Collapsed reference entries where multiple fields are on one line
    """
    if not text:
        return ""

    # --- Clean LaTeX math and ASCII box artifacts first ---
    text = clean_latex_math_and_artifacts(text)

    # --- Fix 1: Encoding artifacts (? used as hyphens/spaces) ---
    text = re.sub(r'(\w)\?(%)', r'\1\2', text)          # '30?%' → '30%'
    text = re.sub(r'(\w)\?(\w)', r'\1-\2', text)         # 'AI?driven' → 'AI-driven'
    text = re.sub(r'(\w)\?\s', r'\1- ', text)             # trailing '?' acting as dash
    text = re.sub(r'\.\?', '. ', text)                    # 'B.?Baldassarre' → 'B. Baldassarre'
    text = re.sub(r'<\?\$', '<$', text)                   # '<?$10?k' → '<$10k'
    text = re.sub(r'(\d)\?([kKmMbB])\b', r'\1\2', text)  # '10?k' → '10k'
    text = text.replace('et?al', 'et al')
    text = text.replace('Section?', 'Section ')
    text = text.replace('source?', 'source ')
    text = text.replace('Insight?', 'Insight ')
    text = text.replace('Memory?', 'Memory ')

    # --- Fix 2: Stray page markers (remove first so they don't break tables) ---
    text = re.sub(r'^\s*_Page\s+\d+/\d+_\s*$\n?', '', text, flags=re.MULTILINE)

    # --- Fix 3: Fix heading markers that got prefixed with ## accidentally ---
    text = re.sub(r'^\s*##\s*(\|[-|]+\|)\s*$', r'\1', text, flags=re.MULTILINE)

    # --- Fix 4: Broken table rows with '- |' prefix or wrapped cells ---
    text = re.sub(r'^\s*-\s*\|', '|', text, flags=re.MULTILINE)
    text = re.sub(r'\|\s*\n+\s*-\s*(\[\d+\]\s*\|)', r'| \1', text)

    # Collapse empty/blank lines between adjacent table rows so Markdown tables render properly
    for _ in range(5):
        text = re.sub(r'(\|\s*\n)\s*\n+(\s*\|)', r'\1\2', text)

    # --- Fix 5: Truncated reference field labels ---
    truncated_labels = {
        'uthors': 'Authors',
        'ear': 'Year',
        'itle': 'Title',
        'ource Type': 'Source Type',
        'ource': 'Source',
        'enue': 'Venue',
        'OI': 'DOI',
        'RL': 'URL',
        'uthority Score': 'Authority Score',
        'elevance Score': 'Relevance Score',
        'ontribution': 'Contribution',
    }
    for truncated, full in truncated_labels.items():
        text = re.sub(
            rf'^(\s*[-•*]?\s*\*?\*?)\b{re.escape(truncated)}\b:',
            rf'\1**{full}:**',
            text,
            flags=re.MULTILINE
        )
        text = re.sub(
            rf'•\s*{re.escape(truncated)}:',
            f'• **{full}:**',
            text
        )

    # --- Fix 6: Collapsed reference entries — split inline fields onto separate lines ---
    text = re.sub(r'\s*•\s*\*\*', r'\n- **', text)

    # --- Fix 7: Clean up excessive blank lines (3+ → 2) ---
    text = re.sub(r'\n{4,}', '\n\n\n', text)

    return text.strip()


def build_compilation_prompt(validated_research: str, summary: str, critique_dict: dict, sources_str: str, academic_count: int, web_count: int, memory_context: str = "") -> str:
    """
    Constructs the prompt for report synthesis with optional ChromaDB vector memory context.
    """
    score = critique_dict.get("score", "N/A")
    grade = critique_dict.get("research_grade", "N/A")
    confidence = critique_dict.get("confidence_level", "N/A")
    verdict = critique_dict.get("final_verdict", "N/A")

    coverage_dict = critique_dict.get("coverage_analysis", {})
    if isinstance(coverage_dict, dict):
        coverage = "\n".join([f"- **{sec}**: {val}" for sec, val in coverage_dict.items()])
    else:
        coverage = str(coverage_dict)

    strengths = "\n".join([f"- {s}" for s in critique_dict.get("strengths", [])]) if critique_dict.get("strengths") else "- None noted."
    weaknesses = "\n".join([f"- {w}" for w in critique_dict.get("weaknesses", [])]) if critique_dict.get("weaknesses") else "- None noted."
    
    missing_list = critique_dict.get("missing_research_areas", critique_dict.get("missing_areas", critique_dict.get("missing_topics", [])))
    missing_areas = "\n".join([f"- {m}" for m in missing_list]) if missing_list else "- None noted."
    
    imp_priorities = critique_dict.get("improvement_priorities", {})
    if isinstance(imp_priorities, dict) and imp_priorities:
        priorities_list = []
        for prio, items in imp_priorities.items():
            if isinstance(items, list):
                for item in items:
                    priorities_list.append(f"- **{prio}**: {item}")
            elif isinstance(items, str):
                priorities_list.append(f"- **{prio}**: {items}")
        suggestions = "\n".join(priorities_list) if priorities_list else "- None noted."
    else:
        suggestions = "\n".join([f"- {i}" for i in critique_dict.get("improvement_recommendations", critique_dict.get("improvement_suggestions", []))]) if critique_dict.get("improvement_recommendations") or critique_dict.get("improvement_suggestions") else "- None noted."

    memory_block = ""
    if memory_context and memory_context.strip():
        memory_block = f"""
Here is Prior Vector Database Memory Context (Retrieved from ChromaDB):
<prior_research_memory>
{memory_context}
</prior_research_memory>
"""

    return f"""You are a Master Report Synthesizer and Academic Editor.
Your job is to take validated research drafts, an executive summary, critic feedback, citation information, and historical ChromaDB vector memory, and compile them into a unified, publication-grade, professional research report.

Here is the Executive Summary:
<summary>
{summary}
</summary>

Here is the Quality Critique:
<critique>
Score: {score}/10
Research Grade: {grade}
Coverage Analysis:
{coverage}
Strengths:
{strengths}
Weaknesses:
{weaknesses}
Missing Research Areas:
{missing_areas}
Improvement Priorities:
{suggestions}
Confidence Level: {confidence}
Final Verdict: {verdict}
</critique>

Here is the Validated Research Body:
<research_body>
{validated_research}
</research_body>
{memory_block}
Here are the citation sources:
<sources>
{sources_str}
</sources>

### COMPILATION INSTRUCTIONS:
1. Synthesize these inputs into a single, cohesive, logically organized markdown document.
2. CRITICAL LENGTH & PAGE BUDGET: The report MUST be calibrated to strictly 4 to 6 standard publication pages (approximately 1,800 to 2,400 words total).
   - Keep analysis dense, substantive, and incisive while avoiding rambling, fluffy filler.
   - Do NOT produce 8-10 sprawling pages. Ensure all information is tightly edited and directly valuable.
3. The document MUST follow EXACTLY this 8-section H2 structure in order:

## 1. Executive Summary & Core Objectives
- High-level overview of the topic and problem statement
- Primary research objectives and core scope
- Key research findings and central conclusions (~250-300 words)

## 2. Foundational Concepts & Research Methodology
- Essential definitions, foundational theories, and technical background
- Research methodology and multi-source synthesis approach
- Statistics: {academic_count} Academic Papers Reviewed, {web_count} Web Sources Analyzed (~250-300 words)

## 3. Technical Deep Dive & Comparative Analysis
- Detailed technical mechanisms, architectures, or principles
- Comparative analysis table: Traditional vs Modern/Emerging Approaches
- Causal analysis: WHY and HOW the field is advancing (~400-500 words)

## 4. Real-World Applications & Industry Case Studies
- Practical enterprise/industry implementations with measurable outcomes
- High-impact case studies and adoption patterns
- Current usage, business ROI, and deployment hurdles (~300-400 words)

## 5. Key Insights & Strategic Findings
Present the top 4 to 5 strategic insights in this exact format:
**Insight [N]: [Title]**
- **Observation:** [Specific finding grounded in research]
- **Impact:** [Strategic, technological, or market implication]
- **Evidence:** [Direct supporting data/citations] (~300-350 words)

## 6. Critical Limitations, Risks & Challenges
- Core technical limitations, bottlenecks, and failure modes
- Security, ethical, regulatory, or economic obstacles
- Root-cause analysis of adoption barriers (~250-300 words)

## 7. Future Outlook & Actionable Recommendations
- Chronological projections: Short-Term (1-2 Years) vs Medium-to-Long-Term (3-5+ Years)
- Actionable recommendations targeted by role:
  - **For Researchers:** High-priority open problems
  - **For Businesses & Leaders:** Strategic timing, KPIs, and risk mitigation
  - **For Engineers & Practitioners:** Architecture best practices and technical tooling (~300-350 words)

## 8. Conclusion & Cited References
- Synthesis of findings and concluding assessment (~150 words)
- Formatted bibliography of top cited references using the exact source metadata provided below. Format each entry as:
  - **[N] [Title](URL)** — *Authors* (Year). Venue / Source. Contribution note.

Below is the metadata of the sources to compile:
{sources_str}

IMPORTANT: Do NOT invent, modify, or fabricate any URLs. You MUST render ALL provided sources as clickable links using the exact URLs provided.
4. CITATION ENFORCEMENT: Preserve, format, and align all in-text academic citations (e.g., "(Vaswani et al., 2017)") throughout the compiled report body.
5. STRICT HEADING NUMBERING: Number the main H2 headings exactly as '## 1. Executive Summary & Core Objectives', '## 2. Foundational Concepts & Research Methodology', through '## 8. Conclusion & Cited References'. H2 headings must use only integers: 1 to 8.
6. NO RAW LATEX MATH NOTATION: Do NOT wrap mathematical variables, units, or equations in dollar signs ($ or $$). NEVER output raw LaTeX symbols or backslash commands. ALWAYS write clean, executive publication plain text: 'Mc', 'Mw', 'b-value', 'a-value', '>12 km', '~8 km', '+/- 35%', 'P-wave', 'S-wave', 'log10 N(M) = a - bM'.
7. NO ASCII-ART BOXES OR PSEUDO-DIAGRAMS: Do NOT draw ASCII-art boxes, pseudo-flowcharts, or diagram boxes using +---+, |, or ??? characters. Express all architectures and pipelines as clean Markdown bullet lists or standard Markdown tables.
8. Do NOT include markdown code blocks wrapping the entire report. Output ONLY the compiled markdown report.
"""

def build_autonomous_synthesis_report(validated_research: str, summary: str, critique_dict: dict, sources_str: str, memory_context: str = "") -> str:
    """
    Builds a complete, publication-grade academic report from the validated research chapters,
    executive summary findings, and citations when external LLM compilation is constrained.
    Guarantees that error notices are never placed in the Executive Summary.
    """
    clean_summary = summary
    if not clean_summary or clean_summary.startswith("⚠️") or "Invalid API Key" in clean_summary or "Quota" in clean_summary:
        from agents.summarizer_agent import build_autonomous_summary
        clean_summary = build_autonomous_summary(validated_research)

    lines = [
        "# Comprehensive Academic & Technical Synthesis Report\n\n",
        "## 1. Executive Summary & Core Objectives\n",
        f"{clean_summary.strip()}\n\n",
        "## 2. Research Methodology & Multi-Agent Investigation Architecture\n",
        "This synthesis was compiled using an autonomous multi-agent research framework. Three parallel deep-research agents executed empirical literature retrieval across open-access academic databases (arXiv, Crossref, Semantic Scholar) and indexed domain repositories. Retrieved evidence was cross-validated, consolidated, and evaluated under academic peer-review criteria.\n\n",
        "## 3. Detailed Technical Analysis & Findings\n",
        f"{validated_research.strip()}\n\n"
    ]
    if memory_context:
        lines.append(f"## 4. Vector Memory & Historical Longitudinal Context\n{memory_context.strip()}\n\n")

    lines.append(f"## 5. Conclusion & Cited References\n{sources_str.strip()}\n")
    report = "".join(lines)
    report = clean_report_headings(report)
    report = clean_report_formatting(report)
    return report


def generate_final_report(validated_research: str, summary: str, critique_str: any, sources: list, memory_context: str = "") -> str:
    """
    Synthesizes validated components, references, and historical vector memory into a final report.
    """
    print("[Report Agent] Generating final comprehensive report (4-6 pages budget)...")
    
    if validated_research.startswith("⚠️"):
        return validated_research
        
    # Ensure critique is treated as a dict
    critique_dict = {}
    if isinstance(critique_str, dict):
        critique_dict = critique_str
    elif isinstance(critique_str, str):
        # Try parsing it as JSON just in case
        try:
            critique_dict = json.loads(critique_str)
        except Exception:
            score_match = re.search(r"Score:\s*([\d\.]+)", critique_str)
            score = score_match.group(1) if score_match else "N/A"
            critique_dict = {
                "score": score,
                "research_grade": "N/A",
                "coverage_analysis": {},
                "strengths": [critique_str] if critique_str else [],
                "weaknesses": [],
                "missing_research_areas": [],
                "improvement_priorities": {},
                "confidence_level": "N/A",
                "final_verdict": "N/A"
            }
    elif critique_str is None:
        critique_dict = {}

    # Count unique academic and web sources
    academic_sources = [s for s in sources if s.get("type") in ["academic", "pdf"]]
    web_sources = [s for s in sources if s.get("type") == "web"]
    
    academic_count = len(academic_sources)
    web_count = len(web_sources)

    # Format sources list (limit list to top 8 for clean references)
    sources_str = ""
    sliced_sources = sources[:8]
    if sliced_sources:
        for idx, src in enumerate(sliced_sources, start=1):
            title = src.get("title", "No Title")
            url = src.get("url", "#")
            authors = src.get("authors", [])
            authors_str = ", ".join(authors) if isinstance(authors, list) else str(authors)
            year = src.get("year", "N/A")
            venue = src.get("venue", "N/A")
            source_type = src.get("type", "academic" if src.get("source") in ["arXiv", "Semantic Scholar", "Crossref"] else "web")
            doi = src.get("doi") or "N/A"
            citations = src.get("citations", 0)
            
            sources_str += f"Source [{idx}]:\n"
            sources_str += f"  Title: {title}\n"
            sources_str += f"  URL: {url}\n"
            sources_str += f"  Authors: {authors_str}\n"
            sources_str += f"  Year: {year}\n"
            sources_str += f"  Venue: {venue}\n"
            sources_str += f"  Database/Source: {src.get('source', 'Unknown')}\n"
            sources_str += f"  Type: {source_type}\n"
            sources_str += f"  DOI: {doi}\n"
            sources_str += f"  Citations: {citations}\n\n"
    else:
        sources_str = "No source references available."
        
    prompt = build_compilation_prompt(validated_research, summary, critique_dict, sources_str, academic_count, web_count, memory_context=memory_context)
    
    try:
        # Use 3200 tokens — calibrated for a concise, high-density 4-6 pages report (~1800-2400 words)
        final_report = ask_groq(prompt, max_tokens=3200).strip()
        if not final_report or final_report.startswith("⚠️"):
            print(f"[Report Agent] API notice during compilation ({final_report[:60]}...). Assembling comprehensive publication report directly from validated subtopics.")
            return build_autonomous_synthesis_report(validated_research, summary, critique_dict, sources_str, memory_context=memory_context)
        
        # Clean markdown code block markers
        final_report = re.sub(r"^```markdown\s*", "", final_report)
        final_report = re.sub(r"^```\s*", "", final_report)
        final_report = re.sub(r"```$", "", final_report).strip()
        
        # Apply standard headings cleaner
        final_report = clean_report_headings(final_report)
        
        # Apply formatting cleanup (fix tables, encoding artifacts, truncated labels)
        final_report = clean_report_formatting(final_report)
        
        print("[Report Agent] Final report compilation complete.")
        return final_report
        
    except Exception as e:
        print(f"[Report Agent Error] Compilation failed: {e}. Assembling autonomous report.")
        return build_autonomous_synthesis_report(validated_research, summary, critique_dict, sources_str, memory_context=memory_context)

if __name__ == "__main__":
    print(generate_final_report("Raw facts", "Summary notes", {"score": 8.0, "strengths": ["Good work"]}, [{"title": "Source Paper", "url": "https://arxiv.org", "type": "academic"}]))

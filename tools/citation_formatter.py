import re

def format_citations(sources: list, style: str) -> str:
    """
    Formats a list of academic and web sources into standard bibliography formats:
    APA, IEEE, Harvard, BibTeX, or LaTeX \bibitem.
    """
    if not sources:
        return "No source references available."

    formatted = []
    for idx, src in enumerate(sources, start=1):
        title = src.get("title", "No Title").replace("[PDF Library] ", "").strip()
        url = src.get("url", "#")
        authors = src.get("authors", [])
        
        # Format authors nicely
        if isinstance(authors, list):
            # Clean empty/placeholder values
            authors = [a for a in authors if a and a != "Unknown Author" and a != "Web Source" and a != "Unknown"]
            if not authors:
                authors_str = "Unknown"
            elif len(authors) == 1:
                authors_str = authors[0]
            elif len(authors) == 2:
                authors_str = f"{authors[0]} and {authors[1]}"
            else:
                authors_str = f"{authors[0]} et al."
        else:
            authors_str = str(authors)
            
        year = src.get("year", "2026")
        venue = src.get("venue") or src.get("source") or "Web Search"
        doi = src.get("doi")
        
        if style == "APA":
            # Author, A. A. (Year). Title. Venue. URL or DOI.
            entry = f"{authors_str} ({year}). {title}."
            if venue and venue != "Web Search":
                entry += f" {venue}."
            if doi and doi != "N/A":
                entry += f" https://doi.org/{doi}"
            else:
                entry += f" Retrieved from {url}"
            formatted.append(f"{idx}. {entry}")
            
        elif style == "IEEE":
            # [N] A. Author, "Title," Venue, Year. [Online]. Available: URL.
            entry = f"[{idx}] {authors_str}, \"{title},\""
            if venue and venue != "Web Search":
                entry += f" in {venue},"
            entry += f" {year}."
            if url and url != "#":
                entry += f" [Online]. Available: {url}."
            if doi and doi != "N/A":
                entry += f" doi: {doi}."
            formatted.append(entry)
            
        elif style == "Harvard":
            # Author, Year. Title. Venue. Available at: <URL>.
            entry = f"{authors_str}, {year}. {title}."
            if venue and venue != "Web Search":
                entry += f" {venue}."
            if url and url != "#":
                entry += f" Available at: <{url}>."
            formatted.append(f"[{idx}] {entry}")
            
        elif style == "BibTeX":
            # LaTeX BibTeX entry format
            cite_key = f"ref_{idx}"
            # Normalize title for cite_key to make it valid BibTeX key
            clean_key = re.sub(r"[^a-zA-Z0-9]", "", title.split()[0] if title.split() else "ref")
            cite_key = f"{clean_key.lower()}_{year}_{idx}"
            
            entry = f"@article{{{cite_key},\n"
            entry += f"  author  = {{{authors_str}}},\n"
            entry += f"  title   = {{{title}}},\n"
            if venue and venue != "Web Search":
                entry += f"  journal = {{{venue}}},\n"
            entry += f"  year    = {{{year}}},\n"
            if url and url != "#":
                entry += f"  url     = {{{url}}},\n"
            if doi and doi != "N/A":
                entry += f"  doi     = {{{doi}}}\n"
            entry += "}"
            formatted.append(entry)
            
        elif style == "LaTeX Integration":
            # LaTeX \bibitem format
            cite_key = f"ref_{idx}"
            clean_key = re.sub(r"[^a-zA-Z0-9]", "", title.split()[0] if title.split() else "ref")
            cite_key = f"{clean_key.lower()}_{year}_{idx}"
            
            entry = f"\\bibitem{{{cite_key}}}\n"
            entry += f"{authors_str}, ``{title},'' "
            if venue and venue != "Web Search":
                entry += f"\\emph{{{venue}}}, "
            entry += f"{year}."
            if url and url != "#":
                entry += f" \\url{{{url}}}"
            if doi and doi != "N/A":
                entry += f" doi: {doi}"
            formatted.append(entry)

    if style in ["BibTeX", "LaTeX Integration"]:
        return "\n\n".join(formatted)
    return "\n".join(formatted)

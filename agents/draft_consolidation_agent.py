import os
import sys
import re

# Ensure project root is in the Python path to import tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.groq_client import ask_groq

def build_consolidation_prompt(raw_research_data: str) -> str:
    """
    Constructs the prompt for the Draft Consolidation Agent.
    """
    return f"""You are an elite AI Report Consolidation Agent. Your goal is to review, organize, and merge draft subtopic research reports into a unified, coherent, and clean draft.

Your responsibilities:
1. Consolidate and merge all subtopic drafts into a single continuous, logically structured research report.
2. Remove any duplicate paragraphs or highly redundant explanations between sections while preserving all unique details and technical facts.
3. Ensure smooth transitions between the consolidated sections.
4. Return the consolidated and clean markdown text.
5. Keep the content highly technical, academic, and detailed. Do NOT summarize or shorten the research. Preserve all useful information.

Here is the draft research text to consolidate:
<draft_research>
{raw_research_data}
</draft_research>

Please produce the consolidated markdown report. Output ONLY the consolidated markdown content. Do not include conversational prefaces or conclusions.
"""

def consolidate_research_drafts(subtopic_reports: list[dict]) -> str:
    """
    Consolidates subtopic drafts.
    
    Args:
        subtopic_reports (list[dict]): A list of dicts, each with 'subtopic' and 'report' keys.
        
    Returns:
        str: Consolidated research report draft.
    """
    print("[Draft Consolidation Agent] Consolidating parallel research drafts...")
    
    if not subtopic_reports:
        return "⚠️ Error: No research drafts provided for consolidation."
        
    # Combine drafts with subtopic markers
    combined_drafts = ""
    for idx, item in enumerate(subtopic_reports, start=1):
        sub = item.get("subtopic", f"Subtopic {idx}")
        rep = item.get("report", "")
        combined_drafts += f"\n\n=== DRAFT: {sub} ===\n{rep}\n"
        
    # Guard against upstream error propagation
    if "⚠️" in combined_drafts:
        print("[Draft Consolidation Agent] Upstream errors detected in drafts. Skipping consolidation.")
        return combined_drafts
        
    # Token budget: truncate if extremely long
    MAX_INPUT_CHARS = 10_000
    if len(combined_drafts) > MAX_INPUT_CHARS:
        combined_drafts = combined_drafts[:MAX_INPUT_CHARS] + "\n\n[... truncated for consolidation budget ...]"
        
    prompt = build_consolidation_prompt(combined_drafts)
    
    try:
        consolidated_report = ask_groq(prompt).strip()
        
        # Clean potential markdown wrappers
        consolidated_report = re.sub(r"^```markdown\s*", "", consolidated_report)
        consolidated_report = re.sub(r"^```\s*", "", consolidated_report)
        consolidated_report = re.sub(r"```$", "", consolidated_report).strip()
        
        print("[Draft Consolidation Agent] Consolidation complete.")
        return consolidated_report
    except Exception as e:
        print(f"[Draft Consolidation Agent Error] Consolidation loop failed. Details: {e}")
        return f"⚠️ **Draft Consolidation Agent Error:** {e}\n\nFallback Raw Drafts:\n{combined_drafts}"

if __name__ == "__main__":
    test_drafts = [
        {"subtopic": "Introduction to QML", "report": "QML runs on quantum computers. It achieves 1000x speedup today."},
        {"subtopic": "QML Challenges", "report": "Quantum computer hardware is highly noisy and no actual commercial speedup is currently demonstrated."}
    ]
    print(consolidate_research_drafts(test_drafts))

import os
import sys

# Ensure the project root is in the python path to allow importing tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.groq_client import ask_groq

def build_critic_prompt(research_text: str, summary_text: str, topic: str = "", previous_critique: dict = None) -> str:
    """
    Constructs an advanced, structured prompt for the Critic Agent with scoring rubrics,
    topic-aware expected coverage checks, and upgraded JSON schema.
    """
    topic_context = ""
    if topic:
        topic_context = f"\nResearch Topic Requested: \"{topic}\"\n"

    refinement_context = ""
    if previous_critique:
        prev_score = previous_critique.get("score", "N/A")
        prev_weaknesses = "\n- ".join(previous_critique.get("weaknesses", []))
        prev_missing = "\n- ".join(previous_critique.get("missing_research_areas", previous_critique.get("missing_areas", [])))
        
        refinement_context = f"""
### REFINE EVALUATION CONTEXT (COMPARATIVE CRITIQUE) ###
This report is a refined/optimized draft of a previous version that scored {prev_score}/10.
The previous draft had the following identified gaps:
Weaknesses to fix:
- {prev_weaknesses}
Missing topics to integrate:
- {prev_missing}

Compare the new report against the previous gaps. If the author successfully addressed the weaknesses and missing topics, you should reward their effort by increasing the score accordingly (elevating it above the 7.5 minimum criteria, moving into the 7.8 to 9.5 range if resolved with high research quality).
"""

    prompt = f"""You are an elite Principal Research Critic and Senior Peer-Review Analyst.
Your objective is to rigorously evaluate an in-depth research report and its executive summary.
{topic_context}
Your core responsibilities:
1. **Topic-Aware Expected Coverage Analysis**:
   - Deduce the standard academic/professional subtopics that a comprehensive report on "{topic}" must cover:
     * If the topic is Medical/Clinical (e.g. "Cardiovascular Surgery", "Type 2 Diabetes"), expected areas include: etiology, pathophysiology, diagnostic criteria, clinical trials, pharmacotherapy/surgical interventions, patient outcomes, and clinical guidelines.
     * If the topic is Business/Economics (e.g. "New Business Ideas", "Renewable Energy Market"), expected areas include: market size/TAM, value proposition, unit economics, customer acquisition, competitor landscape, risk assessment, and go-to-market roadmap.
     * If the topic is Legal/Policy, expected areas include: statutory frameworks, precedent case law, jurisdictional variance, and regulatory impact.
     * If the topic is Science/Engineering/Tech, expected areas include: core mechanisms, mathematical foundations, implementation architectures, trade-offs, and empirical benchmarks.
   - Contrast the report content and subtopics against this domain-appropriate list. Every missing expected topic must be reported in `missing_research_areas`.
   - IMPORTANT: DO NOT penalize non-technical or non-AI topics for lacking AI or computer science concepts. Evaluate the report strictly within its own relevant domain!
2. **Specific Content Evaluation**:
   - Evaluate the depth, clarity, and completeness of the research.
   - Do NOT repeat or summarize the research content. Focus strictly on evaluating the research quality.
   - All comments in `strengths`, `weaknesses`, `missing_research_areas`, and `improvement_priorities` must be derived from actual report content, referencing specific topics, methods, or sections. Avoid generic feedback or boilerplate phrases.
3. **Scoring and Suitability Verdict**:
   - Provide an objective overall score out of 10 (use floats, e.g., 7.5).
   - Evaluate coverage of each major section individually (e.g. Introduction, Core Concepts, Technical Depth, Applications, Challenges, Future Outlook) and provide scores.
   - Determine suitability of this report (students, professionals, researchers, publication-level work).
4. Do NOT hallucinate. Be objective, highly critical, yet constructive.

### SCORING RUBRICS & CALIBRATION ###
- **7.5 - 10.0 (Meets Minimum Criteria / High Quality)**: The report is well-structured, coherent, and covers the primary dimensions of the requested topic with substantive analysis and references. A score >= 7.5 satisfies the platform's minimum quality criteria and allows the report to proceed directly to publication without refinement.
- **Below 7.5 (Below Criteria — Triggers Self-Correction)**: If major expected sections are missing, explanations are superficial, or key areas lack depth, assign a score below 7.5 (e.g. 6.0 to 7.4). Any score below 7.5 immediately triggers the Self-Correction Loop for optimization to improve the score.

### FAIRNESS & CALIBRATION DIRECTIVE ###
Be fair, balanced, and objective. When the draft demonstrates thorough investigation, multiple coherent sections, and meaningful insight, reward it with a 7.5+ score (e.g. 7.8, 8.2, 8.8, 9.2). Reserve sub-7.5 scores for drafts that genuinely lack depth or have clear structural gaps.

{refinement_context}
Here is the Executive Summary:
<summary>
{summary_text}
</summary>

Here is the Full Research Report:
<research>
{research_text}
</research>

Please generate your critique STRICTLY as a valid JSON object. Do NOT wrap it in markdown code blocks like ```json. Output ONLY the raw JSON object.
Use the following exact schema:

{{
  "score": <float between 1.0 and 10.0>,
  "research_grade": "<string: Excellent / Very Good / Good / Fair / Poor>",
  "coverage_analysis": {{
    "Introduction": "<string: e.g. 9/10 - specific comment on introduction coverage>",
    "Core Concepts": "<string: e.g. 8/10 - specific comment on core concepts coverage>",
    "Technical Depth": "<string: e.g. 7/10 - specific comment on technical depth coverage>",
    "Applications": "<string: e.g. 9/10 - specific comment on applications coverage>",
    "Challenges": "<string: e.g. 8/10 - specific comment on challenges coverage>",
    "Future Outlook": "<string: e.g. 8/10 - specific comment on future outlook coverage>"
  }},
  "strengths": [
    "<string strength 1 - referencing actual topics found in the report>",
    "<string strength 2 - referencing actual topics found in the report>"
  ],
  "weaknesses": [
    "<string weakness 1 - referencing actual missing depth or poor coverage found in the report>",
    "<string weakness 2 - referencing actual missing depth or poor coverage found in the report>"
  ],
  "missing_research_areas": [
    "<string missing expected subtopic 1>",
    "<string missing expected subtopic 2>"
  ],
  "improvement_priorities": {{
    "High Priority": [
      "<string high priority recommendation 1>",
      "<string high priority recommendation 2>"
    ],
    "Medium Priority": [
      "<string medium priority recommendation 1>"
    ],
    "Low Priority": [
      "<string low priority recommendation 1>"
    ]
  }},
  "confidence_level": "<string: e.g. High / Medium / Low>",
  "final_verdict": "<string final judgment explaining suitability for students, professionals, researchers, or publication-level work>"
}}
"""
    return prompt

import json
import re
import time

# Default fallback critique used when the LLM fails to return valid JSON
_FALLBACK_CRITIQUE = {
    "score": 7.0,
    "research_grade": "Good",
    "coverage_analysis": {
        "Introduction": "7/10 - Auto-evaluated (LLM critique unavailable)",
        "Core Concepts": "7/10 - Auto-evaluated",
        "Technical Depth": "7/10 - Auto-evaluated",
        "Applications": "7/10 - Auto-evaluated",
        "Challenges": "7/10 - Auto-evaluated",
        "Future Outlook": "7/10 - Auto-evaluated"
    },
    "strengths": [
        "Research was generated and consolidated successfully.",
        "Multiple subtopics were covered with source material."
    ],
    "weaknesses": [
        "Automated critique was unavailable — manual review recommended.",
        "Quality score is estimated; actual depth may vary."
    ],
    "missing_research_areas": [],
    "improvement_priorities": {
        "High Priority": ["Manual review of report accuracy and completeness"],
        "Medium Priority": ["Verify source citations"],
        "Low Priority": ["Polish formatting and structure"]
    },
    "confidence_level": "Low",
    "final_verdict": "This is an auto-generated fallback critique because the AI critic was unable to produce a valid evaluation. The research content itself may still be high quality — please review manually."
}

CRITIC_MAX_RETRIES = 3
CRITIC_RETRY_DELAY = 2  # seconds, doubles each retry

def critique_research(research_text: str, summary_text: str, topic: str = "", previous_critique: dict = None) -> dict:
    """
    Main execution function for the Critic Agent.
    
    Args:
        research_text     (str):  The extensive research data.
        summary_text      (str):  The executive summary.
        topic             (str):  The original research topic.
        previous_critique (dict): Feedback dictionary from a previous loop iteration.
        
    Returns:
        dict: The structured JSON critique. Returns a fallback critique if parsing fails.
    """
    print("[Critic Agent] Initializing critique of research report and summary...")

    # --- Guard: propagate upstream errors cleanly without wasting tokens ---
    if research_text.startswith("⚠️") or summary_text.startswith("⚠️"):
        print("[Critic Agent] Upstream agent error detected — skipping critique.")
        error_msg = research_text if research_text.startswith("⚠️") else summary_text
        return {"error": error_msg}

    # --- Token budget: calibrated for rapid evaluation without hitting Groq per-minute limits ---
    MAX_RESEARCH_CHARS = 12_000
    MAX_SUMMARY_CHARS  = 3_000
    if len(research_text) > MAX_RESEARCH_CHARS:
        research_text = research_text[:MAX_RESEARCH_CHARS] + "\n\n[... truncated for token budget ...]"
    if len(summary_text) > MAX_SUMMARY_CHARS:
        summary_text = summary_text[:MAX_SUMMARY_CHARS] + "\n\n[... truncated for token budget ...]"
    
    # 1. Construct the specialized prompt
    prompt = build_critic_prompt(research_text, summary_text, topic, previous_critique)
    
    # 2. Call the LLM with internal retries
    last_raw_output = ""
    for attempt in range(1, CRITIC_MAX_RETRIES + 1):
        try:
            critique_result_str = ask_groq(prompt).strip()
            last_raw_output = critique_result_str
            
            # Guard: empty or error response from LLM
            if not critique_result_str:
                print(f"[Critic Agent] Attempt {attempt}/{CRITIC_MAX_RETRIES}: LLM returned empty response.")
                if attempt < CRITIC_MAX_RETRIES:
                    time.sleep(CRITIC_RETRY_DELAY * attempt)
                continue
            
            if critique_result_str.startswith("⚠️"):
                print(f"[Critic Agent] Attempt {attempt}/{CRITIC_MAX_RETRIES}: LLM returned error: {critique_result_str[:80]}")
                if attempt < CRITIC_MAX_RETRIES:
                    time.sleep(CRITIC_RETRY_DELAY * attempt)
                continue
            
            # Clean up any potential markdown code blocks
            critique_result_str = re.sub(r"^```json\s*", "", critique_result_str)
            critique_result_str = re.sub(r"^```\s*", "", critique_result_str)
            critique_result_str = re.sub(r"```$", "", critique_result_str).strip()
            
            # Try to extract JSON from the response if it contains extra text
            json_match = re.search(r'\{[\s\S]*\}', critique_result_str)
            if json_match:
                critique_result_str = json_match.group(0)
            
            critique_json = json.loads(critique_result_str)
            print(f"[Critic Agent] Critique successfully generated. Score: {critique_json.get('score', 'N/A')}/10")
            return critique_json
            
        except json.JSONDecodeError as e:
            print(f"[Critic Agent] Attempt {attempt}/{CRITIC_MAX_RETRIES}: JSON parse failed: {e}. Raw: {last_raw_output[:150]}...")
            if attempt < CRITIC_MAX_RETRIES:
                time.sleep(CRITIC_RETRY_DELAY * attempt)
        except Exception as e:
            print(f"[Critic Agent] Attempt {attempt}/{CRITIC_MAX_RETRIES}: Unexpected error: {e}")
            if attempt < CRITIC_MAX_RETRIES:
                time.sleep(CRITIC_RETRY_DELAY * attempt)
    
    # All retries exhausted — return graceful fallback instead of crashing
    print("[Critic Agent] All retries exhausted. Returning fallback critique (score=7.0) to keep pipeline alive.")
    fallback = dict(_FALLBACK_CRITIQUE)  # shallow copy
    fallback["_fallback"] = True
    fallback["_raw_output"] = last_raw_output[:500] if last_raw_output else "(empty)"
    return fallback

# ==========================================
# Debug/Testing Block
# ==========================================
if __name__ == "__main__":
    sample_research = "Quantum Machine Learning (QML) is an emerging field..."
    sample_summary = "QML combines quantum computing and machine learning..."
    
    print("--- Running Critic Agent Test ---")
    result = critique_research(sample_research, sample_summary)
    print("\n" + "="*40 + "\n")
    print(result)
    print("\n" + "="*40 + "\n")

import os
import sys
import json
import re

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.groq_client import ask_groq

def build_planner_prompt(topic: str) -> str:
    """
    Constructs an advanced prompt for the Planner Agent to decompose a research topic.
    """
    return f"""You are a Master Strategic Research Planner. Your objective is to architect a highly structured, professional research roadmap before downstream agents begin their investigations.

Topic to Analyze: "{topic}"

IMPORTANT RULES:
1. Decompose this topic intelligently into logical, sequential research phases SPECIFIC TO THE TOPIC DOMAIN.
2. Your subtopics, objectives, and analytical angles MUST be directly relevant to the user's topic. Do NOT inject AI, machine learning, RAG, or technology concepts unless the user's topic is explicitly about those subjects.
3. If the topic is about medicine — focus on medical science, clinical evidence, pathophysiology, treatments, epidemiology, etc.
4. If the topic is about business — focus on market analysis, revenue models, competitive landscape, customer segments, etc.
5. If the topic is about law, history, education, agriculture, or any other field — stay within that domain.
6. Avoid duplicate subtopics. Ensure a logical progression from fundamentals to advanced concepts.
7. Think like a senior research director commissioning a professional analyst report — the goal is INSIGHT, not just description.

You MUST return your output STRICTLY as a valid JSON object matching the schema below. Do not wrap it in markdown code blocks like ```json.
Output ONLY the raw JSON object.

{{
    "overview": "<string: brief summary of what the research must accomplish and WHY it matters — specific to the topic domain>",
    "objectives": [
        "<string: objective 1 — analytical goal specific to the topic, not just 'understand X'>",
        "<string: objective 2>"
    ],
    "roadmap": [
        "<string: Phase 1 description>",
        "<string: Phase 2 description>"
    ],
    "subtopics": [
        "<string: Core Subtopic 1 — must be directly relevant to the topic domain>",
        "<string: Core Subtopic 2>",
        "<string: Core Subtopic 3>"
    ],
    "analytical_angles": [
        "<string: A comparative or causal angle relevant to THIS topic, e.g., 'Traditional surgical approaches vs minimally invasive techniques' for medical topics, or 'Franchise model vs direct-to-consumer model' for business topics>",
        "<string: Another domain-relevant analytical angle>",
        "<string: Another domain-relevant analytical angle>"
    ],
    "insight_targets": [
        "<string: Most Important Recent Development in this field — identify and analyze>",
        "<string: Most Significant Strategic Opportunity — identify and analyze>",
        "<string: Most Critical Limitation or Risk — identify and analyze>",
        "<string: Most Important Emerging Trend — identify and analyze>",
        "<string: Most Relevant Research Gap — identify and analyze>"
    ],
    "technical_areas": [
        "<string: domain-specific technical concept 1>",
        "<string: domain-specific technical concept 2>"
    ],
    "suggested_order": [
        "<string: Step 1>",
        "<string: Step 2>"
    ],
    "critical_questions": [
        "<string: A key analytical question the research MUST answer, specific to the topic>"
    ],
    "focus_areas": [
        "<string: area to prioritize for deep analysis>"
    ],
    "potential_challenges": [
        "<string: hurdle in research or practical implementation>"
    ],
    "future_opportunities": [
        "<string: specific future trajectory with reasoning>"
    ]
}}
"""

def build_fallback_plan(topic: str) -> dict:
    """Constructs a domain-structured research roadmap when external AI keys are unavailable."""
    clean_topic = topic.strip().capitalize()
    return {
        "overview": f"Multi-angle scientific, empirical, and strategic investigation of '{clean_topic}', examining foundations, technical mechanisms, historical records, and future trajectories.",
        "objectives": [
            f"Analyze core definitions, background, and historical milestones of {clean_topic}",
            f"Evaluate scientific mechanisms, empirical data, and contemporary methodologies in {clean_topic}",
            f"Synthesize strategic implications, risk factors, and technological trajectories for {clean_topic}"
        ],
        "roadmap": [
            f"Phase 1: Foundations, chronological timeline, and fundamental principles of {clean_topic}",
            f"Phase 2: Deep technical and empirical analysis of {clean_topic}",
            f"Phase 3: Impact assessment, real-world case studies, and future outlook"
        ],
        "subtopics": [
            f"{clean_topic}: Historical Milestones & Foundations",
            f"{clean_topic}: Scientific Principles & Technical Analysis",
            f"{clean_topic}: Global Impact, Resilience & Future Outlook"
        ],
        "analytical_angles": [
            f"Historical observations vs modern empirical modeling in {clean_topic}",
            f"Direct structural and socio-economic effects vs secondary long-term impacts",
            f"Current mitigation/prevention frameworks vs next-generation technological solutions"
        ],
        "insight_targets": [
            f"Primary scientific mechanism driving {clean_topic}",
            f"Key technological advancements improving monitoring or execution in {clean_topic}",
            f"Critical risk factors and vulnerability bottlenecks in {clean_topic}",
            f"Comparative outcomes across key historical events in {clean_topic}",
            f"Long-term trajectory and emerging methodologies in {clean_topic}"
        ],
        "technical_areas": [
            "Empirical data modeling & monitoring networks",
            "Predictive analysis & resilience engineering"
        ],
        "suggested_order": [
            "1. Baseline data analysis",
            "2. Technical deep-dive",
            "3. Strategic synthesis"
        ],
        "critical_questions": [
            f"What are the most significant developments in {clean_topic}?",
            f"How have modern technologies transformed our understanding and management of {clean_topic}?"
        ],
        "focus_areas": [
            "Historical timeline and empirical records",
            "Technological evolution and future resilience"
        ],
        "potential_challenges": [
            "Data heterogeneity across historical records",
            "Predictive uncertainty in dynamic complex systems"
        ],
        "future_opportunities": [
            "Integration of real-time sensor networks and machine learning modeling"
        ]
    }

def generate_plan(topic: str) -> dict:
    """
    Main execution function for the Planner Agent.
    
    Args:
        topic (str): The subject to be planned.
        
    Returns:
        dict: A structured dictionary containing the roadmap.
    """
    print(f"\n[Planner Agent] Analyzing research topic: '{topic}'...")
    
    prompt = build_planner_prompt(topic)
    
    try:
        print("[Planner Agent] Generating investigation roadmap...")
        plan_str = ask_groq(prompt).strip()
        
        if plan_str.startswith("⚠️"):
            print(f"[Planner Agent Notice] AI provider returned notice: {plan_str[:80]}...")
            print("[Planner Agent] Generating structured domain roadmap via Autonomous Analytical Planner...")
            return build_fallback_plan(topic)
            
        # Clean up possible markdown wrappers
        plan_str = re.sub(r"^```json\s*", "", plan_str)
        plan_str = re.sub(r"^```\s*", "", plan_str)
        plan_str = re.sub(r"```$", "", plan_str).strip()
        
        plan_json = json.loads(plan_str)
        print("[Planner Agent] Research phases created successfully.")
        return plan_json
        
    except (json.JSONDecodeError, Exception) as e:
        print(f"[Planner Agent Notice] Falling back to structured domain roadmap: {e}")
        return build_fallback_plan(topic)

if __name__ == "__main__":
    test_topic = "AI in Healthcare"
    plan = generate_plan(test_topic)
    if plan:
        print(json.dumps(plan, indent=2))

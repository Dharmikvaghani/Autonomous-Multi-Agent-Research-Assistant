import os
import sys
import asyncio
from unittest.mock import patch

# Ensure project root is in the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrators.agent_orchestrator import AgentOrchestrator, Task

# Mock plan dictionary
MOCK_PLAN = {
    "overview": "Strategic overview of molecular modeling.",
    "objectives": ["Understand atomic structures", "Examine molecular dynamics"],
    "roadmap": ["Phase 1: Basic modeling", "Phase 2: Simulation protocols"],
    "subtopics": ["Atomic structures", "Force fields", "Molecular dynamics"],
    "technical_areas": ["DFT calculations", "Amber force field"],
    "suggested_order": ["Step 1: Setup", "Step 2: Run"],
    "critical_questions": ["What is the simulation time?"],
    "focus_areas": ["Quantum effects"],
    "potential_challenges": ["Size scaling"],
    "future_opportunities": ["AI folding models"]
}

# Mock researcher result
MOCK_RESEARCH = {
    "report": "Comprehensive subtopic report body detailing technical dynamics.",
    "sources": [{"title": "Molecular Studies", "url": "https://arxiv.org/abs/123.456"}],
    "pdf_chunks": [],
    "academic_papers": [{"title": "Molecular Studies", "url": "https://arxiv.org/abs/123.456", "year": 2024}],
    "fallback_used": False
}

# Mock validation result
MOCK_VALIDATION = "Validated research report body. No factual contradictions found."

# Mock summarizer result
MOCK_SUMMARY = "## Executive Summary\nDistilled summary.\n## Key Findings\n* Point A\n## Important Technologies\n* Tool B"

# Mock critic result
MOCK_CRITIQUE = {
    "score": 9.2,
    "report_quality_assessment": "High quality presentation.",
    "coverage_analysis": "Comprehensive topic coverage.",
    "accuracy_assessment": "Technically accurate.",
    "completeness_assessment": "Covers all key areas.",
    "strengths": ["Excellent detail"],
    "weaknesses": ["None"],
    "missing_areas": ["None"],
    "improvement_recommendations": ["Keep as is"],
    "confidence_level": "High",
    "final_verdict": "Publishable."
}

# Mock report generator result
MOCK_REPORT = "# Consolidated Research Report\n\n## Executive Summary\nDistilled summary.\n\n## Body\nValidated research report body."



async def test_orchestrator_successful_dag_execution():
    """
    Tests that the AgentOrchestrator successfully executes all 9 stages
    in the correct dependency order and compiles the final report.
    """
    with patch("orchestrators.agent_orchestrator.generate_plan", return_value=MOCK_PLAN), \
         patch("orchestrators.agent_orchestrator.generate_research", return_value=MOCK_RESEARCH), \
         patch("orchestrators.agent_orchestrator.consolidate_research_drafts", return_value=MOCK_VALIDATION), \
         patch("orchestrators.agent_orchestrator.summarize_research", return_value=MOCK_SUMMARY), \
         patch("orchestrators.agent_orchestrator.critique_research", return_value=MOCK_CRITIQUE), \
         patch("orchestrators.agent_orchestrator.generate_final_report", return_value=MOCK_REPORT), \
         patch("orchestrators.agent_orchestrator.save_research_to_memory", return_value=True), \
         patch("orchestrators.agent_orchestrator.search_memory_context", return_value=("", [])):
          
        # Initialize orchestrator
        orchestrator = AgentOrchestrator(topic="Molecular dynamics", workspace="test_workspace")
        
        # Run orchestrator
        await orchestrator.run()
        
        # Verify pipeline state
        assert orchestrator.pipeline_status == "COMPLETED"
        assert orchestrator.tasks["planner"].status == "COMPLETED"
        assert orchestrator.tasks["researcher_0"].status == "COMPLETED"
        assert orchestrator.tasks["researcher_1"].status == "COMPLETED"
        assert orchestrator.tasks["researcher_2"].status == "COMPLETED"
        assert orchestrator.tasks["draft_consolidation"].status == "COMPLETED"
        assert orchestrator.tasks["rag_enhancement"].status == "COMPLETED"
        assert orchestrator.tasks["summarizer"].status == "COMPLETED"
        assert orchestrator.tasks["critic"].status == "COMPLETED"
        assert orchestrator.tasks["self_correction"].status == "SKIPPED"  # Because score is 9.2 (>= 7.5)
        assert orchestrator.tasks["report_generator"].status == "COMPLETED"
        assert orchestrator.tasks["memory_storage"].status == "COMPLETED"
        
        # Verify compiled outputs
        assert orchestrator.tasks["report_generator"].result == MOCK_REPORT

async def test_orchestrator_self_correction_trigger():
    """
    Tests that the Self-Correction task executes if the Critic Agent
    issues a score below the threshold (< 7.5).
    """
    low_critique = MOCK_CRITIQUE.copy()
    low_critique["score"] = 6.5
    
    with patch("orchestrators.agent_orchestrator.generate_plan", return_value=MOCK_PLAN), \
         patch("orchestrators.agent_orchestrator.generate_research", return_value=MOCK_RESEARCH), \
         patch("orchestrators.agent_orchestrator.consolidate_research_drafts", return_value=MOCK_VALIDATION), \
         patch("orchestrators.agent_orchestrator.summarize_research", return_value=MOCK_SUMMARY), \
         patch("orchestrators.agent_orchestrator.critique_research", side_effect=[low_critique, MOCK_CRITIQUE]), \
         patch("orchestrators.agent_orchestrator.refine_research", return_value="Refined validated report body."), \
         patch("orchestrators.agent_orchestrator.generate_final_report", return_value=MOCK_REPORT), \
         patch("orchestrators.agent_orchestrator.save_research_to_memory", return_value=True), \
         patch("orchestrators.agent_orchestrator.search_memory_context", return_value=("", [])):
          
        # Initialize orchestrator
        orchestrator = AgentOrchestrator(topic="Molecular dynamics", workspace="test_workspace")
        
        # Run orchestrator
        await orchestrator.run()
        
        # Verify self correction status was completed (not skipped)
        assert orchestrator.pipeline_status == "COMPLETED"
        assert orchestrator.tasks["self_correction"].status == "COMPLETED"
        assert orchestrator.tasks["self_correction"].result["optimized"] is True
        assert orchestrator.tasks["self_correction"].result["score_delta"] == 2.7  # 9.2 - 6.5

async def run_tests():
    print("================================================================")
    print("  Orchestration Unit Tests")
    print("================================================================")
    
    try:
        print("Running test_orchestrator_successful_dag_execution...")
        await test_orchestrator_successful_dag_execution()
        print("  [PASS] test_orchestrator_successful_dag_execution")
        
        print("Running test_orchestrator_self_correction_trigger...")
        await test_orchestrator_self_correction_trigger()
        print("  [PASS] test_orchestrator_self_correction_trigger")
        
        print("\n  VERDICT: ALL ORCHESTRATION TESTS PASSED (100% success rate)")
        print("================================================================")
    except AssertionError as e:
        print(f"\n  [FAIL] Test failure: {e}")
        print("================================================================")
        sys.exit(1)
    except Exception as e:
        print(f"\n  [ERROR] Critical error: {e}")
        print("================================================================")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_tests())

"""Golden test set for copilot-service eval.

Two categories, scored with different metrics because they're
fundamentally different tasks:

KNOWLEDGE_BASE questions exercise the RAG pipeline (search_knowledge_base)
- these get the full metric suite (faithfulness, contextual precision/
recall) since we have real retrieved_context to score against.

LIVE_DATA questions exercise tool-calling against real telemetry/alert
state, not RAG retrieval - "context" here is a tool's JSON result, not
a document chunk, so faithfulness/contextual-precision (which are
specifically about document-grounding) don't apply the same way.
Scored with AnswerRelevancy only (does the answer address the question),
plus manual comparison against expected_output.
"""

from dataclasses import dataclass


@dataclass
class GoldenCase:
    question: str
    expected_output: str
    category: str  # "knowledge_base" | "live_data"


GOLDEN_DATASET = [
    GoldenCase(
        question="What causes condenser fouling in HVAC systems?",
        expected_output=(
            "Condenser fouling is caused by dirt or debris accumulation that reduces "
            "airflow across the condenser coil, which reduces heat rejection from the "
            "condenser to the surroundings."
        ),
        category="knowledge_base",
    ),
    GoldenCase(
        question="What evaluation metrics are commonly used to assess fault detection performance?",
        expected_output=(
            "Common metrics include true positive rate, true negative rate, false "
            "positive rate, false negative rate, and no-detection rate for detection; "
            "correct diagnosis rate and misdiagnosis rate for diagnosis. Confusion "
            "matrices, F-measure, and ROC/AUC are also used."
        ),
        category="knowledge_base",
    ),
    GoldenCase(
        question="What data sources are typically used to train data-driven fault detection models?",
        expected_output=(
            "Lab experiment data, simulation data, and real building data are the three "
            "main sources, with several public datasets available including ASHRAE "
            "Project 1043-RP and 1312-RP, and LBNL fault detection datasets."
        ),
        category="knowledge_base",
    ),
    GoldenCase(
        question="Is the condenser pressure (RTU_REFG_COND_PRES) showing any signs of a problem right now?",
        expected_output=(
            "Yes, the condenser pressure is deviating significantly from its fitted "
            "per-asset baseline, with a z-score around 18, well past the deviation "
            "threshold - this indicates an abnormal condition."
        ),
        category="live_data",
    ),
    GoldenCase(
        question="Are there any open alerts for this unit?",
        expected_output=(
            "Yes, there is one open critical alert, sourced from baseline_deviation, "
            "indicating the condenser pressure deviated significantly from its baseline."
        ),
        category="live_data",
    ),
    GoldenCase(
        question="What is the current condenser pressure reading for this unit?",
        expected_output=(
            "The current condenser pressure reading is a specific numeric value from "
            "the most recent telemetry data point for this asset."
        ),
        category="live_data",
    ),
]

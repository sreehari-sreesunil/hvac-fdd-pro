"""Function-calling schemas describing each tool to the LLM.

The `description` fields matter more than they might look like they
should - they're the ONLY thing the LLM uses to decide WHEN to call a
given tool. A vague description leads to a model that either never
calls the tool when it should, or calls it inappropriately. Being
specific about what each tool returns and when it's relevant is real,
load-bearing prompt engineering, not just documentation.

This follows the OpenAI-compatible function-calling schema format,
which Groq (and most providers - Anthropic, OpenAI, Gemini all support
this same JSON Schema shape with minor wrapper differences) use - this
is genuinely transferable knowledge, not Groq-specific.
"""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_telemetry",
            "description": (
                "Get the latest sensor reading for a specific metric on this asset "
                "(e.g. current condenser pressure, outdoor air temperature). Use this "
                "when the user asks about current/live sensor values."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {
                        "type": "string",
                        "description": (
                            "The exact metric name, e.g. 'RTU_REFG_COND_PRES', "
                            "'RTU_OA_TEMP', 'RTU_STG_STA'."
                        ),
                    },
                },
                "required": ["metric_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_baseline_status",
            "description": (
                "Check whether a specific metric on this asset is currently deviating "
                "from its normal, learned baseline for THIS specific unit - use this "
                "when the user asks whether something looks abnormal, faulty, or "
                "different from usual for a specific metric."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {
                        "type": "string",
                        "description": "The exact metric name to check, e.g. 'RTU_REFG_COND_PRES'.",
                    },
                },
                "required": ["metric_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_alert_history",
            "description": (
                "Get recent alerts raised for this asset. Use this when the user asks "
                "about alert history, open issues, or past problems flagged for this "
                "unit."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status_filter": {
                        "type": "string",
                        "enum": ["open", "acknowledged", "resolved"],
                        "description": "Optional - filter to only this status. Omit for all alerts.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "Search technical HVAC fault-detection documentation (ASHRAE/DOE/LBNL "
                "research literature) for explanations of fault types, causes, and "
                "diagnostic methods. Use this when the user asks 'why does X happen' or "
                "'what causes Y' - general domain knowledge questions, not live data "
                "about this specific asset."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A natural-language search query describing what information is needed.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diagnose_fault",
            "description": (
                "Run a full fault diagnosis for this asset: checks every trained "
                "classifier model, attributes the fault to the single most confident "
                "one if multiple fire on the same event, and explains WHICH sensor "
                "readings actually drove that specific prediction (SHAP feature "
                "importance). Use this when the user asks 'what's wrong with this "
                "unit', 'why is there a fault', 'diagnose this asset', or wants the "
                "reasoning behind a specific fault call - not for simple current-value "
                "or baseline-deviation checks, which get_telemetry/get_baseline_status "
                "already cover."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

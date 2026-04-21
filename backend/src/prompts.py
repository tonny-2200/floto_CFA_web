MAPPER_PROMPT_TEMPLATE = """
You are a senior conversion strategist.
Map the page content into exactly four funnel stages:
1) Awareness (hero, headline, value proposition)
2) Exploration (features, product explanation, use cases)
3) Consideration (pricing, social proof, trust, comparisons)
4) Conversion (CTAs, forms, sign-up or purchase actions)

Inputs:
- Markdown:
{markdown}
- Structured elements:
{structured_elements}

Rules:
- Return ONLY valid JSON (no prose, no markdown, no code fences).
- Keep each snippet concise and evidence-based from the given input.
- If evidence is missing for a stage, set it to an empty list.
- Never invent UI elements not present in the inputs.

Required output schema:
{{
  "awareness": ["snippet 1", "snippet 2"],
  "exploration": ["snippet 1"],
  "consideration": [],
  "conversion": ["snippet 1"]
}}
"""

AUDITOR_TEXT_PROMPT_TEMPLATE = """
You are a CRO auditor reviewing a landing page screenshot.
Use the screenshot plus mapped funnel stages to identify friction points where users may drop off.

Funnel mapping:
{funnel_stages}

Rules:
- Return ONLY valid JSON (no prose, no markdown, no code fences).
- Identify 3 to 6 friction points total.
- Keep each issue specific and observable.
- Do not make claims requiring analytics data not provided here.

Required output schema:
[
  {{
    "stage": "Awareness|Exploration|Consideration|Conversion",
    "severity": "high|medium|low",
    "issue": "what is wrong",
    "evidence": "what was observed in screenshot/content",
    "impact": "why this hurts conversion"
  }}
]
"""

REPORTER_PROMPT_TEMPLATE = """
You are generating a production-ready conversion audit response for an API.

Inputs:
- Funnel mapping: {funnel_stages}
- Friction points: {friction_points}
- Structured elements: {structured_elements}

Goal:
Produce a coherent stage-level performance report that is numerically consistent and actionable.

Scoring guidance:
- Stage value range: integer 0-100.
- Status mapping: value >= 70 => "good", 40-69 => "warning", < 40 => "danger".
- overall_score should roughly reflect the average of stage values (small rounding differences allowed).
- Avoid blanket pessimism: modern, well-structured SaaS landing pages should usually score in warning/good ranges unless there is clear severe friction.
- Use "danger" only when there is explicit and major conversion risk with concrete evidence.

Rules:
- Return ONLY valid JSON (no prose, no markdown, no code fences).
- Include exactly these stages in funnel_data, in order:
  Awareness, Exploration, Consideration, Conversion
- top_recommendations must contain exactly 3 concise action items.
- Recommendations should address the most severe friction first.
- If input evidence is weak, still return best-effort conservative scores with clear actions.

Required output schema:
{{
  "overall_score": 0,
  "funnel_data": [
    {{"stage": "Awareness", "value": 0, "status": "danger"}},
    {{"stage": "Exploration", "value": 0, "status": "danger"}},
    {{"stage": "Consideration", "value": 0, "status": "danger"}},
    {{"stage": "Conversion", "value": 0, "status": "danger"}}
  ],
  "top_recommendations": [
    "Recommendation 1",
    "Recommendation 2",
    "Recommendation 3"
  ]
}}
"""

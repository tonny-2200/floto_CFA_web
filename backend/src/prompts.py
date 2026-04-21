MAPPER_PROMPT_TEMPLATE = """
Analyze the following website markdown and group the content into these 4 funnel stages:
1. Awareness (Hero, Headline, Main Value Prop)
2. Exploration (Features, How it works, Problem description)
3. Consideration (Pricing, Testimonials, Comparisons, Trust badges)
4. Conversion (Primary CTAs, Forms, Sign-up links)

Markdown:
{markdown}

Return a JSON object where keys are the 4 stages and values are relevant snippets.
"""

AUDITOR_TEXT_PROMPT = (
    "Look at this website screenshot and the mapped funnel stages. "
    "Identify 3-5 friction points or 'leaks' where a user might drop off. "
    "Check for: missing CTAs, excessive text, or unclear next steps."
)

REPORTER_PROMPT_TEMPLATE = """
Create a final Conversion Audit Report.
Funnel Mapping: {funnel_stages}
Friction Points: {friction_points}

Return ONLY a JSON object with:
- overall_score (0-100)
- funnel_data (list of objects with 'stage', 'value', 'status')
- top_recommendations (list of 3 strings)
"""

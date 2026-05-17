# Non-Negotiables Before Submission

**Window:** through 2026-06-05 inclusive  
**Rule:** do not reopen these decisions before the deadline unless a legal /
compliance blocker or hard technical impossibility appears. If that happens,
escalate to the founder.

## Frozen product decisions

1. **Inspection target:** SMT first-article inspection under microscope.
2. **Workflow unit:** tile-based capture and review.
3. **Human role:** operator-in-the-loop; the system assists, it does not replace.
4. **Agent count:** exactly four agents for the submission:
   - Vision Inspector
   - FMEA Risk
   - Evidence Report
   - Supervisor
5. **Submission stack:** ADK-native orchestration with Vertex AI Gemini.
6. **UI surface:** one Streamlit UI only.
7. **Deployment target:** Cloud Run.
8. **Data posture:** documented public datasets only for the submission corpus;
   no proprietary or customer imagery.

## Frozen anti-scope

- no second frontend
- no LangGraph
- no LiteLLM
- no ROMA
- no MCP server in the submission path
- no unrelated domain narratives or hardware pivots
- no generative media pipeline inside the submission repo
- no expansion from four agents to a larger framework before the deadline

## Review rule

If a proposal conflicts with this file, the default answer before 2026-06-05 is:

> Not during the submission sprint. Revisit after 2026-06-06.

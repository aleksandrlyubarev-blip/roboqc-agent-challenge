"""Human-in-the-loop review routing.

The HITL gate is implemented in :mod:`roboqc_agent.orchestration.board_flow`:
tiles whose action carries ``triggered_hitl`` block board finalization until
the operator records an :class:`~roboqc_agent.schemas.OperatorResponse`
(accept or override) via ``POST /boards/{board_id}/operator-response``.
This package is reserved for future calibration logic (operator agreement
scoring, reviewer routing).
"""

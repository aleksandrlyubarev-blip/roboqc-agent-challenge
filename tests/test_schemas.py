from __future__ import annotations

from datetime import UTC, datetime

from roboqc_agent.schemas import (
    Action,
    ActionKind,
    BBox,
    Defect,
    DefectClass,
    Tile,
    TilePosition,
)


def test_tile_and_defect_contracts_round_trip() -> None:
    tile = Tile(
        board_id="board-1",
        lot_id="lot-1",
        position=TilePosition(row=2, col=3),
        magnification=10,
        image_uri="gs://demo/tile.png",
        captured_at=datetime.now(UTC),
        operator_id="op-1",
    )
    defect = Defect(
        tile_id=tile.tile_id,
        defect_class=DefectClass.OPEN_TRACE,
        bbox=BBox(x=1, y=2, w=3, h=4),
        confidence=0.91,
        source="labeled_detector",
    )
    action = Action(
        tile_id=tile.tile_id,
        kind=ActionKind.HUMAN_REVIEW,
        reason="low confidence",
        triggered_hitl=True,
        confidence=defect.confidence,
    )

    assert defect.tile_id == tile.tile_id
    assert action.kind is ActionKind.HUMAN_REVIEW

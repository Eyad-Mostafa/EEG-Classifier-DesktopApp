from typing import Optional, List, Dict, Any, Union
from sqlalchemy.orm import Session
from datetime import datetime
import json
from pydantic import BaseModel

from app.db.models import VisualizationPlot
from app.schemas.visualization_schema import SavePlotRequest


class VisualizationPlotRepository:
    def __init__(self, session: Session):
        self.session = session

    def _normalize_filters(self, filters: Any) -> str:
        """
        Convert dict / Pydantic model / list into a stable JSON string.
        This is important because the UniqueConstraint compares TEXT.
        """
        if isinstance(filters, BaseModel):
            filters = filters.model_dump()

        return json.dumps(filters, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def save_or_update_plot(self, payload: SavePlotRequest) -> dict:
        filters_dict = payload.filters.model_dump()
        filters_json = json.dumps(filters_dict, sort_keys=True)

        existing = (
            self.session.query(VisualizationPlot)
            .filter(
                VisualizationPlot.config_id == payload.config_id,
                VisualizationPlot.filters_json == filters_json,
            )
            .one_or_none()
        )

        now = datetime.now()

        if existing:
            existing.plot_name = payload.plot_name
            existing.created_at = now
            self.session.commit()
            self.session.refresh(existing)
            return {
                "action": "updated",
                "plot_id": existing.plot_id,
                "config_id": existing.config_id,
            }

        db_row = VisualizationPlot(
            config_id=payload.config_id,
            plot_name=payload.plot_name,
            filters_json=filters_json,
            created_at=now,
        )
        self.session.add(db_row)
        self.session.commit()
        self.session.refresh(db_row)

        return {
            "action": "created",
            "plot_id": db_row.plot_id,
            "config_id": db_row.config_id,
        }

    def get_by_id(self, plot_id: int) -> Optional[Dict[str, Any]]:
        db_row = self.session.get(VisualizationPlot, plot_id)
        return self._to_dict(db_row) if db_row else None

    def get_by_config_id(self, config_id: int) -> List[Dict[str, Any]]:
        rows = (
            self.session.query(VisualizationPlot)
            .filter(VisualizationPlot.config_id == config_id)
            .order_by(VisualizationPlot.plot_id.desc())
            .all()
        )
        return [self._to_dict(r) for r in rows]

    def delete_plot(self, plot_id: int) -> None:
        db_row = self.session.get(VisualizationPlot, plot_id)
        if not db_row:
            return
        self.session.delete(db_row)
        self.session.commit()

    def delete_all_plots(self, config_id: str) -> None:
        self.session.query(VisualizationPlot)\
            .filter(VisualizationPlot.config_id == config_id)\
            .delete(synchronize_session=False)
        self.session.commit()

    def _to_dict(self, db_row: VisualizationPlot) -> Dict[str, Any]:
        return {
            "plot_id": db_row.plot_id,
            "config_id": db_row.config_id,
            "plot_name": db_row.plot_name,
            "filters_json": db_row.filters_json,
            "created_at": db_row.created_at,
        }
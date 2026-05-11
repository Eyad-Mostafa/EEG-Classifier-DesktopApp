from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session, joinedload
from app.db.models import AnalysisRun, AnalysisResult
from datetime import datetime
import json


class AnalysisRepository:
    def __init__(self, session: Session):
        self.session = session

    def _normalize_json_text(self, data: Any) -> Optional[str]:
        if data is None:
            return None
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
            except ValueError:
                return data
            return json.dumps(parsed, sort_keys=True, separators=(",", ":"))
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def _try_parse_json(self, text: Optional[str]) -> Any:
        if text is None:
            return None
        try:
            return json.loads(text)
        except (ValueError, TypeError):
            return text

    def _run_to_dict(self, row: AnalysisRun) -> Dict[str, Any]:
        return {
            "analysis_run_id": row.analysis_run_id,
            "config_id": row.config_id,
            "pipeline_id": row.pipeline_id,
            "analysis_method_id": row.analysis_method_id,
            "source_type": row.source_type,
            "parameters_json": self._try_parse_json(row.parameters_json),
            "executed_at": row.executed_at,
            "results": [
                {
                    "result_id": r.result_id,
                    "result_path": r.result_path,
                    "result_json": self._try_parse_json(r.result_json),
                }
                for r in row.results
            ],
        }

    def get_existing_run(
        self,
        config_id: str,
        pipeline_id: Optional[int],
        analysis_method_id: int,
        source_type: str,
        parameters_json: Any = None,
    ) -> Optional[Dict[str, Any]]:
        normalized_params = self._normalize_json_text(parameters_json)

        query = (
            self.session.query(AnalysisRun)
            .options(joinedload(AnalysisRun.results))
            .filter(
                AnalysisRun.config_id == config_id,
                AnalysisRun.pipeline_id == pipeline_id,
                AnalysisRun.analysis_method_id == analysis_method_id,
                AnalysisRun.source_type == source_type,
                AnalysisRun.parameters_json == normalized_params,
            )
            .order_by(AnalysisRun.executed_at.desc())
        )

        row = query.first()
        return self._run_to_dict(row) if row else None

    def create_analysis_run(
        self,
        config_id: str,
        pipeline_id: Optional[int],
        analysis_method_id: int,
        source_type: str,
        parameters_json: Any = None,
    ) -> int:
        row = AnalysisRun(
            config_id=config_id,
            pipeline_id=pipeline_id,
            analysis_method_id=analysis_method_id,
            source_type=source_type,
            parameters_json=self._normalize_json_text(parameters_json),
            executed_at=datetime.now(),
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row.analysis_run_id

    def save_analysis_result(
        self,
        analysis_run_id: int,
        result_path: str,
        result_json: Any = None,
    ) -> int:
        row = AnalysisResult(
            analysis_run_id=analysis_run_id,
            result_path=result_path,
            result_json=self._normalize_json_text(result_json),
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row.result_id

    def get_runs_by_context(
        self,
        config_id: str,
        pipeline_id: Optional[int],
        source_type: str,
    ) -> List[Dict[str, Any]]:
        rows = (
            self.session.query(AnalysisRun)
            .options(joinedload(AnalysisRun.results))
            .filter(
                AnalysisRun.config_id == config_id,
                AnalysisRun.pipeline_id == pipeline_id,
                AnalysisRun.source_type == source_type,
            )
            .order_by(AnalysisRun.executed_at.desc())
            .all()
        )
        return [self._run_to_dict(r) for r in rows]

from typing import Optional, List, Dict, Any
from sqlalchemy import desc, nullslast
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.models import FileConfiguration
import json
from datetime import datetime


class FileConfigurationRepository:
    """
    Repository for file configurations. Commits immediately by default
    (same behaviour as your FileRepository). You can set canonicalize_json=False
    if you prefer to store the string exactly as provided.
    """

    def __init__(self, session: Session, canonicalize_json: bool = True):
        self.session = session
        self.canonicalize_json = canonicalize_json

    # ---------------------------
    # Internal helpers
    # ---------------------------
    def _normalize_json_text(self, data: Any) -> Optional[str]:
        """
        Accepts dict or JSON string or None.
        Returns a canonical JSON string (sorted keys) when possible,
        otherwise returns the original string (if not valid JSON).
        """
        if data is None:
            return None
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
            except ValueError:
                # not JSON — keep raw string
                return data
            return json.dumps(parsed, sort_keys=True, separators=(",", ":"))
        else:
            # assume dict-like
            return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def _try_parse_json(self, text: Optional[str]) -> Any:
        if text is None:
            return None
        try:
            return json.loads(text)
        except (ValueError, TypeError):
            return text  # return raw string if not JSON

    def _to_dict(self, dbobj: FileConfiguration) -> Dict[str, Any]:
        return {
            "config_id": dbobj.config_id,
            "file_id": dbobj.file_id,
            # return python object (dict) when configuration_json is valid JSON
            "configuration_json": self._try_parse_json(dbobj.configuration_json),
            "created_at": dbobj.created_at,
            "last_opened_at": dbobj.last_opened_at,
        }

    # ---------------------------
    # Read methods
    # ---------------------------
    def get_by_id(self, config_id: int) -> Optional[Dict[str, Any]]:
        dbc = self.session.get(FileConfiguration, config_id)
        return self._to_dict(dbc) if dbc else None

    def get_by_file_id(self, file_id: int) -> List[Dict[str, Any]]:
        rows = (
            self.session.query(FileConfiguration)
            .filter(FileConfiguration.file_id == file_id)
            .order_by(nullslast(desc(FileConfiguration.last_opened_at)))
            .all()
        )
        return [self._to_dict(r) for r in rows]

    def get_by_file_and_json(
        self, file_id: int, configuration_json: Any
    ) -> Optional[Dict[str, Any]]:
        if configuration_json is None:
            # search for NULL
            dbc = (
                self.session.query(FileConfiguration)
                .filter(
                    FileConfiguration.file_id == file_id,
                    FileConfiguration.configuration_json.is_(None),
                )
                .one_or_none()
            )
            return self._to_dict(dbc) if dbc else None

        json_text = (
            self._normalize_json_text(configuration_json)
            if self.canonicalize_json
            else (
                configuration_json
                if isinstance(configuration_json, str)
                else json.dumps(configuration_json)
            )
        )
        dbc = (
            self.session.query(FileConfiguration)
            .filter(
                FileConfiguration.file_id == file_id,
                FileConfiguration.configuration_json == json_text,
            )
            .one_or_none()
        )
        return self._to_dict(dbc) if dbc else None

    def list_configurations(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        rows = self.session.query(FileConfiguration).limit(limit).offset(offset).all()
        return [self._to_dict(r) for r in rows]

    # ---------------------------
    # Write methods
    # ---------------------------
    def add_configuration(self, payload: Dict[str, Any]) -> int:
        """
        payload expects at least:
          - file_id (int)
        optional:
          - configuration_json (dict or str or None)
          - created_at (datetime) — if omitted, set to now()
        Returns the config_id (existing one if unique constraint matches).
        """
        if "file_id" not in payload:
            raise ValueError("payload must contain file_id")

        file_id = payload["file_id"]
        # optional normalization / canonicalization
        config_raw = payload.get("configuration_json")
        if self.canonicalize_json:
            config_text = self._normalize_json_text(config_raw)
        else:
            if config_raw is None:
                config_text = None
            elif isinstance(config_raw, str):
                config_text = config_raw
            else:
                config_text = json.dumps(config_raw)

        # check for existing (pre-check); this avoids IntegrityError on many DB backends
        existing = (
            self.session.query(FileConfiguration)
            .filter(
                FileConfiguration.file_id == file_id,
                FileConfiguration.configuration_json == config_text,
            )
            .one_or_none()
        )
        if existing:
            existing.last_opened_at = datetime.now()
            self.session.commit()
            return existing.config_id

        dbc = FileConfiguration(
            file_id=file_id,
            configuration_json=config_text,
            created_at=payload.get("created_at") or datetime.now(),
            last_opened_at=payload.get("last_opened_at") or datetime.now(),
        )
        self.session.add(dbc)
        try:
            self.session.commit()
            self.session.refresh(dbc)
            return dbc.config_id
        except IntegrityError:
            # race: another transaction inserted the same unique combo — re-query
            self.session.rollback()
            existing = (
                self.session.query(FileConfiguration)
                .filter(
                    FileConfiguration.file_id == file_id,
                    FileConfiguration.configuration_json == config_text,
                )
                .one_or_none()
            )
            if existing:
                existing.last_opened_at = datetime.now()
                self.session.commit()
                return existing.config_id
            raise  # re-raise if something else happened

    def update_configuration(self, config_id: int, patch: Dict[str, Any]) -> None:
        dbc = self.session.get(FileConfiguration, config_id)
        if not dbc:
            return
        # if configuration_json is in patch, normalize if configured
        if "configuration_json" in patch:
            new_cfg = patch["configuration_json"]
            dbc.configuration_json = (
                self._normalize_json_text(new_cfg)
                if self.canonicalize_json
                else (new_cfg if isinstance(new_cfg, str) else json.dumps(new_cfg))
            )
            del patch["configuration_json"]

        # update other scalar fields (e.g., created_at) if present
        for k, v in patch.items():
            if hasattr(dbc, k):
                setattr(dbc, k, v)
        self.session.commit()

    def delete_configuration(self, config_id: str) -> None:
        dbc = self.session.get(FileConfiguration, config_id)
        if not dbc:
            return {"error": f"config id : {config_id}, is not exist"}
        self.session.delete(dbc)
        self.session.commit()
        return {"message": f"config with id : {config_id}, deleted"}

    def delete_by_file_id(self, file_id: str) -> int:
        rows = (
            self.session.query(FileConfiguration)
            .filter(FileConfiguration.file_id == file_id)
            .all()
        )

        deleted_count = len(rows)

        for row in rows:
            self.session.delete(row)

        self.session.commit()

        return deleted_count

    def delete_by_id_and_file_id(self, config_id: str, file_id: str) -> bool:
        dbc = (
            self.session.query(FileConfiguration)
            .filter(
                FileConfiguration.config_id == config_id,
                FileConfiguration.file_id == file_id,
            )
            .one_or_none()
        )

        if not dbc:
            return False

        self.session.delete(dbc)
        self.session.commit()

        return True

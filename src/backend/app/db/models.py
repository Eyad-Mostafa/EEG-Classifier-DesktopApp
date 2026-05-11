import uuid

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    Float,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from . import Base


class File(Base):
    __tablename__ = "files"
    file_id = Column(String, primary_key=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False, unique=True)
    file_hash = Column(String, nullable=True, unique=True)
    sampling_rate = Column(Integer, nullable=True)
    first_opened_at = Column(DateTime, nullable=True)
    last_opened_at = Column(DateTime, nullable=True, index= True)

    configurations = relationship(
        "FileConfiguration", back_populates="file", cascade="all, delete-orphan"
    )


class FileConfiguration(Base):
    __tablename__ = "file_configurations"
    config_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(
        String, ForeignKey("files.file_id", ondelete="CASCADE"), nullable=False
    )
    configuration_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)
    last_opened_at = Column(DateTime, nullable=True, index= True)

    file = relationship("File", back_populates="configurations")
    visualization_plots = relationship(
        "VisualizationPlot",
        back_populates="configuration",
        cascade="all, delete-orphan",
    )
    analysis_runs = relationship(
        "AnalysisRun", back_populates="configuration", cascade="all, delete-orphan"
    )
    pipelines = relationship(
        "Pipeline", back_populates="configuration", cascade="all, delete-orphan"
    )
    __table_args__ = (
        UniqueConstraint("file_id", "configuration_json", name="uix_file_config"),
    )


class VisualizationPlot(Base):
    __tablename__ = "visualization_plots"
    plot_id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(
        String,
        ForeignKey("file_configurations.config_id", ondelete="CASCADE"),
        nullable=False,
    )
    plot_name = Column(String, nullable=True)
    filters_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)

    configuration = relationship(
        "FileConfiguration", back_populates="visualization_plots"
    )
    __table_args__ = (
        UniqueConstraint("config_id", "filters_json", name="uix_file_config"),
    )


class AnalysisMethod(Base):
    __tablename__ = "analysis_methods"
    analysis_method_id = Column(Integer, primary_key=True, autoincrement=True)
    method_name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)

    runs = relationship("AnalysisRun", back_populates="method")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    analysis_run_id = Column(Integer, primary_key=True, autoincrement=True)

    config_id = Column(
        String,
        ForeignKey("file_configurations.config_id", ondelete="CASCADE"),
        nullable=False,
    )

    pipeline_id = Column(
        Integer,
        ForeignKey("pipelines.pipeline_id", ondelete="SET NULL"),
        nullable=True,
    )

    analysis_method_id = Column(
        Integer,
        ForeignKey("analysis_methods.analysis_method_id", ondelete="SET NULL"),
        nullable=True,
    )

    source_type = Column(String, nullable=False, default="configured")

    parameters_json = Column(Text, nullable=True)
    executed_at = Column(DateTime, nullable=True)

    configuration = relationship("FileConfiguration", back_populates="analysis_runs")
    pipeline = relationship("Pipeline", back_populates="analysis_runs")
    method = relationship("AnalysisMethod", back_populates="runs")
    results = relationship(
        "AnalysisResult", back_populates="run", cascade="all, delete-orphan"
    )


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    result_id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_run_id = Column(
        Integer,
        ForeignKey("analysis_runs.analysis_run_id", ondelete="CASCADE"),
        nullable=False,
    )
    result_path = Column(Text, nullable=False)
    result_json = Column(Text, nullable=True)

    run = relationship("AnalysisRun", back_populates="results")


class Pipeline(Base):
    __tablename__ = "pipelines"
    pipeline_id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(
        String,
        ForeignKey("file_configurations.config_id", ondelete="SET NULL"),
        nullable=True,
    )
    pipeline_name = Column(String, nullable=False)
    is_template = Column(Boolean, default=False)
    executed_at = Column(DateTime, nullable=True)
    execution_time_seconds = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    signature = Column(String(64), nullable=False, index=True)
    configuration = relationship("FileConfiguration", back_populates="pipelines")
    steps = relationship(
        "PipelineStep", back_populates="pipeline", cascade="all, delete-orphan"
    )
    analysis_runs = relationship("AnalysisRun", back_populates="pipeline")


class PipelineStep(Base):
    __tablename__ = "pipeline_steps"
    step_id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(
        Integer, ForeignKey("pipelines.pipeline_id", ondelete="CASCADE"), nullable=False
    )
    method_id = Column(
        Integer,
        ForeignKey("preprocessing_methods.method_id", ondelete="SET NULL"),
        nullable=True,
    )
    step_order = Column(Integer, nullable=False, default=0)
    parameters_json = Column(Text, nullable=True)

    pipeline = relationship("Pipeline", back_populates="steps")
    method = relationship("PreprocessingMethod", back_populates="steps")


class PreprocessingMethod(Base):
    __tablename__ = "preprocessing_methods"
    method_id = Column(Integer, primary_key=True, autoincrement=True)
    method_name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)

    steps = relationship("PipelineStep", back_populates="method")


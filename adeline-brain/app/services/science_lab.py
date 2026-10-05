"""Structured lab specifications and learner-owned notebook evidence."""
import json
from typing import Literal
from pydantic import BaseModel, Field, model_validator

NOTEBOOK_PREFIX = "Lab notebook submission:\n"


class LabColumn(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,30}$")
    label: str = Field(min_length=1, max_length=80)
    unit: str = Field(default="", max_length=20)
    kind: Literal["number", "text"]


class LabGraph(BaseModel):
    x_key: str
    y_key: str
    kind: Literal["scatter", "line"] = "scatter"


class ScienceLabSpec(BaseModel):
    question: str = Field(min_length=1, max_length=300)
    investigation_kind: Literal["controlled_experiment", "observation", "simulation"]
    prediction_prompt: str = Field(min_length=1, max_length=300)
    independent_variable: str = Field(default="", max_length=200)
    dependent_variable: str = Field(default="", max_length=200)
    controls_or_limits: list[str] = Field(min_length=1, max_length=6)
    safety: list[str] = Field(min_length=1, max_length=6)
    columns: list[LabColumn] = Field(min_length=2, max_length=6)
    graph: LabGraph | None = None
    claim_prompt: str = Field(min_length=1, max_length=250)
    evidence_prompt: str = Field(min_length=1, max_length=250)
    reasoning_prompt: str = Field(min_length=1, max_length=250)

    @model_validator(mode="after")
    def coherent_measurements(self):
        by_key = {c.key: c for c in self.columns}
        if len(by_key) != len(self.columns):
            raise ValueError("Data column keys must be unique")
        if self.investigation_kind == "controlled_experiment" and not (self.independent_variable and self.dependent_variable):
            raise ValueError("Controlled experiments identify both variables")
        if self.graph:
            keys = [self.graph.x_key, self.graph.y_key]
            if keys[0] == keys[1] or any(k not in by_key or by_key[k].kind != "number" for k in keys):
                raise ValueError("Graphs require two distinct numerical data columns")
        if any(len(s) > 300 for s in self.controls_or_limits + self.safety):
            raise ValueError("Lab guidance must be concise")
        return self


class LabNotebook(BaseModel):
    resource_id: str = Field(min_length=1, max_length=80)
    prediction: str = Field(default="", max_length=300)
    rows: list[dict[str, str]] = Field(default_factory=list, max_length=12)
    claim: str = Field(default="", max_length=300)
    evidence: str = Field(default="", max_length=300)
    reasoning: str = Field(default="", max_length=300)

    @model_validator(mode="after")
    def bounded_cells(self):
        if any(len(row) > 6 or any(len(k) > 31 or len(v) > 40 for k, v in row.items()) for row in self.rows):
            raise ValueError("Notebook rows/cells exceed limits")
        if len(NOTEBOOK_PREFIX + self.model_dump_json()) > 4000:
            raise ValueError("Notebook exceeds the Space message limit")
        return self


def notebook_from_message(text: str) -> LabNotebook | None:
    if not text.startswith(NOTEBOOK_PREFIX):
        return None
    return LabNotebook.model_validate(json.loads(text[len(NOTEBOOK_PREFIX):]))


def update_notebook(messages: list[dict], notebook: LabNotebook) -> str:
    """Update only an issued resource in this session; caller holds the session lock."""
    for message in reversed(messages):
        resource = message.get("resource_block") or {}
        metadata = resource.get("metadata") or {}
        if metadata.get("resource_id") != notebook.resource_id:
            continue
        spec = ScienceLabSpec.model_validate(metadata.get("lab"))
        columns = {c.key: c for c in spec.columns}
        import math
        for row in notebook.rows:
            if any(k not in columns for k in row):
                raise ValueError("Notebook contains unknown data columns")
            for key, value in row.items():
                if value.strip() and columns[key].kind == "number":
                    if not math.isfinite(float(value)):
                        raise ValueError("Measurements must be finite numbers")
        metadata["notebook"] = notebook.model_dump()
        return str((metadata.get("decision") or {}).get("block_id") or "")
    raise ValueError("Notebook does not belong to an issued lab in this Space")

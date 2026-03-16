from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# S0 entities
# ---------------------------------------------------------------------------


class MaterialDef(BaseModel):
    color: tuple[int, int, int]
    texture: Optional[str] = None


class BaseEntity(BaseModel):
    parent: Optional[str]
    children: Optional[list[str]] = None


class ModelRoot(BaseEntity):
    type: Literal["Model"]


class Group(BaseEntity):
    type: Literal["Group"]
    transform: list[float]  # 4x4 matrix, row-major, 16 floats


class Component(BaseEntity):
    type: Literal["Component"]
    definition: str
    transform: list[float]  # 4x4 matrix, row-major, 16 floats


class Face(BaseEntity):
    type: Literal["Face"]
    vertices: list[list[float]]  # [[x,y,z], ...]
    normal: list[float]  # [x, y, z]
    material: Optional[str] = None


class Edge(BaseEntity):
    type: Literal["Edge"]
    start: list[float]  # [x, y, z]
    end: list[float]  # [x, y, z]


Entity = ModelRoot | Group | Component | Face | Edge


class S0(BaseModel):
    timestamp: int
    model_units: Literal["mm", "cm", "m", "inch", "feet"]
    entities: dict[str, Entity]
    materials: dict[str, MaterialDef]


# ---------------------------------------------------------------------------
# Delta
# ---------------------------------------------------------------------------


class DeltaContext(BaseModel):
    active_path: list[str]  # empty = world context


class DeltaInput(BaseModel):
    entity_id: str
    entity_type: str
    position: list[float]  # local if active_path non-empty, else world
    parameters: dict  # operation-specific, open schema


class DeltaOutput(BaseModel):
    new_entities: list[str]
    modified_entities: list[str]
    deleted_entities: list[str]


class Delta(BaseModel):
    index: int
    timestamp: int
    operation: str
    context: DeltaContext
    input: DeltaInput
    output: DeltaOutput


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------


class Recording(BaseModel):
    s0: S0
    linear_flow: list[Delta]
    undo_log: list[list[Delta]]  # undo_log[i] = abandoned deltas before linear_flow[i]

    def get_state_at(self, step: int) -> list[Delta]:
        return self.linear_flow[: step + 1]

    def get_undone_at(self, step: int) -> list[Delta]:
        return self.undo_log[step]

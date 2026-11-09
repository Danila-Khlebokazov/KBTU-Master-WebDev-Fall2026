from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, ClassVar

from fastapi import Path, Query
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

ID = Annotated[int, Path(gt=0)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]

Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]
Description = Annotated[str, StringConstraints(max_length=5000)]
Priority = Annotated[int, Field(ge=1, le=5)]
ForeignId = Annotated[int, Field(gt=0)]


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PatchModel(InputModel):
    non_nullable: ClassVar[tuple[str, ...]] = ()

    @model_validator(mode="after")
    def check_patch(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        for field in self.non_nullable:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"'{field}' cannot be null")
        return self


class OutputModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# Users
class UserCreate(InputModel):
    email: Email
    name: Name


class UserUpdate(PatchModel):
    non_nullable = ("email", "name")

    email: Email | None = None
    name: Name | None = None


class UserOut(OutputModel):
    id: int
    email: str
    name: str
    created_at: datetime


# Projects
class ProjectCreate(InputModel):
    name: Name
    description: Description | None = None
    owner_id: ForeignId


class ProjectUpdate(PatchModel):
    non_nullable = ("name", "owner_id")

    name: Name | None = None
    description: Description | None = None
    owner_id: ForeignId | None = None


class ProjectOut(OutputModel):
    id: int
    name: str
    description: str | None
    owner_id: int
    created_at: datetime


class ProjectDetail(ProjectOut):
    owner: UserOut
    task_count: int


# Tasks
class TaskCreate(InputModel):
    title: Name
    description: Description | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: Priority = 3
    due_date: date | None = None
    assignee_id: ForeignId | None = None


class TaskUpdate(PatchModel):
    non_nullable = ("title", "status", "priority", "project_id")

    title: Name | None = None
    description: Description | None = None
    status: TaskStatus | None = None
    priority: Priority | None = None
    due_date: date | None = None
    project_id: ForeignId | None = None
    assignee_id: ForeignId | None = None


class TaskOut(OutputModel):
    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: int
    due_date: date | None
    project_id: int
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime

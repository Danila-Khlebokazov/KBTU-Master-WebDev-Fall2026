from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, ClassVar

from fastapi import Path, Query
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

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
Username = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, to_lower=True, pattern=r"^[a-z0-9._-]{3,50}$"
    ),
    Field(description="3-50 chars: letters, digits, '.', '_' or '-'"),
]


def _bcrypt_limit(value: str) -> str:
    if len(value.encode()) > 72:
        raise ValueError("Password must be at most 72 bytes")
    return value


Password = Annotated[
    str,
    StringConstraints(min_length=8, max_length=72),
    AfterValidator(_bcrypt_limit),
]
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]
Description = Annotated[str, StringConstraints(max_length=5000)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]
Url = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, max_length=255, pattern=r"^https?://[^\s]+$"
    ),
]
TagName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
]
Color = Annotated[str, StringConstraints(to_lower=True, pattern=r"^#[0-9a-fA-F]{6}$")]
Priority = Annotated[int, Field(ge=1, le=5)]
ForeignId = Annotated[int, Field(gt=0)]
TagIds = Annotated[
    list[ForeignId],
    Field(max_length=20),
    AfterValidator(lambda ids: list(dict.fromkeys(ids))),
]


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


# Auth
class SignupRequest(InputModel):
    username: Username
    email: Email
    name: Name
    password: Password


class LoginRequest(InputModel):
    username: Annotated[
        str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1)
    ]
    password: Annotated[str, StringConstraints(min_length=1)]


class RefreshRequest(InputModel):
    refresh_token: Annotated[str, StringConstraints(min_length=1)]


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")


class PasswordChange(InputModel):
    current_password: Annotated[str, StringConstraints(min_length=1)]
    new_password: Password

    @model_validator(mode="after")
    def check_different(self):
        if self.current_password == self.new_password:
            raise ValueError("New password must differ from the current one")
        return self


# Users
class UserReplace(InputModel):
    username: Username
    email: Email
    name: Name


class UserUpdate(PatchModel):
    non_nullable = ("username", "email", "name")

    username: Username | None = None
    email: Email | None = None
    name: Name | None = None


class UserOut(OutputModel):
    """Public user representation (no email)."""

    id: int
    username: str
    name: str
    created_at: datetime


# Profiles (one-to-one with users)
class ProfileWrite(InputModel):
    bio: Description | None = None
    job_title: ShortText | None = None
    location: ShortText | None = None
    website: Url | None = None


class ProfileUpdate(PatchModel):
    bio: Description | None = None
    job_title: ShortText | None = None
    location: ShortText | None = None
    website: Url | None = None


class ProfileOut(OutputModel):
    user_id: int
    bio: str | None
    job_title: str | None
    location: str | None
    website: str | None
    updated_at: datetime


class UserMe(UserOut):
    email: str
    profile: ProfileOut | None


# Tags (many-to-many with tasks)
class TagCreate(InputModel):
    name: TagName
    color: Color = "#6b7280"


class TagUpdate(PatchModel):
    non_nullable = ("name", "color")

    name: TagName | None = None
    color: Color | None = None


class TagOut(OutputModel):
    id: int
    name: str
    color: str
    created_at: datetime


# Projects
class ProjectCreate(InputModel):
    name: Name
    description: Description | None = None


class ProjectUpdate(PatchModel):
    non_nullable = ("name", "owner_id")

    name: Name | None = None
    description: Description | None = None
    owner_id: ForeignId | None = Field(
        default=None, description="Transfer ownership to another user"
    )


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
    tag_ids: TagIds = []


class TaskUpdate(PatchModel):
    non_nullable = ("title", "status", "priority", "project_id", "tag_ids")

    title: Name | None = None
    description: Description | None = None
    status: TaskStatus | None = None
    priority: Priority | None = None
    due_date: date | None = None
    project_id: ForeignId | None = None
    assignee_id: ForeignId | None = None
    tag_ids: TagIds | None = None


class TaskOut(OutputModel):
    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: int
    due_date: date | None
    project_id: int
    assignee_id: int | None
    tags: list[TagOut]
    created_at: datetime
    updated_at: datetime

from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class NoteWrite(StrictModel):
    revision: int = Field(ge=0)
    body_md: str = Field(default='', max_length=2000000)
    code_text: str = Field(default='', max_length=2000000)
    language: str = Field(default='python', max_length=50)


class CodeRewrite(StrictModel):
    revision: int = Field(ge=0)
    language: str = Field(max_length=50)
    history_id: int | None = Field(default=None, gt=0)


class DraftWrite(StrictModel):
    revision: int = Field(ge=0)
    code_text: str = Field(max_length=2000000)


class NoteBodyWrite(StrictModel):
    revision: int = Field(ge=0)
    body_md: str = Field(max_length=2000000)


class LanguagePreferenceWrite(StrictModel):
    revision: int = Field(ge=0)
    language: str = Field(max_length=50)


class StateWrite(StrictModel):
    revision: int = Field(ge=0)
    done: bool | None = None
    mastery: int | None = Field(default=None, ge=0, le=3)
    favorite: bool | None = None
    review_enabled: bool | None = None


class AttemptWrite(StrictModel):
    request_id: str = Field(min_length=1, max_length=128)
    outcome: Literal['independent', 'hint', 'solution', 'unfinished']
    duration_seconds: int | None = Field(default=None, ge=0, le=86400)

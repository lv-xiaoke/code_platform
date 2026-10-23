from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConfigWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    api_key: str = Field(default='', max_length=256)
    model: Literal['deepseek-flash','deepseek-v4-pro'] = 'deepseek-flash'

    @field_validator('api_key')
    @classmethod
    def key_format(cls, value):
        value = value.strip()
        if value and (not value.isascii() or any(c.isspace() for c in value)):
            raise ValueError('API Key 格式无效')
        return value


class Ask(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID
    question: str = Field(min_length=1, max_length=4000)
    dataset_id: str | None = Field(default=None, max_length=100)
    code: str = Field(default='', max_length=65536)
    language: str = Field(default='python', max_length=30)
    include_statement: bool = True
    include_code: bool = True
    notes: str | None = Field(default=None, max_length=16000)
    run_id: str | None = Field(default=None, max_length=100)
    include_history: bool = False

    @field_validator('question')
    @classmethod
    def nonempty(cls, value):
        if not value.strip(): raise ValueError('请输入问题')
        return value.strip()

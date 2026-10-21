from typing import Literal
from pydantic import Field, model_validator

from ..schemas import StrictModel


class TestCase(StrictModel):
    id: str | None = Field(default=None, max_length=100)
    name: str = Field(default='自定义测试', min_length=1, max_length=100)
    stdin: str = Field(default='', max_length=65536)
    expected_stdout: str | None = Field(default=None, max_length=65536)
    comparison: Literal['tokens','exact','unordered_lines','float'] = 'tokens'

    @model_validator(mode='after')
    def byte_limits(self):
        if len(self.stdin.encode('utf-8'))>65536 or len((self.expected_stdout or '').encode('utf-8'))>65536:
            raise ValueError('每组输入和期望输出分别不能超过 64 KiB')
        return self


class SuiteWrite(StrictModel):
    revision: int = Field(ge=0)
    cases: list[TestCase] = Field(max_length=16)
    draft: TestCase | None = None

    @model_validator(mode='after')
    def unique_ids(self):
        ids=[c.id for c in self.cases if c.id]
        if len(ids)!=len(set(ids)): raise ValueError('自定义测试编号不能重复')
        return self


class RunWrite(StrictModel):
    request_id: str = Field(min_length=1,max_length=128)
    source_code: str = Field(min_length=1,max_length=200000)
    language: Literal['python']='python'
    mode: Literal['custom','suite']='custom'
    cases: list[TestCase] = Field(default_factory=list,max_length=20)

    @model_validator(mode='after')
    def valid_mode(self):
        if not self.source_code.strip(): raise ValueError('请先编写 Python 代码')
        if self.mode=='custom' and not self.cases: raise ValueError('自定义运行至少需要一组输入')
        if self.mode=='suite' and self.cases: raise ValueError('全部测试使用服务器已保存的用例')
        return self

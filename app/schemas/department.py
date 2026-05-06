from typing import Optional, List
from pydantic import BaseModel


class MajorOut(BaseModel):
    name: str


class DepartmentOut(BaseModel):
    name: str
    majors: List[str]


class CollegeOut(BaseModel):
    college: str
    departments: List[DepartmentOut]

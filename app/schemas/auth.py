from pydantic import BaseModel


class RegisterRequest(BaseModel):
    username: str     # 아이디
    password: str
    student_id: str   # 학번
    name: str         # 이름
    grade: int        # 학년 (1~4)
    department: str   # 학과/전공


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    success: bool = True
    data: dict

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.department import College, Department, Major

router = APIRouter(prefix="/departments", tags=["departments"])

_DATA_DIR = Path(__file__).parent.parent.parent / "seed" / "data"


@router.get("")
def get_departments(
    college: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
):
    college_query = db.query(College)
    if college:
        college_query = college_query.filter(College.name == college)
    colleges = college_query.all()

    result = []
    for col in colleges:
        dept_query = db.query(Department).filter(Department.college_id == col.id)
        if department:
            dept_query = dept_query.filter(Department.name == department)
        departments = dept_query.all()

        dept_list = []
        for dept in departments:
            majors = db.query(Major).filter(Major.department_id == dept.id).all()
            dept_list.append({
                "name": dept.name,
                "majors": [m.name for m in majors],
            })
        result.append({"college": col.name, "departments": dept_list})

    return {"success": True, "data": result}


@router.get("/tree")
def get_departments_tree():
    """단과대 → 학부 → 전공 3단계 학술 트리 (UNI_DATA 구조)."""
    raw: dict = json.loads((_DATA_DIR / "uni_data.json").read_text(encoding="utf-8"))
    colleges = []
    for college_name, value in raw.items():
        if isinstance(value, list):
            colleges.append({"name": college_name, "departments": [], "majors": value})
        else:
            depts = [{"name": d, "majors": m or []} for d, m in value.items()]
            colleges.append({"name": college_name, "departments": depts, "majors": []})
    return {"success": True, "data": {"colleges": colleges}}

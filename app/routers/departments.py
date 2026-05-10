from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.department import College, Department, Major

router = APIRouter(prefix="/departments", tags=["departments"])


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

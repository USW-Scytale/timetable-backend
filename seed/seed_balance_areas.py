# -*- coding: utf-8 -*-
"""크롤한 suwon_electives.json을 읽어 Course 테이블에 balance_area / balance_area_num 채움.

사용법:
  1) DB에 컬럼 추가 (수동, MySQL):
       ALTER TABLE courses
         ADD COLUMN balance_area VARCHAR(50) NULL,
         ADD COLUMN balance_area_num TINYINT NULL,
         ADD INDEX idx_balance_area (balance_area),
         ADD INDEX idx_balance_area_num (balance_area_num);
  2) 크롤 JSON을 backend 폴더에 복사 후 실행:
       venv\\Scripts\\python.exe -m seed.seed_balance_areas suwon_electives.json
"""
import json
import sys
from pathlib import Path

from sqlalchemy import text
from app.database import SessionLocal


def main():
    json_path = sys.argv[1] if len(sys.argv) > 1 else "suwon_electives.json"
    p = Path(json_path)
    if not p.exists():
        print(f"❌ {p} 없음 — 크롤 JSON 경로 확인")
        return

    rows = json.loads(p.read_text(encoding="utf-8"))
    print(f"📂 {len(rows)}건 로드됨")

    db = SessionLocal()
    updated_by_div = 0  # subject_code+division 매칭
    updated_by_name = 0  # 이름 매칭 (분반 정보가 백엔드 DB와 다를 때 폴백)
    missing = 0

    # 매칭 우선순위: (subject_code, division) → subject_code → name+professor
    for r in rows:
        area = r.get("balance_area")
        area_num = r.get("balance_area_num")
        if not area:
            continue

        sc = r.get("subject_code")
        div = r.get("division")
        name = r.get("name")
        prof = r.get("professor")

        n = 0
        if sc and div is not None:
            n = db.execute(
                text(
                    "UPDATE courses SET balance_area=:a, balance_area_num=:n "
                    "WHERE subject_code=:sc AND division=:div"
                ),
                {"a": area, "n": area_num, "sc": sc, "div": div},
            ).rowcount

        if n == 0 and sc:
            # 분반은 달라도 같은 강의이면 영역은 같음
            n = db.execute(
                text(
                    "UPDATE courses SET balance_area=:a, balance_area_num=:n "
                    "WHERE subject_code=:sc"
                ),
                {"a": area, "n": area_num, "sc": sc},
            ).rowcount

        if n == 0 and name and prof:
            n = db.execute(
                text(
                    "UPDATE courses SET balance_area=:a, balance_area_num=:n "
                    "WHERE name=:nm AND professor=:pr"
                ),
                {"a": area, "n": area_num, "nm": name, "pr": prof},
            ).rowcount
            if n:
                updated_by_name += n
        else:
            if n:
                updated_by_div += n

        if n == 0:
            missing += 1

    db.commit()
    print(f"✅ 학수번호+분반/학수번호 매칭: {updated_by_div}건")
    print(f"✅ 이름+교수 매칭 폴백:        {updated_by_name}건")
    print(f"⚠️  매칭 안 됨 (DB에 없는 과목):  {missing}건")

    # 통계
    from app.models.course import Course
    total = db.query(Course).filter(Course.balance_area_num.isnot(None)).count()
    print(f"\n📊 balance_area_num 채워진 Course 총 {total}건")


if __name__ == "__main__":
    main()

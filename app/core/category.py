"""강의/졸업요건 카테고리 매핑 헬퍼.

Course.course_type 은 수원대 교과구분 6종을 따른다:
  major_required   = 전공필수 (전필)
  major_elective   = 전공선택 (전선)
  major_basic      = 전공교양 (전교)
  core_general     = 핵심교양 (중핵)
  balance_general  = 균형교양 (균형)
  free_general     = 자유선택 (자유)

졸업요건 grad_category_enum 은 4+1 종 그룹을 갖는다:
  major_required / major_elective / general_required / general_elective / other
"""

COURSE_TYPE_LABEL: dict[str, str] = {
    "major_required": "전공필수",
    "major_elective": "전공선택",
    "major_basic": "전공교양",
    "core_general": "핵심교양",
    "balance_general": "균형교양",
    "free_general": "자유선택",
}

# Course.course_type → 졸업요건 grad_category 매핑
GRAD_CATEGORY_OF: dict[str, str] = {
    "major_required": "major_required",
    "major_elective": "major_elective",
    "major_basic": "major_required",
    "core_general": "general_required",
    "balance_general": "general_elective",
    "free_general": "general_elective",
}

GRAD_CATEGORY_META: dict[str, dict] = {
    "major_required":   {"name": "전공필수",  "color": "#3B82F6"},
    "major_elective":   {"name": "전공선택",  "color": "#7C3AED"},
    "general_required": {"name": "교양필수",  "color": "#16A34A"},
    "general_elective": {"name": "교양선택",  "color": "#D97706"},
    "other":            {"name": "기타·자유", "color": "#EC4899"},
}

# 추천 엔진에서 "필수성"을 판별할 때 사용
REQUIRED_TYPES: set[str] = {"major_required", "core_general"}
ELECTIVE_TYPES: set[str] = {"major_elective", "major_basic", "balance_general", "free_general"}


def grad_category_of(course_type: str) -> str:
    """Course.course_type → 졸업요건 카테고리. 미지정시 'other'."""
    return GRAD_CATEGORY_OF.get(course_type, "other")


def course_type_label(course_type: str) -> str:
    return COURSE_TYPE_LABEL.get(course_type, course_type)


def grad_category_meta(category: str) -> dict:
    return GRAD_CATEGORY_META.get(category, {"name": category, "color": "#888888"})

"""HTML 목업 데이터 추출기 (1회용).

suwon_smart_timetable.html 안에 인라인된 JS 상수들을
seed/data/ 하위 JSON 파일로 분리한다.

추출 대상:
  - UNI_DATA            → seed/data/uni_data.json
  - CAMPUS_BUILDINGS    → seed/data/campus_buildings.json
  - ROOM_BUILDING_ALIASES → seed/data/room_aliases.json
  - WALK_EDGES          → seed/data/walk_edges.json
  - COURSE_POOL         → seed/data/course_pool.json
  - DEPT_GRAD_DATA      → seed/data/dept_grad_data.json

사용:
  python -m seed._extract_html_mock --html /home/jovyan/work/suwon_smart_timetable.html
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _slice_between(text: str, start_marker: str, open_ch: str, close_ch: str) -> str:
    """start_marker 이후 처음 등장하는 open_ch부터 짝이 맞는 close_ch까지 슬라이스."""
    idx = text.find(start_marker)
    if idx == -1:
        raise ValueError(f"marker not found: {start_marker!r}")
    open_idx = text.find(open_ch, idx)
    if open_idx == -1:
        raise ValueError(f"open {open_ch!r} not found after {start_marker!r}")

    depth = 0
    in_string: str | None = None
    escape = False
    for i in range(open_idx, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_string:
                in_string = None
            continue
        if ch in ("'", '"', "`"):
            in_string = ch
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[open_idx : i + 1]
    raise ValueError("unmatched braces")


def _js_object_to_json(src: str) -> str:
    """JS 객체 리터럴을 JSON 호환 문자열로 보정.
    - // 한 줄 주석 제거
    - /* 블록 */ 주석 제거
    - 작은따옴표 문자열을 큰따옴표로
    - 따옴표 없는 키를 큰따옴표 키로
    - 마지막 쉼표 제거
    """
    # /* */ 블록 주석 제거
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    # // 줄 주석 제거 (문자열 안의 //는 거의 없는 데이터라 단순 치환)
    src = re.sub(r"(?m)//[^\n]*$", "", src)

    # 작은따옴표 문자열 → 큰따옴표 (이스케이프 없음 가정. 데이터가 한글/영문만이라 안전)
    out: list[str] = []
    in_string: str | None = None
    escape = False
    for ch in src:
        if in_string:
            if escape:
                out.append(ch)
                escape = False
                continue
            if ch == "\\":
                out.append(ch)
                escape = True
                continue
            if ch == in_string:
                out.append('"' if in_string == "'" else ch)
                in_string = None
                continue
            if in_string == "'" and ch == '"':
                out.append('\\"')
                continue
            out.append(ch)
            continue
        if ch in ("'", '"'):
            in_string = ch
            out.append('"' if ch == "'" else ch)
            continue
        out.append(ch)
    s = "".join(out)

    # 따옴표 없는 키 → 큰따옴표 키 ({ name: , key: 등)
    s = re.sub(r"(?P<pre>[\{,]\s*)(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:", r'\g<pre>"\g<key>":', s)

    # 마지막 쉼표 제거 ( ,] 또는 ,} )
    s = re.sub(r",\s*([\]}])", r"\1", s)

    return s


def _parse_js_literal(src: str, label: str):
    json_src = _js_object_to_json(src)
    try:
        return json.loads(json_src)
    except json.JSONDecodeError as e:
        # 디버그용 prefix 출력
        snippet = json_src[max(0, e.pos - 60) : e.pos + 60]
        raise SystemExit(f"[{label}] JSON 파싱 실패: {e.msg} @ {e.pos}\n  near: ...{snippet}...")


def extract_uni_data(html: str):
    block = _slice_between(html, "const UNI_DATA = ", "{", "}")
    return _parse_js_literal(block, "UNI_DATA")


def extract_campus_buildings(html: str):
    block = _slice_between(html, "const CAMPUS_BUILDINGS = Object.freeze", "{", "}")
    return _parse_js_literal(block, "CAMPUS_BUILDINGS")


def extract_room_aliases(html: str):
    block = _slice_between(html, "const ROOM_BUILDING_ALIASES = Object.freeze", "{", "}")
    return _parse_js_literal(block, "ROOM_BUILDING_ALIASES")


def extract_walk_edges(html: str):
    block = _slice_between(html, "const WALK_EDGES = Object.freeze", "[", "]")
    return _parse_js_literal(block, "WALK_EDGES")


def extract_course_pool(html: str):
    # COURSE_POOL 은 이미 JSON 호환. 그대로 파싱 가능.
    block = _slice_between(html, "const COURSE_POOL = ", "[", "]")
    return json.loads(block)


def extract_dept_grad_data(html: str):
    block = _slice_between(html, "const DEPT_GRAD_DATA = ", "{", "}")
    return _parse_js_literal(block, "DEPT_GRAD_DATA")


def _dump(obj, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="HTML 목업 데이터 → JSON 분리")
    parser.add_argument("--html", default="/home/jovyan/work/suwon_smart_timetable.html")
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "data"))
    args = parser.parse_args()

    if not os.path.exists(args.html):
        print(f"[error] HTML 파일을 찾을 수 없습니다: {args.html}")
        sys.exit(1)

    os.makedirs(args.out, exist_ok=True)
    html = _read(args.html)

    extracts = [
        ("uni_data.json", extract_uni_data),
        ("campus_buildings.json", extract_campus_buildings),
        ("room_aliases.json", extract_room_aliases),
        ("walk_edges.json", extract_walk_edges),
        ("dept_grad_data.json", extract_dept_grad_data),
        ("course_pool.json", extract_course_pool),
    ]
    for fname, fn in extracts:
        data = fn(html)
        path = os.path.join(args.out, fname)
        _dump(data, path)
        size = os.path.getsize(path)
        count = len(data) if isinstance(data, (list, dict)) else 1
        print(f"  {fname:24s}  items={count:<6d}  size={size:>9,d} bytes")
    print("[done]")


if __name__ == "__main__":
    main()

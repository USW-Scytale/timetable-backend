"""baseline: suwon timetable schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "colleges",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
    )

    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("college_id", sa.Integer(), sa.ForeignKey("colleges.id"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
    )

    op.create_table(
        "majors",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
    )

    op.create_table(
        "buildings",
        sa.Column("building_id", sa.String(length=20), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("icon", sa.String(length=10), nullable=True),
        sa.Column("total_rooms", sa.Integer(), nullable=True, server_default="0"),
    )

    op.create_table(
        "rooms",
        sa.Column("room_id", sa.String(length=20), primary_key=True),
        sa.Column("building_id", sa.String(length=20), sa.ForeignKey("buildings.building_id"), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=True, server_default="30"),
        sa.Column("tags", sa.JSON(), nullable=True),
    )

    course_type = sa.Enum(
        "major_required", "major_elective", "major_basic",
        "core_general", "balance_general", "free_general",
        name="course_type_enum",
    )
    day_enum = sa.Enum("mon", "tue", "wed", "thu", "fri", "sat", name="day_enum")
    status_enum = sa.Enum("done", "in_progress", "not_taken", name="course_status_enum")

    op.create_table(
        "courses",
        sa.Column("course_id", sa.String(length=30), primary_key=True),
        sa.Column("subject_code", sa.String(length=20), nullable=False),
        sa.Column("division", sa.SmallInteger(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("professor", sa.String(length=50), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("type", course_type, nullable=False),
        sa.Column("target_grade", sa.SmallInteger(), nullable=True),
        sa.Column("offering_dept", sa.String(length=100), nullable=True),
        sa.Column("belong_dept", sa.String(length=100), nullable=True),
        sa.Column("semester", sa.String(length=10), nullable=True),
        sa.Column("max_enrollment", sa.Integer(), nullable=True, server_default="60"),
        sa.Column("grade_limits", sa.JSON(), nullable=True),
        sa.UniqueConstraint("subject_code", "division", name="uq_course_subject_division"),
    )
    op.create_index("ix_course_subject_code", "courses", ["subject_code"])
    op.create_index("ix_courses_name", "courses", ["name"])
    op.create_index("ix_courses_professor", "courses", ["professor"])

    op.create_table(
        "course_schedules",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("course_id", sa.String(length=30), sa.ForeignKey("courses.course_id"), nullable=False),
        sa.Column("day", day_enum, nullable=False),
        sa.Column("start_period", sa.Integer(), nullable=False),
        sa.Column("end_period", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.String(length=20), sa.ForeignKey("rooms.room_id"), nullable=True),
        sa.Column("room_name", sa.String(length=50), nullable=True),
    )

    op.create_table(
        "prerequisites",
        sa.Column("course_id", sa.String(length=30), sa.ForeignKey("courses.course_id"), primary_key=True),
        sa.Column("prerequisite_course_id", sa.String(length=30), sa.ForeignKey("courses.course_id"), primary_key=True),
    )

    admission_enum = sa.Enum("normal", "transfer", name="admission_type_enum")

    op.create_table(
        "students",
        sa.Column("id", sa.String(length=20), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("college", sa.String(length=100), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=False),
        sa.Column("major", sa.String(length=100), nullable=True),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("admission_type", admission_enum, nullable=False),
        sa.Column("transfer_grade", sa.Integer(), nullable=True),
        sa.Column("transfer_credits", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "student_credits",
        sa.Column("student_id", sa.String(length=20), sa.ForeignKey("students.id"), primary_key=True),
        sa.Column("major_required", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("major_core", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("major_elective", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("general", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "course_history",
        sa.Column("student_id", sa.String(length=20), sa.ForeignKey("students.id"), primary_key=True),
        sa.Column("course_id", sa.String(length=30), sa.ForeignKey("courses.course_id"), primary_key=True),
        sa.Column("status", status_enum, nullable=False),
    )

    rec_status = sa.Enum("pending", "completed", "failed", name="recommendation_status_enum")

    op.create_table(
        "timetable_recommendations",
        sa.Column("recommendation_id", sa.String(length=30), primary_key=True),
        sa.Column("student_id", sa.String(length=20), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("status", rec_status, nullable=False, server_default="completed"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "recommendation_plans",
        sa.Column("plan_id", sa.String(length=20), primary_key=True),
        sa.Column("recommendation_id", sa.String(length=30), sa.ForeignKey("timetable_recommendations.recommendation_id"), nullable=False),
        sa.Column("tag", sa.String(length=50), nullable=True),
        sa.Column("free_days", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("total_credits", sa.Integer(), nullable=True, server_default="0"),
    )

    op.create_table(
        "plan_courses",
        sa.Column("plan_id", sa.String(length=20), sa.ForeignKey("recommendation_plans.plan_id"), primary_key=True),
        sa.Column("course_id", sa.String(length=30), sa.ForeignKey("courses.course_id"), primary_key=True),
    )

    op.create_table(
        "saved_timetables",
        sa.Column("timetable_id", sa.String(length=30), primary_key=True),
        sa.Column("student_id", sa.String(length=20), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("recommendation_id", sa.String(length=30), sa.ForeignKey("timetable_recommendations.recommendation_id"), nullable=False),
        sa.Column("plan_id", sa.String(length=20), sa.ForeignKey("recommendation_plans.plan_id"), nullable=False),
        sa.Column("semester", sa.String(length=10), nullable=False),
        sa.Column("saved_at", sa.DateTime(), nullable=True),
    )

    grad_category = sa.Enum(
        "major_required", "major_elective",
        "general_required", "general_elective", "other",
        name="grad_category_enum",
    )
    req_course_cat = sa.Enum("major_required", "general_required", name="req_course_cat_enum")

    op.create_table(
        "graduation_requirements",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("department", sa.String(length=100), nullable=False),
        sa.Column("major", sa.String(length=100), nullable=True),
        sa.Column("category", grad_category, nullable=False),
        sa.Column("required_credits", sa.Integer(), nullable=False),
        sa.Column("total_required", sa.Integer(), nullable=False),
    )

    op.create_table(
        "required_courses",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("department", sa.String(length=100), nullable=False),
        sa.Column("major", sa.String(length=100), nullable=True),
        sa.Column("course_id", sa.String(length=30), sa.ForeignKey("courses.course_id"), nullable=False),
        sa.Column("category", req_course_cat, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("required_courses")
    op.drop_table("graduation_requirements")
    op.drop_table("saved_timetables")
    op.drop_table("plan_courses")
    op.drop_table("recommendation_plans")
    op.drop_table("timetable_recommendations")
    op.drop_table("course_history")
    op.drop_table("student_credits")
    op.drop_table("students")
    op.drop_table("prerequisites")
    op.drop_table("course_schedules")
    op.drop_table("courses")
    op.drop_table("rooms")
    op.drop_table("buildings")
    op.drop_table("majors")
    op.drop_table("departments")
    op.drop_table("colleges")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    for enum_name in [
        "req_course_cat_enum",
        "grad_category_enum",
        "recommendation_status_enum",
        "course_status_enum",
        "admission_type_enum",
        "day_enum",
        "course_type_enum",
    ]:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)

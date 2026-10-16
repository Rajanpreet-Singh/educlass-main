
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, TypedDict

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from src.database.db import (
    get_teacher_subjects,
    get_attendance_for_teacher,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_THRESHOLD = 75.0


def get_llm():
    """Create the Groq model only when it is needed."""
    if not os.getenv("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY is missing from .env")

    return ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0,
        max_retries=2,
    )


def load_teacher_scope(teacher_id: int):
    """
    Load only subjects owned by this teacher and attendance belonging
    to those subjects. Uses existing project database helpers.
    """
    subjects = get_teacher_subjects(teacher_id) or []

    allowed_ids = {
        str(subject["subject_id"])
        for subject in subjects
        if subject.get("subject_id") is not None
    }

    all_records = get_attendance_for_teacher(teacher_id) or []

    # Apply a second scope check before analyzing records.
    records = [
        record
        for record in all_records
        if record.get("subject_id") is not None
        and str(record["subject_id"]) in allowed_ids
    ]

    return subjects, records


def get_status(record):
    """Return True/False for known statuses; otherwise exclude the record."""
    value = record.get("is_present")
    if value is True:
        return True
    if value is False:
        return False
    return None


def get_student_details(record):
    student = record.get("students") or {}
    return {
        "student_id": record.get("student_id", student.get("student_id")),
        "student_name": student.get("name", "Unknown student"),
    }


def get_subject_details(record, subjects_by_id):
    subject_id = record.get("subject_id")
    subject = subjects_by_id.get(str(subject_id), {})
    nested = record.get("subjects") or {}

    return {
        "subject_id": subject_id,
        "subject_name": subject.get(
            "name", nested.get("name", f"Subject {subject_id}")
        ),
        "subject_code": subject.get(
            "subject_code", nested.get("subject_code", "")
        ),
    }


def safe_json(data):
    return json.dumps(data, ensure_ascii=False, default=str)


# -------------------------------------------------------------------
# DATABASE TOOL 1: Find students whose attendance is below a threshold
# -------------------------------------------------------------------

@tool
def get_low_attendance_students(
    teacher_id: int,
    threshold: float = DEFAULT_THRESHOLD,
) -> str:
    """Find students below a specified attendance percentage in the
    subjects assigned to this teacher. Returns student and subject details.
    """
    if not 0 <= threshold <= 100:
        return safe_json({"error": "Threshold must be between 0 and 100."})

    try:
        subjects, records = load_teacher_scope(teacher_id)
        subjects_by_id = {
            str(s["subject_id"]): s
            for s in subjects
            if s.get("subject_id") is not None
        }

        grouped = {}

        for record in records:
            status = get_status(record)
            if status is None:
                continue

            student = get_student_details(record)
            subject = get_subject_details(record, subjects_by_id)

            if student["student_id"] is None:
                continue

            key = (
                str(student["student_id"]),
                str(subject["subject_id"]),
            )

            if key not in grouped:
                grouped[key] = {
                    **student,
                    **subject,
                    "present": 0,
                    "total": 0,
                }

            grouped[key]["total"] += 1
            if status:
                grouped[key]["present"] += 1

        results = []

        for item in grouped.values():
            total = item["total"]
            percentage = item["present"] / total * 100 if total else 0

            if percentage < threshold:
                results.append({
                    **item,
                    "attendance_percentage": round(percentage, 2),
                    "absent": total - item["present"],
                })

        results.sort(key=lambda x: x["attendance_percentage"])

        return safe_json({
            "kind": "low_attendance",
            "threshold": threshold,
            "results": results,
            "records_analyzed": len(records),
            "message": (
                "Attendance is calculated separately for each student "
                "and subject, using records with known statuses."
            ),
        })

    except Exception as exc:
        print(f"Low attendance tool error: {exc}")
        return safe_json({
            "error": "Unable to retrieve low-attendance data."
        })


# -------------------------------------------------------------------
# DATABASE TOOL 2: Analyze attendance trend for a subject
# -------------------------------------------------------------------

@tool
def get_subject_attendance_trend(
    teacher_id: int,
    subject_code: str,
) -> str:
    """Calculate timestamp-based attendance trends for a subject code
    owned by this teacher.
    """
    try:
        subjects, records = load_teacher_scope(teacher_id)

        matched = next(
            (
                subject for subject in subjects
                if str(subject.get("subject_code", "")).strip().lower()
                == subject_code.strip().lower()
            ),
            None,
        )

        if not matched:
            available = [
                subject.get("subject_code", "")
                for subject in subjects
            ]
            return safe_json({
                "error": f"Subject code '{subject_code}' was not found "
                         "among your assigned subjects.",
                "available_subject_codes": available,
            })

        subject_id = str(matched["subject_id"])
        subject_records = [
            record for record in records
            if str(record.get("subject_id")) == subject_id
        ]

        # Each timestamp represents an attendance session. Each row
        # represents one student's status for that session.
        sessions = defaultdict(lambda: {
            "present": 0,
            "total": 0,
            "date": "",
        })

        missing_timestamps = 0

        for record in subject_records:
            status = get_status(record)
            if status is None:
                continue

            timestamp = record.get("timestamp")
            if not timestamp:
                missing_timestamps += 1
                continue

            try:
                parsed = datetime.fromisoformat(
                    str(timestamp).replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                missing_timestamps += 1
                continue

            session_key = parsed.isoformat()
            sessions[session_key]["date"] = parsed.strftime("%Y-%m-%d")
            sessions[session_key]["present"] += int(status)
            sessions[session_key]["total"] += 1

        trend = []

        for session_key, item in sessions.items():
            total = item["total"]
            trend.append({
                "session": session_key,
                "date": item["date"],
                "present": item["present"],
                "total": total,
                "absent": total - item["present"],
                "percentage": round(
                    item["present"] / total * 100, 2
                ) if total else 0,
            })

        trend.sort(key=lambda item: item["session"])

        return safe_json({
            "kind": "subject_trend",
            "subject_name": matched.get("name", ""),
            "subject_code": matched.get("subject_code", ""),
            "trend": trend,
            "missing_timestamps": missing_timestamps,
            "message": (
                "Each trend point represents one attendance session. "
                "The percentage is present students divided by students "
                "with known statuses recorded for that session."
            ),
        })

    except Exception as exc:
        print(f"Subject trend tool error: {exc}")
        return safe_json({
            "error": "Unable to calculate the subject attendance trend."
        })


# -------------------------------------------------------------------
# DATABASE TOOL 3: Compare attendance across assigned subjects
# -------------------------------------------------------------------

@tool
def compare_teacher_subjects(teacher_id: int) -> str:
    """Compare present counts, absences, and attendance percentages
    across all subjects assigned to this teacher.
    """
    try:
        subjects, records = load_teacher_scope(teacher_id)

        grouped = {
            str(subject["subject_id"]): {
                "subject_id": subject["subject_id"],
                "subject_name": subject.get("name", "Unnamed subject"),
                "subject_code": subject.get("subject_code", ""),
                "present": 0,
                "absent": 0,
                "total": 0,
            }
            for subject in subjects
            if subject.get("subject_id") is not None
        }

        for record in records:
            subject_id = str(record.get("subject_id"))
            status = get_status(record)

            if status is None or subject_id not in grouped:
                continue

            grouped[subject_id]["total"] += 1
            if status:
                grouped[subject_id]["present"] += 1
            else:
                grouped[subject_id]["absent"] += 1

        results = []

        for item in grouped.values():
            total = item["total"]
            item["attendance_percentage"] = (
                round(item["present"] / total * 100, 2)
                if total else None
            )
            results.append(item)

        results.sort(
            key=lambda item: (
                item["attendance_percentage"] is None,
                item["attendance_percentage"]
                if item["attendance_percentage"] is not None
                else 0,
            )
        )

        return safe_json({
            "kind": "subject_comparison",
            "subjects": results,
            "records_analyzed": len(records),
        })

    except Exception as exc:
        print(f"Subject comparison tool error: {exc}")
        return safe_json({
            "error": "Unable to compare subject attendance."
        })


# -------------------------------------------------------------------
# LANGGRAPH ROUTER
# -------------------------------------------------------------------

class RouteDecision(BaseModel):
    route: Literal[
        "low_attendance",
        "subject_trend",
        "subject_comparison",
    ] = Field(description="The database analysis required")
    subject_code: str | None = Field(
        default=None,
        description="Subject code when the question names one",
    )
    threshold: float = Field(
        default=DEFAULT_THRESHOLD,
        ge=0,
        le=100,
        description="Attendance threshold as a percentage",
    )


class AnalyticsState(TypedDict):
    teacher_id: int
    question: str
    route: str
    subject_code: str
    threshold: float
    analytics: dict
    answer: str
    error: str


def fallback_route(question: str) -> dict:
    """Basic routing if Groq is temporarily unavailable."""
    q = question.lower()

    code_match = re.search(
        r"\b[A-Za-z]{2,}[A-Za-z0-9_-]*\d+[A-Za-z0-9_-]*\b",
        question,
    )
    subject_code = code_match.group(0) if code_match else ""

    threshold_match = re.search(
        r"(?:below|under|less than)\s*(\d{1,3}(?:\.\d+)?)\s*%?",
        q,
    )
    threshold = (
        float(threshold_match.group(1))
        if threshold_match else DEFAULT_THRESHOLD
    )
    threshold = min(max(threshold, 0), 100)

    if any(word in q for word in [
        "low attendance", "below", "under", "at risk",
        "absentee", "students missing",
    ]):
        route = "low_attendance"
    elif subject_code and any(word in q for word in [
        "trend", "over time", "history", "progress",
    ]):
        route = "subject_trend"
    else:
        route = "subject_comparison"

    return {
        "route": route,
        "subject_code": subject_code,
        "threshold": threshold,
    }


def route_question(state: AnalyticsState) -> dict:
    question = state["question"]

    try:
        llm = get_llm()
        router = llm.with_structured_output(RouteDecision)

        decision = router.invoke([
            SystemMessage(content="""
You route teacher attendance analytics questions.

Choose:
- low_attendance: find students below an attendance threshold.
- subject_trend: show historical/session trends for one named subject.
- subject_comparison: overall summary or comparison across subjects.

Extract a subject code when present, such as CS101.
Extract a percentage threshold if the teacher specifies one.
Use 75 percent as the default threshold.
Do not answer the question; only route it.
"""),
            HumanMessage(content=question),
        ])

        subject_code = decision.subject_code or ""
        if not subject_code:
            match = re.search(
                r"\b[A-Za-z]{2,}[A-Za-z0-9_-]*\d+[A-Za-z0-9_-]*\b",
                question,
            )
            if match:
                subject_code = match.group(0)

        return {
            "route": decision.route,
            "subject_code": subject_code,
            "threshold": decision.threshold,
        }

    except Exception as exc:
        print(f"Analytics router fallback: {exc}")
        return fallback_route(question)


def low_attendance_node(state: AnalyticsState) -> dict:
    raw = get_low_attendance_students.invoke({
        "teacher_id": state["teacher_id"],
        "threshold": state["threshold"],
    })
    return {"analytics": json.loads(raw)}


def subject_trend_node(state: AnalyticsState) -> dict:
    if not state["subject_code"]:
        return {
            "analytics": {
                "error": (
                    "Please include a subject code, for example: "
                    "'Show attendance trends for CS101'."
                )
            }
        }

    raw = get_subject_attendance_trend.invoke({
        "teacher_id": state["teacher_id"],
        "subject_code": state["subject_code"],
    })
    return {"analytics": json.loads(raw)}


def comparison_node(state: AnalyticsState) -> dict:
    raw = compare_teacher_subjects.invoke({
        "teacher_id": state["teacher_id"],
    })
    return {"analytics": json.loads(raw)}


def generate_answer(state: AnalyticsState) -> dict:
    analytics = state.get("analytics", {})

    if analytics.get("error"):
        return {
            "answer": analytics["error"],
            "error": analytics["error"],
        }

    try:
        llm = get_llm()
        response = llm.invoke([
            SystemMessage(content="""
You are the teacher's Attendance Analytics Assistant.

Answer using only the database results supplied.
Use clear, professional language and explain relevant statistics.
Do not invent students, subjects, percentages, or dates.
If the data is empty or incomplete, state that clearly.
A low-attendance result is calculated separately per student and subject.
Do not suggest that you changed attendance records.
"""),
            HumanMessage(content=(
                f"Teacher's question:\n{state['question']}\n\n"
                f"Database analytics result:\n{safe_json(analytics)}\n\n"
                "Answer the teacher's question:"
            )),
        ])
        answer = response.content
        if isinstance(answer, list):
            answer = "\n".join(
                part.get("text", "") if isinstance(part, dict)
                else str(part)
                for part in answer
            )
        return {"answer": str(answer), "error": ""}

    except Exception as exc:
        print(f"Analytics answer generation error: {exc}")
        return {
            "answer": (
                "The database analysis is available below. "
                "I couldn't generate the natural-language explanation "
                "right now; please check your Groq configuration."
            ),
            "error": "",
        }


builder = StateGraph(AnalyticsState)

builder.add_node("route_question", route_question)
builder.add_node("low_attendance", low_attendance_node)
builder.add_node("subject_trend", subject_trend_node)
builder.add_node("subject_comparison", comparison_node)
builder.add_node("generate_answer", generate_answer)

builder.add_edge(START, "route_question")

builder.add_conditional_edges(
    "route_question",
    lambda state: state["route"],
    {
        "low_attendance": "low_attendance",
        "subject_trend": "subject_trend",
        "subject_comparison": "subject_comparison",
    },
)

builder.add_edge("low_attendance", "generate_answer")
builder.add_edge("subject_trend", "generate_answer")
builder.add_edge("subject_comparison", "generate_answer")
builder.add_edge("generate_answer", END)

teacher_attendance_analytics_graph = builder.compile()


def run_teacher_attendance_analytics(
    teacher_id: int,
    question: str,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict:
    """Call from Streamlit using the authenticated teacher's ID."""
    if not question or not question.strip():
        return {
            "analytics": {},
            "answer": "Please enter an analytics question.",
            "error": "",
        }

    result = teacher_attendance_analytics_graph.invoke({
        "teacher_id": int(teacher_id),
        "question": question.strip(),
        "route": "subject_comparison",
        "subject_code": "",
        "threshold": float(threshold),
        "analytics": {},
        "answer": "",
        "error": "",
    })

    return {
        "route": result["route"],
        "analytics": result["analytics"],
        "answer": result["answer"],
        "error": result.get("error", ""),
    }

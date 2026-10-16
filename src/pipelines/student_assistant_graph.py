import os
from dotenv import load_dotenv
from typing import TypedDict, Any

from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq

from src.database.db import (
    get_student_subjects,
    get_student_attendance,
)
load_dotenv()

# Check that the key exists
if not os.getenv("GROQ_API_KEY"):
    raise ValueError(
        "GROQ_API_KEY not found. Check your project's .env file."
    )


class StudentAssistantState(TypedDict):
    student_id: Any
    question: str
    academic_context: str
    answer: str


llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    max_retries=2,
)


def load_academic_context(state: StudentAssistantState):
    """Load only the authenticated student's academic records."""
    student_id = state["student_id"]

    subjects_data = get_student_subjects(student_id)
    attendance_data = get_student_attendance(student_id)

    subjects = []
    for row in subjects_data:
        subject = row.get("subjects")
        if subject:
            subjects.append(subject)

    # Calculate attendance from this student's stored records.
    attendance_by_subject = {}

    for log in attendance_data:
        subject = log.get("subjects") or {}
        subject_id = log.get("subject_id")

        if not subject_id:
            continue

        item = attendance_by_subject.setdefault(
            str(subject_id),
            {
                "subject_name": subject.get("name", "Unknown"),
                "subject_code": subject.get("subject_code", ""),
                "total": 0,
                "present": 0,
            },
        )

        item["total"] += 1
        if log.get("is_present") is True:
            item["present"] += 1

    lines = ["ENROLLED SUBJECTS:"]

    if subjects:
        for subject in subjects:
            lines.append(
                f"- {subject.get('name', 'Unknown')}; "
                f"code={subject.get('subject_code', '')}; "
                f"subject_id={subject.get('subject_id')}"
            )
    else:
        lines.append("- No enrolled subjects found.")

    lines.append("\nATTENDANCE RECORDS:")

    if attendance_by_subject:
        for item in attendance_by_subject.values():
            total = item["total"]
            present = item["present"]
            percentage = (present / total * 100) if total else 0

            lines.append(
                f"- {item['subject_name']} "
                f"({item['subject_code']}): "
                f"{present}/{total} sessions present "
                f"({percentage:.1f}%)."
            )
    else:
        lines.append("- No attendance records found.")

    return {"academic_context": "\n".join(lines)}


def answer_student(state: StudentAssistantState):
    """Generate an answer grounded in retrieved academic records."""
    prompt = f"""
You are the EDU CLASS Student Academic Assistant.

Answer the student's question using ONLY the supplied academic data.
Do not invent attendance records, classes, dates, or percentages.
If information is missing, say so clearly.
Explain calculations in simple language.
You cannot change attendance or approve requests.
Do not reveal another student's private information.

Academic data:
{state['academic_context']}

Student question:
{state['question']}
"""

    response = llm.invoke(prompt)

    return {"answer": response.content}


def build_student_assistant():
    builder = StateGraph(StudentAssistantState)

    builder.add_node("load_academic_context", load_academic_context)
    builder.add_node("answer_student", answer_student)

    builder.add_edge(START, "load_academic_context")
    builder.add_edge("load_academic_context", "answer_student")
    builder.add_edge("answer_student", END)

    return builder.compile()


student_assistant = build_student_assistant()


def ask_student_assistant(student_id, question):
    return student_assistant.invoke({
        "student_id": student_id,
        "question": question,
        "academic_context": "",
        "answer": "",
    })

from src.pipelines.student_assistant_graph import (
    ask_student_assistant,
)

# Replace with an actual student_id from your development database.
result = ask_student_assistant(
    student_id=1,
    question="Show my enrolled subjects and attendance percentages.",
)

print(result["answer"])
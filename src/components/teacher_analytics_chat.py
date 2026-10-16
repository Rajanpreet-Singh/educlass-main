
import streamlit as st

from src.pipelines.teacher_attendance_analytics_agent import (
    run_teacher_attendance_analytics,
)


def teacher_analytics_chat():
    """Floating teacher analytics chatbot with a right-side black drawer."""

    teacher_data = st.session_state.get("teacher_data")

    if not teacher_data:
        return

    teacher_id = teacher_data.get("teacher_id")
    if teacher_id is None:
        return

    if "teacher_analytics_bot_open" not in st.session_state:
        st.session_state.teacher_analytics_bot_open = False

    if "teacher_analytics_chat_history" not in st.session_state:
        st.session_state.teacher_analytics_chat_history = []

    st.markdown(
        """
        <style>
        .st-key-teacher_analytics_launcher {
            position: fixed !important;
            right: 24px !important;
            bottom: 22px !important;
            z-index: 1000000 !important;
            width: 64px !important;
        }

        .st-key-teacher_analytics_launcher button {
            width: 58px !important;
            height: 58px !important;
            min-height: 58px !important;
            border-radius: 50% !important;
            border: none !important;
            background: #2563eb !important;
            color: white !important;
            box-shadow: 0 5px 22px rgba(37,99,235,0.4) !important;
            font-size: 27px !important;
        }

        .st-key-teacher_analytics_launcher button:hover {
            background: #1d4ed8 !important;
        }

        .st-key-teacher_analytics_drawer {
            position: fixed !important;
            top: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            width: 400px !important;
            max-width: 100vw !important;
            z-index: 999999 !important;
            background: #000000 !important;
            color: #ffffff !important;
            border-left: 1px solid #333333 !important;
            box-shadow: -8px 0 30px rgba(0,0,0,0.5) !important;
            padding: 20px !important;
            overflow-y: auto !important;
            box-sizing: border-box !important;
        }

        .st-key-teacher_analytics_drawer h1,
        .st-key-teacher_analytics_drawer h2,
        .st-key-teacher_analytics_drawer h3,
        .st-key-teacher_analytics_drawer p,
        .st-key-teacher_analytics_drawer label,
        .st-key-teacher_analytics_drawer
            [data-testid="stMarkdownContainer"] {
            color: #ffffff !important;
        }

        .st-key-teacher_analytics_drawer
            [data-testid="stChatMessage"] {
            background: #171717 !important;
            color: #ffffff !important;
            border: 1px solid #333333 !important;
            border-radius: 14px !important;
            padding: 0.8rem !important;
        }

        .st-key-teacher_analytics_drawer input {
            background: #171717 !important;
            color: #ffffff !important;
            border: 1px solid #444444 !important;
        }

        .st-key-teacher_analytics_drawer input::placeholder {
            color: #aaaaaa !important;
        }

        .st-key-teacher_analytics_drawer button {
            border-radius: 10px !important;
        }

        @media (max-width: 480px) {
            .st-key-teacher_analytics_drawer {
                width: 100vw !important;
                padding: 14px !important;
            }

            .st-key-teacher_analytics_launcher {
                right: 16px !important;
                bottom: 16px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Floating bot icon
    with st.container(key="teacher_analytics_launcher"):
        label = (
            "✕"
            if st.session_state.teacher_analytics_bot_open
            else "🤖"
        )

        if st.button(
            label,
            key="teacher_analytics_bot_toggle",
            help="Open or close Teacher Analytics Assistant",
            use_container_width=True,
        ):
            st.session_state.teacher_analytics_bot_open = (
                not st.session_state.teacher_analytics_bot_open
            )
            st.rerun()

    if not st.session_state.teacher_analytics_bot_open:
        return

    # Right-side chat drawer
    with st.container(key="teacher_analytics_drawer"):
        header_col, close_col = st.columns([5, 1])

        with header_col:
            st.subheader("📊 Teacher Analytics Assistant")
            st.caption("Powered by LangGraph + Groq + Supabase")

        with close_col:
            if st.button(
                "✕",
                key="teacher_analytics_close",
                help="Close chat",
            ):
                st.session_state.teacher_analytics_bot_open = False
                st.rerun()

        st.divider()

        chat_area = st.container(height=440)

        with chat_area:
            if not st.session_state.teacher_analytics_chat_history:
                st.markdown("### 👋 Hello, Teacher!")
                st.write(
                    "Ask me about low-attendance students, subject "
                    "attendance trends, or comparisons across your subjects."
                )
                st.caption("Try asking:")
                st.markdown(
                    "- Which students have attendance below 75%?\n"
                    "- Show attendance trends for CS101.\n"
                    "- Compare attendance across my subjects.\n"
                    "- Which subject has the highest absenteeism?"
                )

            for message in st.session_state.teacher_analytics_chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        with st.form(
            "teacher_analytics_chat_form",
            clear_on_submit=True,
            border=False,
        ):
            question = st.text_input(
                "Message",
                placeholder="Ask about attendance...",
                label_visibility="collapsed",
            )

            send_col, clear_col = st.columns([3, 1])

            with send_col:
                submitted = st.form_submit_button(
                    "➤ Send",
                    use_container_width=True,
                    type="primary",
                )

            with clear_col:
                clear_clicked = st.form_submit_button(
                    "Clear",
                    use_container_width=True,
                )

        if clear_clicked:
            st.session_state.teacher_analytics_chat_history = []
            st.rerun()

        if submitted and question.strip():
            question = question.strip()

            st.session_state.teacher_analytics_chat_history.append({
                "role": "user",
                "content": question,
            })

            try:
                with st.spinner("Analyzing attendance..."):
                    result = run_teacher_attendance_analytics(
                        teacher_id=teacher_id,
                        question=question,
                    )

                answer = result.get(
                    "answer",
                    "Sorry, I couldn't generate an answer.",
                )

                analytics = result.get("analytics", {})

                # Display concise, real database results with the answer.
                if analytics.get("kind") == "low_attendance":
                    answer += (
                        "\n\n**Matching student-subject records:** "
                        f"{len(analytics.get('results', []))}"
                    )

                elif analytics.get("kind") == "subject_trend":
                    answer += (
                        "\n\n**Attendance sessions analyzed:** "
                        f"{len(analytics.get('trend', []))}"
                    )

                elif analytics.get("kind") == "subject_comparison":
                    answer += (
                        "\n\n**Subjects analyzed:** "
                        f"{len(analytics.get('subjects', []))}"
                    )

                st.session_state.teacher_analytics_chat_history.append({
                    "role": "assistant",
                    "content": answer,
                })

            except Exception as exc:
                print(f"Teacher analytics chatbot error: {exc}")

                st.session_state.teacher_analytics_chat_history.append({
                    "role": "assistant",
                    "content": (
                        "Sorry, I couldn't process that question. "
                        "Please check the Groq API and Supabase connection."
                    ),
                })

            st.rerun()

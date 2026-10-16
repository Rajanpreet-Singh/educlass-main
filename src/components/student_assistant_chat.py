
import streamlit as st

from src.pipelines.student_assistant_graph import (
    ask_student_assistant,
)


def student_assistant_chat():
    """Floating academic chatbot with a right-side chat drawer."""

    student_data = st.session_state.get("student_data")

    if not student_data:
        return

    student_id = student_data.get("student_id")

    if student_id is None:
        return

    # Persistent state across Streamlit reruns
    if "academic_bot_open" not in st.session_state:
        st.session_state.academic_bot_open = False

    if "academic_chat_history" not in st.session_state:
        st.session_state.academic_chat_history = []

    # Modern floating button and drawer styling
    st.markdown(
        """
        <style>
        /* Floating launcher in the bottom-right corner */
        .st-key-academic_bot_launcher {
            position: fixed !important;
            right: 24px !important;
            bottom: 22px !important;
            z-index: 1000000 !important;
            width: 64px !important;
        }

        .st-key-academic_bot_launcher button {
            width: 58px !important;
            height: 58px !important;
            min-height: 58px !important;
            border-radius: 50% !important;
            border: none !important;
            background: #2563eb !important;
            color: white !important;
            box-shadow: 0 5px 22px rgba(37, 99, 235, 0.4) !important;
            font-size: 27px !important;
            transition: transform 0.2s ease !important;
        }

        .st-key-academic_bot_launcher button:hover {
            background: #1d4ed8 !important;
            transform: scale(1.07) !important;
        }

        /* Right-side drawer */
        .st-key-academic_bot_drawer {
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

/* Make text inside the panel white */
.st-key-academic_bot_drawer h1,
.st-key-academic_bot_drawer h2,
.st-key-academic_bot_drawer h3,
.st-key-academic_bot_drawer p,
.st-key-academic_bot_drawer label,
.st-key-academic_bot_drawer span,
.st-key-academic_bot_drawer [data-testid="stMarkdownContainer"] {
    color: #ffffff !important;
}

/* Dark chat messages */
.st-key-academic_bot_drawer [data-testid="stChatMessage"] {
    background: #171717 !important;
    color: #ffffff !important;
    border: 1px solid #333333 !important;
    padding: 0.8rem !important;
    border-radius: 14px !important;
}

/* Dark input field */
.st-key-academic_bot_drawer input {
    background: #171717 !important;
    color: #ffffff !important;
    border: 1px solid #444444 !important;
}

/* Placeholder text */
.st-key-academic_bot_drawer input::placeholder {
    color: #aaaaaa !important;
}

        .st-key-academic_bot_drawer [data-testid="stVerticalBlock"] {
            gap: 0.7rem;
        }

        .st-key-academic_bot_drawer [data-testid="stChatMessage"] {
            padding: 0.8rem !important;
            border-radius: 14px !important;
        }

        .st-key-academic_bot_drawer .stButton button {
            border-radius: 10px !important;
        }

        /* Narrow screens */
        @media (max-width: 480px) {
            .st-key-academic_bot_drawer {
                width: 100vw !important;
                padding: 14px !important;
            }

            .st-key-academic_bot_launcher {
                right: 16px !important;
                bottom: 16px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Launcher: fixed to the bottom-right by CSS
    with st.container(key="academic_bot_launcher"):
        launcher_label = (
            "✕" if st.session_state.academic_bot_open else "🤖"
        )

        if st.button(
            launcher_label,
            key="academic_bot_toggle",
            help="Open or close Academic Assistant",
            use_container_width=True,
        ):
            st.session_state.academic_bot_open = (
                not st.session_state.academic_bot_open
            )
            st.rerun()

    # Do not render the drawer while it is closed
    if not st.session_state.academic_bot_open:
        return

    # The drawer is fixed to the right edge
    with st.container(key="academic_bot_drawer"):

        # Header
        header_col, close_col = st.columns([5, 1])

        with header_col:
            st.subheader("🎓 Academic Assistant")
            st.caption("Powered by LangGraph + Groq")

        with close_col:
            if st.button(
                "✕",
                key="academic_bot_close",
                help="Close chat",
            ):
                st.session_state.academic_bot_open = False
                st.rerun()

        st.divider()

        # Chat history
        chat_area = st.container(height=440)

        with chat_area:
            if not st.session_state.academic_chat_history:
                st.markdown("### 👋 Hi there!")
                st.write(
                    "I'm your academic assistant. Ask me about "
                    "your enrolled subjects, attendance, or "
                    "general academic questions."
                )

                st.caption("Try asking:")
                st.markdown(
                    "- What is my attendance percentage?\n"
                    "- Which subjects am I enrolled in?\n"
                    "- How can I improve my attendance?"
                )

            for message in st.session_state.academic_chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # Input form. Enter or click Send to submit.
        with st.form(
            "academic_bot_message_form",
            clear_on_submit=True,
            border=False,
        ):
            question = st.text_input(
                "Message",
                placeholder="Ask your academic question...",
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
            st.session_state.academic_chat_history = []
            st.rerun()

        if submitted and question.strip():
            # Save the question before calling the model
            st.session_state.academic_chat_history.append({
                "role": "user",
                "content": question.strip(),
            })

            try:
                with st.spinner("Thinking..."):
                    result = ask_student_assistant(
                        student_id=student_id,
                        question=question.strip(),
                    )

                answer = result.get(
                    "answer",
                    "Sorry, I couldn't generate a response.",
                )

                st.session_state.academic_chat_history.append({
                    "role": "assistant",
                    "content": answer,
                })

            except Exception:
                st.session_state.academic_chat_history.append({
                    "role": "assistant",
                    "content": (
                        "Sorry, I couldn't process your question. "
                        "Please check the Groq API and database "
                        "connection, then try again."
                    ),
                })

            st.rerun()

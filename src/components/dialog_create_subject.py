import streamlit as st
from src.database.db import create_subject


@st.dialog("create new subject")
def create_subject_dialog(teacher_id):
    st.write("Enter the details of new subject")
    sub_id = st.text_input("Subject code", placeholder="CS101")
    sub_name = st.text_input("Subject Name", placeholder="Computer Science")
    sub_section = st.text_input("section", placeholder="A")

    if st.button("Create Subject Now", type='primary', width='stretch'):
        if sub_id and sub_name and sub_section:
            try:
                create_subject(sub_id, sub_name, sub_section, teacher_id)
                st.toast("Subject Created Successfully!")
                st.rerun()

            except Exception as e:
                error_message = str(e).lower()
                if "duplicate" in error_message or "unique" in error_message or "already exists" in error_message:
                    st.error("Subject code is already taken")
                else:
                    st.error(f"Error: {str(e)}")
        else:
            st.warning("Please fill all the fields")
import streamlit as st
from src.components.header import header_home
from src.components.footer import footer_home
from src.ui.base_layout import style_base_layout,style_background_home

def home_screen():

    style_base_layout()
    style_background_home()
    header_home()
    
    
    col1,col2=st.columns(2,gap="large")
    
    with col1:
        st.header("I am Teacher!!")
        if st.button('Teacher Portal',type='primary'):
            st.session_state['login_type']='teacher'
            st.rerun()
    with col2:
        st.header("I am Student!!")
        if st.button('Student Portal',type='primary'):
            st.session_state['login_type']='student'
            st.rerun()
    
    footer_home()
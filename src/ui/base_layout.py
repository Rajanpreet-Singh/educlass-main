import streamlit as st



def style_background_home():

    st.markdown("""
                <style>
        .stApp {
    background: #4F5FE8 !important;
}

.stApp div[data-testid="stColumn"] {
    background-color: #FFFFFF !important;
    padding: 2.5rem !important;
    border-radius: 3rem !important;
}
                """
            ,unsafe_allow_html=True)
    

def style_background_dashboard():

    st.markdown("""
        <style>

                .stApp {
                    background: #E0E3FF !important;
                }

        </style>  

                """
            ,unsafe_allow_html=True)
    

    

def style_base_layout():
# asdasd
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Climate+Crisis:YEAR@1979&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@100..900&display=swap');

                
         /* Hide Top Bar of streamlit */
                
            #MainMenu, footer, header {
                visibility: hidden;
            }
                
            .block-container {
                padding-top:1.5rem !important;    
            }

            h1 {
    font-family: 'Outfit', sans-serif !important;
    font-size: 3.2rem !important;
    font-weight: 800 !important;
    line-height: 1.05 !important;
    margin-bottom: 0rem !important;
    letter-spacing: -1.5px !important;
    transform: scaleX(0.95);
    color: #FFFFFF !important;
}
                

           h2 {
    font-family: 'Outfit', sans-serif !important;
    font-size: 2rem !important;
    font-weight: 800 !important;
    line-height: 1.1 !important;
    margin-bottom: 0.4rem !important;
    letter-spacing: -0.7px !important;
    transform: none !important;
    color: #18234A !important;
}
                
            h3, h4, p {
                font-family: 'Outfit', sans-serif;    
            }
                

            button {
    border-radius: 1.5rem !important;
    background-color: #3548D4 !important;
    color: #FFFFFF !important;
    padding: 10px 20px !important;
    border: none !important;
    transition: transform 0.25s ease-in-out !important;
}

button:hover {
    transform: scale(1.03);
    background-color: #2637B5 !important;
}

            button[kind="secondary"]{
                border-radius: 1.5rem !important;
                background-color: #EB459E !important;
                color: white !important;
                padding: 10px 20px !important;
                border: none !important;
                transition: transform 0.25s ease-in-out !important;
                }

            button[kind="tertiary"]{
                border-radius: 1.5rem !important;
                background-color: black !important;
                color: white !important;
                padding: 10px 20px !important;
                border: none !important;
                transition: transform 0.25s ease-in-out !important;
                }

            
        </style>  

                """
            ,unsafe_allow_html=True)
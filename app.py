import streamlit as st
import os

st.set_page_config(
    page_title="Inteligentny Tutor AI",
    page_icon="🧠",
    layout="centered"
)

# Inicjalizacja stanu sesji
if 'projects' not in st.session_state: st.session_state.projects = {}
if 'selected_project' not in st.session_state: st.session_state.selected_project = None
if 'vectorstore' not in st.session_state: st.session_state.vectorstore = None
if 'quiz_data' not in st.session_state: st.session_state.quiz_data = []
if 'quiz_sources' not in st.session_state: st.session_state.quiz_sources = []
if 'quiz_submitted' not in st.session_state: st.session_state.quiz_submitted = False
if 'user_answers' not in st.session_state: st.session_state.user_answers = {}
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'temperature' not in st.session_state: st.session_state.temperature = 0.7 
if 'score_counted' not in st.session_state: st.session_state.score_counted = False
if 'total_questions_answered' not in st.session_state: st.session_state.total_questions_answered = 0
if 'total_correct_answers' not in st.session_state: st.session_state.total_correct_answers = 0

st.title("🧠 Witaj w Inteligentnym Tutorze AI!")
st.subheader("Twoje osobiste centrum nauki, zasilane przez AI.")
st.markdown("""
Ta aplikacja pozwala Ci tworzyć spersonalizowane moduły do nauki na podstawie własnych dokumentów. 
1.  Przejdź do **"Zarządzaj Projektami"**, aby stworzyć swój pierwszy zestaw materiałów.
2.  Gdy projekt będzie gotowy, przejdź do **"Rozpocznij Naukę"**, aby zacząć sesję z AI.
""")
st.info("Aplikacja korzysta z **Google Gemini** oraz **Hugging Face Hub**.", icon="ℹ️")

if not os.getenv("GOOGLE_API_KEY", st.secrets.get("GOOGLE_API_KEY")):
    st.error("Brak klucza `GOOGLE_API_KEY`. Dodaj go w sekretach swojego Space'a.", icon="🚨")
if not os.getenv("HUGGING_FACE_TOKEN", st.secrets.get("HUGGING_FACE_TOKEN")):
    st.error("Brak klucza `HUGGING_FACE_TOKEN`. Dodaj go w sekretach swojego Space'a (wymagane uprawnienia 'write').", icon="🚨")
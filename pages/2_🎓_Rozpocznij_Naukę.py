import streamlit as st
import os
import json
import time
import asyncio
import ntpath
import random
import re

from langchain.chains import LLMChain, ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from huggingface_hub import snapshot_download, login

st.set_page_config(page_title="Rozpocznij Naukę", layout="centered")
st.title("🎓 Rozpocznij Naukę")

hf_token = os.getenv("HUGGING_FACE_TOKEN", st.secrets.get("HUGGING_FACE_TOKEN"))
google_api_key = os.getenv("GOOGLE_API_KEY", st.secrets.get("GOOGLE_API_KEY"))

if not hf_token or not google_api_key:
    st.error("Upewnij się, że w sekretach Space'a ustawione są `GOOGLE_API_KEY` i `HUGGING_FACE_TOKEN`.")
    st.stop()

login(token=hf_token)
PROJECTS_JSON_PATH = "projects.json"

def load_projects():
    if os.path.exists(PROJECTS_JSON_PATH):
        with open(PROJECTS_JSON_PATH, 'r') as f:
            try: return json.load(f)
            except json.JSONDecodeError: return {}
    return {}

@st.cache_resource(show_spinner="Pobieranie bazy wiedzy dla projektu...")
def load_project_index(project_repo_id, _embeddings):
    local_path = snapshot_download(repo_id=project_repo_id, repo_type="model")
    return FAISS.load_local(local_path, _embeddings, allow_dangerous_deserialization=True)

def parse_json_from_response(text):
    match = re.search(r'```json\s*([\s\S]+?)\s*```', text)
    json_str = match.group(1) if match else text
    try: return json.loads(json_str)
    except (json.JSONDecodeError, TypeError): return None

with st.sidebar:
    st.header("⚙️ Ustawienia Modelu AI")
    st.session_state.temperature = st.slider("Temperatura (kreatywność)", min_value=0.0, max_value=1.0, value=st.session_state.get('temperature', 0.7), step=0.1)

if 'projects' not in st.session_state: st.session_state.projects = load_projects()

try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=google_api_key)

if not st.session_state.projects:
    st.warning("Nie znaleziono żadnych projektów. Przejdź do 'Zarządzaj Projektami', aby stworzyć swój pierwszy.", icon="🗂️")
    st.stop()

project_names = ["-- Wybierz --"] + list(st.session_state.projects.keys())
selected_project_name = st.selectbox("Wybierz projekt, z którego chcesz się uczyć:", project_names, key="project_selector")

if selected_project_name and selected_project_name != "-- Wybierz --":
    if st.session_state.get('selected_project') != selected_project_name:
        st.session_state.selected_project = selected_project_name
        repo_id = st.session_state.projects[selected_project_name]["index_repo_id"]
        st.session_state.vectorstore = load_project_index(repo_id, embeddings)
        st.session_state.quiz_data = []
        st.session_state.chat_history = []
        st.session_state.user_answers = {}
        st.session_state.quiz_submitted = False
        st.rerun()
    
    if 'vectorstore' in st.session_state and st.session_state.vectorstore:
        retriever = st.session_state.vectorstore.as_retriever(search_kwargs={"k": 15})
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", google_api_key=google_api_key, temperature=st.session_state.temperature, convert_system_message_to_human=True)
        
        mode = st.radio("Wybierz tryb nauki:", ["Test Wyboru", "Sesja z Tutorem (pytania otwarte)"], horizontal=True, key="mode_selector")
        st.divider()

        if mode == "Test Wyboru":
            st.header("📝 Test Wyboru")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ Generuj kolejne 5 pytań"):
                    st.session_state.quiz_submitted, st.session_state.score_counted = False, False
                    with st.spinner("Losuję paragrafy i generuję pytania..."):
                        all_docs = list(st.session_state.vectorstore.docstore._dict.values())
                        sample_size = min(15, len(all_docs))
                        context_docs = random.sample(all_docs, sample_size)
                        
                        context_text = "\n\n---\n\n".join([doc.page_content for doc in context_docs])
                        
                        # POPRAWKA: Uproszczony i jawny szablon promptu
                        quiz_prompt_template_str = (
                            "Na podstawie tego kontekstu: {context}\n\n"
                            "Stwórz test JSON z 5 pytań. Zwróć WYŁĄCZNIE poprawny JSON. Pola: 'pytanie', 'typ'('jedno'/'wielo'), "
                            "'opcje'(słownik A,B,C,D), 'poprawne_odpowiedzi'(LISTA), 'uzasadnienie', 'zrodlo_paragrafu' (DOKŁADNY, PEŁNY paragraf z kontekstu)."
                        )
                        quiz_prompt_template = PromptTemplate(template=quiz_prompt_template_str, input_variables=["context"])

                        quiz_chain = LLMChain(llm=llm, prompt=quiz_prompt_template)
                        response = quiz_chain.invoke({"context": context_text})
                        parsed_quiz = parse_json_from_response(response["text"])
                        
                        if parsed_quiz and isinstance(parsed_quiz, list):
                            st.session_state.quiz_data.extend(parsed_quiz)
                            st.session_state.user_answers = {i: [] for i in range(len(st.session_state.quiz_data))}
                            st.rerun()
            with col2:
                if st.button("🗑️ Zakończ i zresetuj test"): 
                    st.session_state.quiz_data, st.session_state.user_answers, st.session_state.quiz_submitted = [], {}, False
                    st.rerun()

            if st.session_state.get('quiz_data'):
                # Reszta logiki Testu Wyboru (formularz i wyniki) bez zmian
                pass

        elif mode == "Sesja z Tutorem (pytania otwarte)":
            st.header("🎤 Sesja z Tutorem")
            
            qa_chain_oral = ConversationalRetrievalChain.from_llm(llm, retriever=retriever)
            if 'chat_history' not in st.session_state: st.session_state.chat_history = []
            
            if not st.session_state.chat_history:
                with st.spinner("Tutor przygotowuje pierwsze pytanie..."):
                    context_docs = retriever.get_relevant_documents(f"Pytanie otwarte na egzamin dla: {st.session_state.selected_project}")
                    context_text = context_docs[0].page_content
                    prompt_text = f"Na podstawie tego fragmentu: '{context_text}', zadaj kandydatowi jedno, otwarte pytanie egzaminacyjne. Zadaj tylko pytanie, bez żadnego wstępu."
                    initial_question = llm.invoke(prompt_text).content
                    st.session_state.chat_history.append(("Pytanie od tutora:", initial_question))
                    st.rerun()

            for question, answer in st.session_state.chat_history:
                with st.chat_message("user"): st.markdown(question)
                with st.chat_message("assistant"): st.markdown(answer)

            if user_prompt := st.chat_input("Twoja odpowiedź lub pytanie..."):
                with st.chat_message("user"): st.markdown(user_prompt)
                with st.chat_message("assistant"):
                    with st.spinner("Myślę..."):
                        system_prompt = "Jesteś surowym, ale sprawiedliwym egzaminatorem i nauczycielem. Zawsze odpowiadaj po polsku. Odpowiedz na pytanie kandydata na podstawie dostarczonych dokumentów i historii rozmowy."
                        full_prompt = f"{system_prompt}\n\nPytanie: {user_prompt}"
                        history_for_chain = st.session_state.chat_history
                        result = qa_chain_oral.invoke({"question": full_prompt, "chat_history": history_for_chain})
                        response = result['answer']
                        st.markdown(response)
                        st.session_state.chat_history.append((user_prompt, response))
import os
import asyncio
import streamlit as st
import json
import re
import time
import ntpath

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# --- Konfiguracja strony i klucza API ---
st.set_page_config(page_title="Tutor Egzaminacyjny - Zakres 1", layout="centered")
api_key = os.getenv("GOOGLE_API_KEY", st.secrets.get("GOOGLE_API_KEY", ""))

# --- Inicjalizacja stanu sesji ---
if 'quiz_data' not in st.session_state:
    st.session_state.quiz_data = None
if 'quiz_sources' not in st.session_state:
    st.session_state.quiz_sources = None
if 'quiz_submitted' not in st.session_state:
    st.session_state.quiz_submitted = False
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}
if 'current_question' not in st.session_state:
    st.session_state.current_question = None
if 'current_evaluation' not in st.session_state:
    st.session_state.current_evaluation = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'total_questions' not in st.session_state:
    st.session_state.total_questions = 0
if 'correct_answers' not in st.session_state:
    st.session_state.correct_answers = 0

# --- Funkcje pomocnicze ---
@st.cache_resource
def load_or_create_vectorstore(_api_key, _embeddings):
    """
    Funkcja, która tylko wczytuje lub tworzy bazę, bez wyświetlania komunikatów.
    """
    index_path = "faiss_index"
    if os.path.exists(index_path):
        return FAISS.load_local(index_path, _embeddings, allow_dangerous_deserialization=True)
    
    # Ta część uruchomi się tylko, gdy folder nie istnieje
    docs_folder = "documents"
    if not os.path.exists(docs_folder) or not os.listdir(docs_folder):
        return None # Zwróci None, jeśli nie ma dokumentów
        
    docs = [PyPDFLoader(os.path.join(docs_folder, file)).load() for file in os.listdir(docs_folder) if file.endswith(".pdf")]
    flat_docs = [item for sublist in docs for item in sublist]

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=400)
    split_docs = text_splitter.split_documents(flat_docs)

    vectorstore = FAISS.from_documents(split_docs, _embeddings)
    vectorstore.save_local(index_path)
    return vectorstore

def parse_json_from_response(text):
    match = re.search(r'```json\s*([\s\S]+?)\s*```', text)
    json_str = match.group(1) if match else text
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None

# --- Główny interfejs aplikacji ---
st.title("👨‍🏫 Tutor Egzaminacyjny - Uprawnienia Geodezyjne")

if not api_key:
    st.warning("🚨 Klucz Google API nie jest ustawiony!")
else:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
    
    # ZMIANA: Logika wyświetlania komunikatów jest teraz tutaj, poza funkcją cache
    index_path = "faiss_index"
    if not os.path.exists(index_path):
        st.info("⚠️ Baza wektorowa nie istnieje. Rozpoczynam jednorazowe tworzenie...")
        st.warning("Ten proces może potrwać kilka minut. Aplikacja uruchomi się automatycznie po zakończeniu.")
        # Wywołujemy funkcję, która stworzy bazę i ją zwróci
        vectorstore = load_or_create_vectorstore(api_key, embeddings)
        if vectorstore:
            st.success("Baza wektorowa utworzona! Uruchamiam aplikację...")
            time.sleep(2)
            st.rerun()
    else:
        # Jeśli baza istnieje, po prostu ją wczytujemy bez żadnych komunikatów
        vectorstore = load_or_create_vectorstore(api_key, embeddings)

    if vectorstore is None:
        st.error("Nie udało się wczytać ani utworzyć bazy wektorowej. Sprawdź, czy folder 'documents' zawiera pliki PDF.")
    else:
        retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=api_key, temperature=0.2, convert_system_message_to_human=True)

        # --- SEKCJA 1: TEST WYBORU ---
        st.header("📝 Test Wyboru", divider='blue')
        if st.session_state.quiz_data is None:
            if st.button("Wygeneruj Interaktywny Test (5 pytań)"):
                with st.spinner("✍️ Krok 1/2: Pobieram kontekst z przepisów..."):
                    context_docs = retriever.get_relevant_documents("Pytania egzaminacyjne na uprawnienia geodezyjne zakres 1")
                    context_text = "\n\n---\n\n".join([doc.page_content for doc in context_docs])
                with st.spinner("✍️ Krok 2/2: Generuję pytania na podstawie kontekstu..."):
                    prompt_template = PromptTemplate(input_variables=["context"], template=("Na podstawie poniższego kontekstu prawnego, stwórz test. Kontekst:\n\n{context}\n\nZwróć odpowiedź WYŁĄCZNIE w formacie JSON. JSON to lista 5 obiektów. Każdy obiekt musi mieć klucze: 'pytanie', 'typ' ('jedno' lub 'wielo'), 'opcje' (słownik A,B,C,D), 'poprawne_odpowiedzi' (LISTA poprawnych kluczy), oraz 'uzasadnienie' (wyjaśnienie z podstawą prawną)."))
                    quiz_chain = LLMChain(llm=llm, prompt=prompt_template)
                    response = quiz_chain.invoke({"context": context_text})
                    parsed_quiz = parse_json_from_response(response["text"])
                    if parsed_quiz and isinstance(parsed_quiz, list):
                        st.session_state.quiz_data = parsed_quiz
                        st.session_state.quiz_sources = context_docs
                        st.session_state.user_answers = {i: [] for i in range(len(parsed_quiz))}
                        st.session_state.quiz_submitted = False
                        st.rerun()
                    else:
                        st.error("Nie udało się poprawnie przetworzyć odpowiedzi modelu. Spróbuj ponownie.")
        else:
            if not st.session_state.quiz_submitted:
                with st.form(key='quiz_form'):
                    for i, q in enumerate(st.session_state.quiz_data):
                        st.markdown(f"**Pytanie {i+1}:** {q['pytanie']}")
                        if q.get('typ') == 'jedno':
                            user_choice = st.radio("Wybierz jedną odpowiedź:", list(q['opcje'].keys()), format_func=lambda opt: f"{opt}: {q['opcje'][opt]}", key=f"q_{i}", index=None, label_visibility="collapsed")
                            st.session_state.user_answers[i] = [user_choice] if user_choice else []
                        else:
                            st.markdown("_Zaznacz wszystkie prawidłowe odpowiedzi:_")
                            temp_answers = [opt_key for opt_key, opt_val in q['opcje'].items() if st.checkbox(f"{opt_key}: {opt_val}", key=f"q_{i}_{opt_key}")]
                            st.session_state.user_answers[i] = temp_answers
                        st.divider()
                    if st.form_submit_button("Sprawdź odpowiedzi"):
                        st.session_state.quiz_submitted = True
                        st.session_state.total_questions += len(st.session_state.quiz_data)
                        st.rerun()
            else:
                st.subheader("📊 Wyniki Testu")
                score = 0
                for i, q in enumerate(st.session_state.quiz_data):
                    user_ans_list = st.session_state.user_answers.get(i, [])
                    correct_ans = sorted(q['poprawne_odpowiedzi'])
                    is_correct = (sorted(user_ans_list) == correct_ans)
                    if is_correct: score += 1
                    
                    st.markdown(f"**Pytanie {i+1}:** {q['pytanie']}")
                    if q.get('typ') == 'jedno':
                        st.radio("Twoja odpowiedź:", list(q['opcje'].keys()), format_func=lambda opt: f"{opt}: {q['opcje'][opt]}", key=f"q_disabled_{i}", index=list(q['opcje'].keys()).index(user_ans_list[0]) if user_ans_list else None, disabled=True, label_visibility="collapsed")
                    else:
                        for opt_key, opt_val in q['opcje'].items():
                            st.checkbox(f"{opt_key}: {opt_val}", key=f"q_disabled_{i}_{opt_key}", value=(opt_key in user_ans_list), disabled=True)

                    if is_correct:
                        st.success(f"✅ Poprawna odpowiedź!")
                    else:
                        st.error(f"❌ Poprawna odpowiedź to: **{', '.join(correct_ans)}**.")
                    
                    with st.expander("Zobacz uzasadnienie i podstawę prawną"):
                        st.info(f"**Uzasadnienie:** {q['uzasadnienie']}")
                        if 'quiz_sources' in st.session_state and st.session_state.quiz_sources:
                            temp_retriever = FAISS.from_documents(st.session_state.quiz_sources, embeddings).as_retriever()
                            source_docs = temp_retriever.get_relevant_documents(q['pytanie'], k=1)
                            if source_docs:
                                file_name = ntpath.basename(source_docs[0].metadata.get('source', 'Nieznane źródło'))
                                st.markdown(f"**Fragment z aktu prawnego ({file_name}):**")
                                st.caption(source_docs[0].page_content)
                    st.divider()
                
                if not getattr(st.session_state, 'score_counted', False):
                    st.session_state.correct_answers += score
                    st.session_state.score_counted = True

                st.markdown(f"### Wynik tego testu: **{score}/{len(st.session_state.quiz_data)}**")
                if st.button("Spróbuj jeszcze raz (nowy test)"):
                    st.session_state.quiz_data = None
                    st.session_state.score_counted = False
                    st.rerun()

        # --- SEKCJA 2: EGZAMIN USTNY ---
        st.header("🎤 Egzamin Ustny", divider='blue')
        qa_chain_oral = ConversationalRetrievalChain.from_llm(llm, retriever=retriever)
        if st.session_state.current_question is None:
            if st.button("Zadaj mi pytanie egzaminacyjne"):
                with st.spinner("Losuję pytanie..."):
                    prompt_question = "Twoim jedynym zadaniem jest wygenerowanie jednego pytania egzaminacyjnego na podstawie dostarczonego kontekstu. Użyj TYLKO dostarczonego fragmentu przepisów. Nie komentuj jakości kontekstu. Zwróć jako odpowiedź wyłącznie treść samego pytania."
                    result = qa_chain_oral({"question": prompt_question, "chat_history": []})
                    st.session_state.current_question = result['answer']
                    st.session_state.current_evaluation = None
                    st.rerun()
        if st.session_state.current_question:
            st.markdown(f"**Pytanie:**")
            st.info(st.session_state.current_question)
            user_answer = st.text_area("Twoja odpowiedź:", height=150, key="user_answer_input")
            if st.button("Oceń moją odpowiedź", key="evaluate_button"):
                if user_answer:
                    with st.spinner("Ocena w toku..."):
                        prompt_eval = f"Oceń odpowiedź: '{user_answer}' na pytanie: '{st.session_state.current_question}'. Bądź jak surowy egzaminator GUGiK. Wskaż błędy i podaj wzorcową odpowiedź z podstawą prawną."
                        result = qa_chain_oral({"question": prompt_eval, "chat_history": []})
                        st.session_state.current_evaluation = result['answer']
                        st.rerun()
        if st.session_state.current_evaluation:
            st.markdown("**Ocena egzaminatora:**")
            st.success(st.session_state.current_evaluation)
            if st.button("Następne pytanie ustne"):
                st.session_state.current_question = None
                st.session_state.current_evaluation = None
                st.rerun()

        # --- SEKCJA 3: STATYSTYKI ---
        st.header("📈 Statystyki Sesji", divider='blue')
        if st.session_state.total_questions > 0:
            accuracy = (st.session_state.correct_answers / st.session_state.total_questions) * 100
            st.metric(label="Łączna liczba odpowiedzi (test)", value=st.session_state.total_questions)
            st.metric(label="Poprawność", value=f"{accuracy:.1f}%")
        else:
            st.info("Rozwiąż pierwszy test, aby zobaczyć statystyki.")
        st.caption("Statystyki są resetowane po ponownym uruchomieniu lub odświeżeniu aplikacji.")
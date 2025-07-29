import streamlit as st
import os
import json
import time
import re
import asyncio
from langchain_core.documents import Document
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from huggingface_hub import HfApi, create_repo, login

st.set_page_config(page_title="Zarządzaj Projektami", layout="centered")
st.title("🗂️ Zarządzaj Projektami Nauki")

hf_token = os.getenv("HUGGING_FACE_TOKEN", st.secrets.get("HUGGING_FACE_TOKEN"))
google_api_key = os.getenv("GOOGLE_API_KEY", st.secrets.get("GOOGLE_API_KEY"))

if not hf_token or not google_api_key:
    st.error("Upewnij się, że w sekretach Space'a ustawione są `GOOGLE_API_KEY` i `HUGGING_FACE_TOKEN`.")
    st.stop()

login(token=hf_token)
api = HfApi()
hf_user = api.whoami()['name']
SPACE_REPO_ID = os.getenv("SPACE_ID", st.secrets.get("SPACE_ID"))
PROJECTS_JSON_PATH = "projects.json"

def sanitize_name(name):
    name = name.lower()
    name = re.sub(r'[ąćęłńóśźż]', lambda m: {'ą':'a','ć':'c','ę':'e','ł':'l','ń':'n','ó':'o','ś':'s','ź':'z','ż':'z'}[m.group(0)], name)
    name = re.sub(r'\s+', '-', name)
    name = re.sub(r'[^a-z0-9\-]', '', name)
    return name

def load_projects():
    if os.path.exists(PROJECTS_JSON_PATH):
        with open(PROJECTS_JSON_PATH, 'r') as f:
            try: return json.load(f)
            except json.JSONDecodeError: return {}
    return {}

def save_projects(projects):
    with open(PROJECTS_JSON_PATH, 'w') as f: json.dump(projects, f, indent=4)
    if SPACE_REPO_ID:
        try: api.upload_file(path_or_fileobj=PROJECTS_JSON_PATH, path_in_repo="projects.json", repo_id=SPACE_REPO_ID, repo_type="space")
        except Exception as e: st.warning(f"Nie udało się zsynchronizować pliku projects.json: {e}")

def clean_text(text):
    text = re.sub(r's\. \d+/\d+', '', text); text = re.sub(r'©Kancelaria Sejmu', '', text)
    text = re.sub(r'Dz\.U\. .*', '', text); text = re.sub(r'\b\w\b', '', text)
    text = re.sub(r' +', ' ', text); text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

st.session_state.projects = load_projects()

st.header("Istniejące Projekty")
if not st.session_state.projects: st.info("Nie stworzyłeś jeszcze żadnego projektu.")
else:
    for project_name, data in st.session_state.projects.items():
        with st.container(border=True):
            st.subheader(project_name)
            st.caption(f"Repozytorium indeksu: `{data.get('index_repo_id', 'Brak info')}`")
            if st.button("🗑️ Usuń", key=f"del_{project_name}"):
                with st.spinner(f"Usuwanie projektu {project_name}..."):
                    try:
                        api.delete_repo(repo_id=data.get("index_repo_id"), repo_type="model")
                        api.delete_repo(repo_id=data.get("dataset_repo_id"), repo_type="dataset")
                        del st.session_state.projects[project_name]
                        save_projects(st.session_state.projects)
                        st.success(f"Projekt {project_name} został usunięty."); st.rerun()
                    except Exception as e: st.error(f"Nie udało się usunąć repozytoriów: {e}")
st.divider()

st.header("Stwórz Nowy Projekt")
with st.form("new_project_form"):
    project_name = st.text_input("Nazwa Projektu*", placeholder="np. Uprawnienia Geodezyjne Zakres 1")
    core_files = st.file_uploader("1. Wgraj pliki z Wiedzą Rdzenną*", type=['pdf', 'txt'], accept_multiple_files=True)
    test_files = st.file_uploader("2. Wgraj Przykładowe Testy", type=['pdf', 'txt'], accept_multiple_files=True)
    instructions_file = st.file_uploader("3. (Opcjonalnie) Wgraj plik z Instrukcjiami dla AI", type=['txt'])
    submitted = st.form_submit_button("Przetwórz i Zapisz Projekt")

    if submitted:
        sanitized_project_name = sanitize_name(project_name)
        if not project_name: st.error("Nazwa projektu jest wymagana.")
        elif not core_files: st.error("Musisz wgrać co najmniej jeden plik z Wiedzą Rdzenną.")
        elif project_name in st.session_state.projects: st.error("Projekt o tej nazwie już istnieje.")
        else:
            with st.spinner("Rozpoczynam przetwarzanie projektu..."):
                try:
                    st.write("Krok 1/4: Tworzenie repozytoriów na Hugging Face Hub...")
                    dataset_repo_id = f"{hf_user}/{sanitized_project_name}-pdfs"
                    index_repo_id = f"{hf_user}/{sanitized_project_name}-index"
                    create_repo(repo_id=dataset_repo_id, repo_type="dataset", private=True, exist_ok=True)
                    create_repo(repo_id=index_repo_id, repo_type="model", private=True, exist_ok=True)
                    
                    temp_dir = f"temp_{sanitized_project_name}"
                    os.makedirs(temp_dir, exist_ok=True)
                    all_uploaded_files = { "core": core_files, "tests": test_files, "instructions": [instructions_file] if instructions_file else [] }
                    for _, files in all_uploaded_files.items():
                         for f in files:
                            with open(os.path.join(temp_dir, f.name), "wb") as out_f: out_f.write(f.getvalue())
                    api.upload_folder(folder_path=temp_dir, repo_id=dataset_repo_id, repo_type="dataset")
                    
                    st.write("Krok 2/4: Wczytywanie i czyszczenie dokumentów...")
                    all_paragraphs = []
                    for f in core_files:
                        path = os.path.join(temp_dir, f.name)
                        loader = PyMuPDFLoader(path) if f.name.endswith(".pdf") else TextLoader(path)
                        full_text = " ".join([doc.page_content for doc in loader.load()])
                        cleaned_text = clean_text(full_text)
                        paragraphs = re.split(r'(?=\n(?:Art\.|§)\s*\d+\.|\n\d+\)\s|\n\d+\.\s)', cleaned_text)
                        for para in paragraphs:
                            if len(para.strip()) > 100: all_paragraphs.append(Document(page_content=para.strip(), metadata={"source": f.name}))
                    if not all_paragraphs: st.error("Nie udało się wyodrębnić treści z plików."); st.stop()

                    st.write("Krok 3/4: Tworzenie indeksu wektorowego (embeddingów)...")
                    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=google_api_key)
                    vectorstore = FAISS.from_documents(all_paragraphs, embeddings)
                    index_path = f"temp_faiss_{sanitized_project_name}"
                    vectorstore.save_local(index_path)

                    st.write("Krok 4/4: Zapisywanie gotowego indeksu...")
                    api.upload_folder(folder_path=index_path, repo_id=index_repo_id, repo_type="model")

                    st.session_state.projects[project_name] = {"index_repo_id": index_repo_id, "dataset_repo_id": dataset_repo_id}
                    save_projects(st.session_state.projects)
                    st.success(f"Projekt '{project_name}' został pomyślnie przetworzony!"); st.balloons()
                except Exception as e:
                    st.error(f"Wystąpił błąd: {e}")
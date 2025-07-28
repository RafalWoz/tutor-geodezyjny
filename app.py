import os
import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.document_loaders import PyPDFLoader

# --- Ładowanie dokumentów ---
def load_documents(folder="documents"):
    docs = []
    for file in os.listdir(folder):
        if file.endswith(".pdf"):
            loader = PyPDFLoader(os.path.join(folder, file))
            docs.extend(loader.load())
    return docs

# --- Tworzenie bazy embeddingów ---
@st.cache_resource
def create_vectorstore():
    docs = load_documents()
    embeddings = OpenAIEmbeddings(openai_api_key=os.environ["OPENAI_API_KEY"])
    return FAISS.from_documents(docs, embeddings)

st.title("🗺️ Tutor do Uprawnień Geodezyjnych")
vectorstore = create_vectorstore()
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
llm = ChatOpenAI(openai_api_key=os.environ["OPENAI_API_KEY"], model_name="gpt-4o")
qa_chain = ConversationalRetrievalChain.from_llm(llm, retriever=retriever)

# --- UI ---
chat_history = []
query = st.text_input("❓ Zadaj pytanie lub poproś o quiz:")
if query:
    result = qa_chain({"question": query, "chat_history": chat_history})
    st.write(result["answer"])
    chat_history.append((query, result["answer"]))

if st.button("🎯 Wygeneruj quiz z bieżącego prawa"):
    result = qa_chain({"question": "Stwórz 5 pytań testowych wielokrotnego wyboru na podstawie przepisów.", "chat_history": chat_history})
    st.write(result["answer"])

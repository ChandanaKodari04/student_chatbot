import streamlit as st
import pandas as pd
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Custom CSS for styling
st.markdown("""
<style>
    .stApp {
        background: #f8f5e6;
        background-image: radial-gradient(#d4d0c4 1px, transparent 1px);
        background-size: 20px 20px;
    }
    .chat-font {
        font-family: 'Times New Roman', serif;
        color: #2c5f2d;
    }
    .user-msg {
        background: #ffffff !important;
        border-radius: 15px !important;
        border: 2px solid #2c5f2d !important;
    }
    .bot-msg {
        background: #fff9e6 !important;
        border-radius: 15px !important;
        border: 2px solid #ffd700 !important;
    }
    .stChatInput {
        background: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

# Configure Google Gemini
genai.configure(api_key="AIzaSyC1sJ_aHUIsdVumIhkYE5pCTlecWewwhXc")  # Replace with your Gemini API key
gemini = genai.GenerativeModel('gemini-1.5-flash')

# Initialize models
embedder = SentenceTransformer('all-MiniLM-L6-v2')  # Embedding model

# Load data and create FAISS index
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('carier_dataset.csv')  # Replace with your dataset file name
        if 'question' not in df.columns or 'answer' not in df.columns:
            st.error("The CSV file must contain 'category' and 'information' columns.")
            st.stop()
        df['context'] = df.apply(
            lambda row: f"Question: {row['category']}\nAnswer: {row['information']}", 
            axis=1
        )
        embeddings = embedder.encode(df['context'].tolist())
        index = faiss.IndexFlatL2(embeddings.shape[1])  # FAISS index for similarity search
        index.add(np.array(embeddings).astype('float32'))
        return df, index
    except Exception as e:
        st.error(f"Failed to load data. Error: {e}")
        st.stop()

# Load dataset and FAISS index
df, faiss_index = load_data()

# App Header
st.markdown('<h1 class="chat-font">🤖 Career Guidance Chabot</h1>', unsafe_allow_html=True)
st.markdown('<h3 class="chat-font">Ask me anything, and I\'ll respond as career guidance!</h3>', unsafe_allow_html=True)
st.markdown("---")

# Function to find the closest matching question using FAISS
def find_closest_category(query, faiss_index, df):
    query_embedding = embedder.encode([query])
    _, I = faiss_index.search(query_embedding.astype('float32'), k=1)  # Top 1 match
    if I.size > 0:
        return df.iloc[I[0][0]]['information']  # Return the closest answer
    return None

# Function to generate a refined answer using Gemini
def generate_refined_information(query, retrieved_information):
    prompt = f""" Respond to the following question in a friendly and conversational tone:
    Question: {query}
    Retrieved Answer: {retrieved_information}
    - Provide a detailed and accurate response.
    - Ensure the response is grammatically correct and engaging.
    """
    response = gemini.generate_content(prompt)
    return response.text

# Chat Interface
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"], 
                        avatar="🙋" if message["role"] == "user" else "🤖"):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask me anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.spinner("Thinking..."):
        try:
            # Find the closest answer
            retrieved_information = find_closest_category(prompt, faiss_index, df)
            if retrieved_information:
                # Generate a refined answer using Gemini
                refined_information = generate_refined_information(prompt, retrieved_information)
                response = f"*Career Chatbot*:\n{refined_information}"
            else:
                response = "*Career Chatbot*:\nI'm sorry, I cannot answer that question."
        except Exception as e:
            response = f"An error occurred: {e}"
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

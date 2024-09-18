from langchain_huggingface import HuggingFaceEmbeddings

def get_embedding_function():
    embeddings = HuggingFaceEmbeddings()
    return embeddings
import argparse
from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_community.llms.ollama import Ollama
from dotenv import load_dotenv
from embedding import get_embedding_function
from langchain_groq import ChatGroq

# TODO !BAD
import warnings
warnings.filterwarnings("ignore")

load_dotenv()

CHROMA_PATH = "chroma"

# PROMPT_TEMPLATE = """
# Answer the question based only on the following context:

# {context}

# ---

# Answer the question based on the above context: {question}
# """
PROMPT_TEMPLATE = """
Given the following context, answer the question concisely:

Context: {context}

Question: {question}

Provide only the most relevant information from the context without any additional details or introductions.
"""


def main():
    # Create CLI.
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text
    query_rag(query_text)


def query_rag(query_text: str):
    # Prepare the DB.
    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

    # Search the DB.
    results = db.similarity_search_with_score(query_text, k=5)

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)
    # print(prompt)

    

    model = ChatGroq(model="llama3-8b-8192")
    # model = Ollama(model="mistral")
    response_text = model.invoke(prompt)

    sources = [doc.metadata.get("id", None) for doc, _score in results]
    formatted_response = f"Response: {response_text.content}\nSources: {sources}"
    print(formatted_response)
    return response_text


if __name__ == "__main__":
    main()
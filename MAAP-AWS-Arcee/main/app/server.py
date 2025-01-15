import json
import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from langserve import add_routes
from app.mongodb_atlas_retriever_tools import MongoDBAtlasCustomRetriever
from app.sagemaker_llm import SageMakerLLM

load_dotenv()

# Set the environment variables
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.supernova.arcee.ai/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SAGEMAKER_ENDPOINT_NAME = os.getenv("SAGEMAKER_ENDPOINT_NAME")
AWS_REGION = os.getenv("AWS_REGION")

app = FastAPI(
    title="MAAP - MongoDB AI Applications Program",
    version="1.0",
    description="MongoDB AI Applications Program",
)


@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")


if SAGEMAKER_ENDPOINT_NAME:
    llm = SageMakerLLM(endpoint_name=SAGEMAKER_ENDPOINT_NAME, region_name=AWS_REGION)
else:
    llm = ChatOpenAI(
        model="arcee_pipeline.Arcee-SuperNova-v1",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        streaming=True,
    )


prompt_template = """Use the following pieces of context to answer the question at the end.
Tell you are Arcee SuperNova. 
Context:
{context}

Question: {question}
Answer:"""


prompt = ChatPromptTemplate.from_template(prompt_template)


def format_documents(documents):
    return [doc.page_content for doc in documents if doc.page_content is not None]


def format_query(rpt):
    input = json.loads(rpt)
    return input["query"]


chain = (
    {
        "context": MongoDBAtlasCustomRetriever()| format_documents | "\n".join,
        "question": RunnablePassthrough() | format_query,
    }
    | prompt
    | llm
)
add_routes(app, chain, path="/rag", playground_type="default")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

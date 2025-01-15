import json
import logging
import os
from typing import List

import boto3
import pymongo
from langchain.retrievers.merger_retriever import MergerRetriever
from langchain_aws import BedrockEmbeddings
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_mongodb import MongoDBAtlasVectorSearch
from pymongo.collection import Collection


# Setup AWS and Bedrock client
def get_bedrock_client():
    return boto3.client("bedrock-runtime", region_name="us-east-1")


def create_embeddings(client):
    return BedrockEmbeddings(model_id="amazon.titan-embed-text-v1", client=client)


# Initialize everything
bedrock_client = get_bedrock_client()
bedrock_embeddings = create_embeddings(bedrock_client)


class MongoDBAtlasCustomRetriever(BaseRetriever):
    @property
    def collection(self) -> Collection:
        return self.vectorstore._collection

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        """Retrieve documents that are highest scoring / most similar to query."""
        MONGODB_URI = os.getenv("MONGODB_URI")
        # Initialize everything
        bedrock_client = get_bedrock_client()
        bedrock_embeddings = create_embeddings(bedrock_client)
        # Connect to the MongoDB database
        mongoDBClient = pymongo.MongoClient(host=MONGODB_URI)
        logging.info("Connected to MongoDB...")

        database = mongoDBClient["travel_agency"]
        collection = database["trip_recommendation"]

        vector_store = MongoDBAtlasVectorSearch(
            text_key="About Place",
            embedding_key="details_embedding",
            index_name="vector_index",
            embedding=bedrock_embeddings,
            collection=collection,
        )

        database_doc = mongoDBClient["maap_data_loader"]
        collection_doc = database_doc["document"]
        vector_store_documents = MongoDBAtlasVectorSearch(
            text_key="document_text",
            embedding_key="document_embedding",
            index_name="document_vector_index",
            embedding=bedrock_embeddings,
            collection=collection_doc,
        )

        retriever_travels = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"score_threshold": 0.9, "k": 10},
        )

        retriever_user_docs = vector_store_documents.as_retriever(
            search_type="similarity",
            search_kwargs={"score_threshold": 0.9, "k": 10},
        )

        inputs = json.loads(query)
        if len(inputs["userId"]) > 0:
            retriever_user_docs = vector_store_documents.as_retriever(
                search_type="similarity",
                search_kwargs={
                    "score_threshold": 0.9,
                    "k": 10,
                    "pre_filter": {"userId": inputs["userId"]},
                },
            )

        retrievers = None
        if (
            len(inputs["dataSource"]) > 0
        ):  # ["Trip Recommendations", "User Uploaded Data"]
            if len(inputs["dataSource"]) == 1:
                if inputs["dataSource"][0] == "Trip Recommendations":
                    retrievers = retriever_travels
                else:
                    retrievers = retriever_user_docs
            elif len(inputs["dataSource"]) > 1:
                retrievers = MergerRetriever(
                    retrievers=[retriever_user_docs, retriever_travels]
                )
        else:
            return ""

        documents = retrievers.invoke(inputs["query"])

        return documents

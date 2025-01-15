"""
AWS SageMaker LLM Wrapper for LangChain
Author: Mohammad Daoud Farooqi

This module provides a custom wrapper for integrating AWS SageMaker-hosted language models with LangChain's 
LLM framework. It supports both synchronous and streaming responses for flexible usage.

Classes:
    - SageMakerLLM: Represents the custom wrapper for a SageMaker endpoint.

Dependencies:
    - boto3: AWS SDK for Python to interact with SageMaker.
    - langchain_core: Core LangChain components.
    - pydantic: Data validation and management.

Example:
    >>> endpoint_name = "example-endpoint"
    >>> llm = SageMakerLLM(endpoint_name=endpoint_name)
    >>> response = llm.invoke("Tell me a joke.")
    >>> print(response)
"""
import json
import boto3
from typing import Any, Dict, Iterator, List, Optional
from pydantic import PrivateAttr
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.outputs import GenerationChunk


class SageMakerLLM(LLM):
    """
    A custom LLM wrapper for AWS SageMaker endpoints, compatible with LangChain.

    This class provides methods to interact with SageMaker-hosted language models, enabling both synchronous
    and streaming responses. It leverages the boto3 client for communication with SageMaker and ensures 
    compatibility with LangChain's LLM abstractions.

    Attributes:
        endpoint_name (str): Name of the SageMaker endpoint.
        region_name (str): AWS region where the SageMaker endpoint is deployed (default: "us-east-1").
        content_type (str): Content type for the payload sent to the SageMaker endpoint (default: "application/json").
    """

    endpoint_name: str
    """Name of the SageMaker endpoint."""

    region_name: str = "us-east-1"
    """AWS region where the SageMaker endpoint is deployed."""

    content_type: str = "application/json"
    """Content type for the payload sent to the SageMaker endpoint."""

    _sagemaker_runtime: boto3.client = PrivateAttr()
    """Private attribute to hold the SageMaker runtime client."""

    def __init__(self, **data: Any):
        """
        Initialize the SageMakerLLM instance.

        Args:
            **data: Arbitrary keyword arguments for initialization.
        """
        super().__init__(**data)
        self._sagemaker_runtime = boto3.client(
            "sagemaker-runtime", region_name=self.region_name
        )

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        Handle synchronous interaction with the SageMaker endpoint.

        Args:
            prompt (str): Input prompt for the language model.
            stop (Optional[List[str]]): List of stop words for text generation.
            run_manager (Optional[CallbackManagerForLLMRun]): Callback manager for tracking runs.

        Returns:
            str: The model's response as a string.
        """
        input_data = {
            "messages": [
                {"role": "system", "content": "You are a friendly and helpful AI assistant."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1024,
            "temperature": 0.7,
            "top_p": 0.9,
            "stop": ["<|endoftext|>", "</s>"],
        }
        payload = json.dumps(input_data)

        response = self._sagemaker_runtime.invoke_endpoint(
            EndpointName=self.endpoint_name,
            ContentType=self.content_type,
            Body=payload,
        )
        result = json.loads(response["Body"].read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]

    def _stream(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[GenerationChunk]:
        """
        Handle streaming interaction with the SageMaker endpoint.

        Args:
            prompt (str): Input prompt for the language model.
            stop (Optional[List[str]]): List of stop words for text generation.
            run_manager (Optional[CallbackManagerForLLMRun]): Callback manager for tracking runs.

        Yields:
            GenerationChunk: An object representing chunks of the response.
        """
        input_data = {
            "messages": [
                {"role": "system", "content": "You are a friendly and helpful AI assistant."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1024,
            "temperature": 0.7,
            "top_p": 0.9,
            "stop": ["<|endoftext|>", "</s>"],
        }
        payload = json.dumps(input_data)

        response = self._sagemaker_runtime.invoke_endpoint_with_response_stream(
            EndpointName=self.endpoint_name,
            ContentType=self.content_type,
            Body=payload,
            Accept="application/jsonlines",
        )

        try:
            for event in response["Body"]:
                if "PayloadPart" in event:
                    chunk_text = event["PayloadPart"]["Bytes"].decode("utf-8").strip()
                    if chunk_text:
                        chunk = GenerationChunk(text=chunk_text)
                        if run_manager:
                            run_manager.on_llm_new_token(chunk.text, chunk=chunk)
                        yield chunk
        finally:
            response["Body"].close()

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """
        Retrieve identifying parameters of the LLM.

        Returns:
            Dict[str, Any]: A dictionary of key parameters.
        """
        return {
            "endpoint_name": self.endpoint_name,
            "region_name": self.region_name,
            "content_type": self.content_type,
        }

    @property
    def _llm_type(self) -> str:
        """
        Retrieve the type of the LLM.

        Returns:
            str: A string representing the type of the language model.
        """
        return "sagemaker_llm"

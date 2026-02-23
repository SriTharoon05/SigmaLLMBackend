# llm_provider.py
import os
from langchain_openai import AzureChatOpenAI
from langchain_ollama import ChatOllama

OLLAMA_URL = os.getenv("OLLAMA_URL", "https://becalmed-anahi-countably.ngrok-free.dev/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b-q4_K_M")

def get_chat_model():
    return AzureChatOpenAI(
    azure_deployment="gpt-4o",
    azure_endpoint=os.getenv("azure_base_url"),
    api_key=os.getenv("azure_api_key"),
    api_version=os.getenv("azure_api_version"),
    temperature=0,
    )

    # return ChatOllama(
    #     model=OLLAMA_MODEL,
    #     base_url=OLLAMA_URL,
    #     temperature=0,
    #     streaming=False
    # )

# llm_provider.py
import os
from typing import Any, Iterator, List, Optional

import requests
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult

# ──────────────────────────────────────────────
# Custom LangChain chat model → HF Space endpoint
# ──────────────────────────────────────────────

HF_SPACE_URL = os.getenv(
    "HF_SPACE_URL",
    "https://sritharoonhf-qwen2-5-coder.hf.space/generate",
)

# Map LangChain message classes → the "type" strings the Flask app expects
_TYPE_MAP = {
    SystemMessage: "system",
    HumanMessage:  "human",
    AIMessage:     "ai",
}


def _serialize_messages(messages: List[BaseMessage]) -> List[dict]:
    """Convert LangChain message objects to plain dicts for the REST call."""
    result = []
    for msg in messages:
        msg_type = _TYPE_MAP.get(type(msg), "human")
        result.append({"type": msg_type, "content": msg.content})
    return result


class HFSpaceChatModel(BaseChatModel):
    """
    LangChain-compatible chat model that forwards requests to the
    Qwen2.5-Coder Flask wrapper running on Hugging Face Spaces.

    Usage
    -----
    llm = HFSpaceChatModel()
    # or with custom settings:
    llm = HFSpaceChatModel(endpoint_url="https://...", temperature=0.2)
    """

    endpoint_url: str  = HF_SPACE_URL
    temperature:  float = 0.0
    max_tokens:   int   = 1024
    timeout:      int   = 120   # seconds

    # ── Required by BaseChatModel ──────────────────────────────────────────

    def _generate(
        self,
        messages:    List[BaseMessage],
        stop:        Optional[List[str]] = None,
        run_manager: Any                 = None,
        **kwargs,
    ) -> ChatResult:
        payload = {
            "messages":    _serialize_messages(messages),
            "temperature": self.temperature,
            "max_tokens":  self.max_tokens,
        }

        resp = requests.post(
            self.endpoint_url,
            json=    payload,
            timeout= self.timeout,
        )
        resp.raise_for_status()

        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"HF Space error: {data['error']}")

        text = data.get("response", "")
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=text))]
        )

    @property
    def _llm_type(self) -> str:
        return "hf-space-qwen2.5-coder"


# ──────────────────────────────────────────────
# Public factory — drop-in replacement for the
# previous get_chat_model() function
# ──────────────────────────────────────────────

def get_chat_model() -> BaseChatModel:
    """
    Returns the active chat model.

    Switch between providers by setting the CHAT_PROVIDER env variable:
      CHAT_PROVIDER=azure   → AzureChatOpenAI  (original)
      CHAT_PROVIDER=ollama  → ChatOllama
      CHAT_PROVIDER=hf      → HFSpaceChatModel  ← default
    """
    provider = os.getenv("CHAT_PROVIDER", "hf").lower()

    if provider == "azure":
        from langchain_openai import AzureChatOpenAI
        return AzureChatOpenAI(
            azure_deployment= "gpt-4o",
            azure_endpoint=   os.getenv("azure_base_url"),
            api_key=          os.getenv("azure_api_key"),
            api_version=      os.getenv("azure_api_version"),
            temperature=      0,
        )

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=      os.getenv("OLLAMA_MODEL", "qwen3:8b-q4_K_M"),
            base_url=   os.getenv("OLLAMA_URL",   "https://becalmed-anahi-countably.ngrok-free.dev/"),
            temperature=0,
            streaming=  False,
        )

    # Default: HF Space
    return HFSpaceChatModel(
        endpoint_url= HF_SPACE_URL,
        temperature=  0.0,
        max_tokens=   1024,
    )
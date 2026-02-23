import os
from langchain_openai import AzureChatOpenAI
from langchain.agents import create_agent
from backend.tools import ubti_lookup

from core.llm.llm_provider import get_chat_model

chat_model = get_chat_model()

def get_ubti_agent(checkpointer):
    tools = [ubti_lookup]
    system_prompt = """You are a UBTI Web Assistant. Look up 'about' or 'services' pages using `ubti_lookup` tool.
    """
    
    agent = create_agent(
        model=chat_model,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        debug=False
    )
    return agent
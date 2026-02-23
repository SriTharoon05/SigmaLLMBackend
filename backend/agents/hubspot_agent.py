import os
from langchain_openai import AzureChatOpenAI
from langchain.agents import create_agent
from backend.tools import fetch_hubspot_companies, fetch_hubspot_tasks

from core.llm.llm_provider import get_chat_model

chat_model = get_chat_model()

def get_hubspot_agent(checkpointer):
    tools = [fetch_hubspot_companies, fetch_hubspot_tasks]
    system_prompt = """You are a HubSpot Assistant. Help users find companies and tasks. Do not return redirect links.
    USE `fetch_hubspot_companies` tool if looking for companies and `fetch_hubspot_tasks` tool if looking for tasks.
    """
    
    agent = create_agent(
        model=chat_model,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        debug=False
    )
    return agent
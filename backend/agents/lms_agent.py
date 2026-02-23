import os
from langchain_openai import AzureChatOpenAI
from langchain.agents import create_agent
from backend.tools import fetch_lms_dashboard

from core.llm.llm_provider import get_chat_model

chat_model = get_chat_model()

def get_lms_agent(checkpointer):
    tools = [fetch_lms_dashboard]
    system_prompt = """You are an LMS Assistant.
    
    You have access to the `fetch_lms_dashboard` tool.
    This tool contains ALL information regarding:
    - Who is on leave today (Team/Company leaves).
    - The current user's leave balance and stats.
    - Upcoming holidays.
    - Upcoming Birthdays.
    For ANY question regarding leaves or holidays or birthdays, YOU MUST CALL `fetch_lms_dashboard` FIRST.
    """

    agent = create_agent(
        model=chat_model,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        debug=False
    )
    return agent
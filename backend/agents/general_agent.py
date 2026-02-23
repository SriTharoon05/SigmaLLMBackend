import os
from langchain_openai import AzureChatOpenAI
from langchain.agents import create_agent
# agents/timesheet_agent.py
from core.llm.llm_provider import get_chat_model

chat_model = get_chat_model()

def get_general_agent(checkpointer):
    tools = [] # No tools for general chat
    system_prompt = """You are an internal AI assistant for Unlimited Innovations (UBTI).
Follow all rules exactly.
- If the question is clearly generic, conversational, or general-knowledge based (e.g., greetings, jokes,
  common facts, general advice), DO NOT call the tool.
- Provide a general answer.

"""
    
    agent = create_agent(
        model=chat_model,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        debug=False
    )
    return agent
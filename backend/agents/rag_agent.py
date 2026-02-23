import os
from langchain_openai import AzureChatOpenAI
from langchain.agents import create_agent
from backend.tools import retrieve_documents

from core.llm.llm_provider import get_chat_model

chat_model = get_chat_model()

def get_rag_agent(checkpointer):
    tools = [retrieve_documents]
    system_prompt = """
You are an internal AI assistant for Unlimited Innovations (UBTI).
Use previous conversation context if available.
RETRIEVAL PRIORITY (Highest → Lowest)
------------------------------------------------------------

1. Uploaded PDFs
- Always check uploaded PDFs first.
- If relevant information is found, answer ONLY using the PDFs.
- List the relevant PDF filenames in "Source Documents".

2. Qdrant Knowledge Base (Tool Required)
- If NO relevant PDF information is found AND the user’s query requires internal/company information,
  you MUST call the "retrieve_documents" tool to search the Qdrant database.
- Also call the tool if the user explicitly asks for more internal information.
- Use the retrieved documents to answer and list their filenames in "Source Documents".

3. General Answers (No Tool Call for Generic Questions)
- If the question is clearly generic, conversational, or general-knowledge based (e.g., greetings, jokes,
  common facts, general advice), DO NOT call the tool.
- Provide a general answer.
- "Source Documents" must be:
  No Documents Retrieved

4. When No Relevant Documents Are Found
- If neither PDFs nor Qdrant contain relevant information:
  • First, INFORM the user: "No relevant internal documents were found for your query."
  • Then provide a general answer.
- "Source Documents" must be exactly:
  "No Documents Retrieved"
    
------------------------------------------------------------
RESPONSE FORMAT
------------------------------------------------------------
[Your response here]

Source Documents:
[List filenames of PDFs or Qdrant documents, or "No Documents Retrieved"]"""
    
    agent = create_agent(
        model=chat_model,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        debug=False
    )
    return agent
import os
from pprint import pprint
import django
import time
import json
import logging
import fitz
from langgraph.checkpoint.memory import MemorySaver
from langchain_community.callbacks.manager import get_openai_callback
from langchain_core.messages import SystemMessage, HumanMessage # Import Message Types

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()
from django.conf import settings
from .models import Conversation, QueryLog

# Import Router and Agents
from .router import classify_intent
from .agents.timesheet_agent import get_timesheet_agent
from .agents.hubspot_agent import get_hubspot_agent
from .agents.rag_agent import get_rag_agent
from .agents.lms_agent import get_lms_agent
from .agents.ubti_agent import get_ubti_agent
from .agents.general_agent import get_general_agent

# ------------------- Helpers -------------------
def chunk_text(text, chunk_size=500):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i + chunk_size]))
    return chunks

def process_session_pdf(user_id: int, conversation_id: int):
    session_folder = os.path.join(settings.BASE_DIR, "tmp_uploads", str(user_id), str(conversation_id))
    if not os.path.exists(session_folder):
        return []

    chunks = []
    for fname in os.listdir(session_folder):
        file_path = os.path.join(session_folder, fname)
        try:
            pdf = fitz.open(file_path)
            text = "".join([page.get_text("text") for page in pdf])
            pdf.close()
            if not text.strip(): continue
            for i, chunk_piece in enumerate(chunk_text(text)):
                chunks.append({
                    "file_name": fname,
                    "chunk_index": i,
                    "text": chunk_piece
                })
        except Exception:
            continue
    return chunks

def track_token_usage_and_store(conversation, callback):
    conversation.tokens_used = callback.total_tokens
    conversation.prompt_tokens = callback.prompt_tokens
    conversation.completion_tokens = callback.completion_tokens
    conversation.total_cost = callback.total_cost
    conversation.save()

# ------------------- Main Orchestration -------------------
memory = MemorySaver()

# Initialize Agents
AGENTS = {
    "timesheet": get_timesheet_agent(memory),
    "hubspot": get_hubspot_agent(memory),
    "documents": get_rag_agent(memory),
    "lms": get_lms_agent(memory),
    "ubtilookup": get_ubti_agent(memory),
    "general": get_general_agent(memory)
}

def ask_agent(prompt: str, trinity_Auth: str, lms_jwt_token: str, strEmpID: str, user=None, conversation_id=None):
    print("Entered Agent")
    
    # 1. Get/Create Conversation
    if conversation_id:
        try:
            conversation = Conversation.objects.get(id=conversation_id, user=user)
        except Conversation.DoesNotExist:
            conversation = Conversation.objects.create(user=user, title=prompt[:50])
            conversation_id = conversation.id
    else:
        conversation = Conversation.objects.create(user=user, title=prompt[:50])
        conversation_id = conversation.id

    # 2. PDF Processing
    pdf_chunks = process_session_pdf(user_id=user.id, conversation_id=conversation_id)

    # Fetch History for Router
    history_str = ""
    last_logs = QueryLog.objects.filter(conversation=conversation).order_by('timestamp')[:15]
    print(last_logs)
    if last_logs:
        for log in reversed(last_logs):
            history_str += f"User: {log.prompt}\nAI: {log.response}\n---\n"

    # 3. Router
    # print("History for Router:", history_str)

    if conversation.active_intent is None:
        # fresh intent, ignore workflow bias
        classified_intent = classify_intent(
            prompt,
            history="",   # 🔥 important
            active_intent=None
        )
    else:
        classified_intent = classify_intent(
            prompt,
            history=history_str,
            active_intent=conversation.active_intent
        )

    print("LLM Classified Intent:", classified_intent)

    # Update active intent ONLY if meaningful
    if conversation.active_intent is None and classified_intent == "timesheet":
        conversation.active_intent = "timesheet"
        conversation.save(update_fields=["active_intent"])

    intent = classified_intent
    selected_agent = AGENTS.get(intent, AGENTS["general"])

    # 4. Invoke
    start_time = time.time()
    
    # Create System Messages
    user_context_msg = f"""User Context:
    - Name: {user.username}
    - Email: {user.email}
    Always greet the user by name if this is the start of the conversation.
    """
    
    # Use proper Message Objects instead of dicts for safety
    agent_messages = [
        SystemMessage(content=user_context_msg),
        SystemMessage(content=f"Context from uploaded files: {str(pdf_chunks)}"), 
        HumanMessage(content=prompt)
    ]

    with get_openai_callback() as cb:
        try:
            response_obj = selected_agent.invoke(
                {"messages": agent_messages},
                config={
                    "configurable": {
                        "thread_id": str(conversation_id),
                        "trinity_auth": trinity_Auth or "",
                        "strEmpID": strEmpID or "",
                        "lms_jwt_token": lms_jwt_token or "",
                    }
                }
            )

            # LangGraph always returns a state dict
            final_state = response_obj

            messages = final_state.get("messages", [])
            current_stage = final_state.get("current_stage")

            # Extract last AI message safely
            if messages:
                last_msg = messages[-1]
                response_text = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
            else:
                response_text = ""

            # 6. Extract Source Documents
            lines = response_text.strip().splitlines()
            source_header_idx = None
            for i in reversed(range(len(lines))):
                if lines[i].strip().lower().startswith("source documents"):
                    source_header_idx = i
                    break

            if source_header_idx is not None:
                source_lines = lines[source_header_idx + 1:]
                content_only = "\n".join(lines[:source_header_idx]).strip()
                source_documents = [line.strip("- ").strip() for line in source_lines if line.strip()]
            else:
                content_only = response_text.strip()
                source_documents = []

            # 7. PDF Source Logic
            if isinstance(pdf_chunks, list):
                pdf_source_files = list({chunk["file_name"] for chunk in pdf_chunks if "file_name" in chunk})
            else:
                pdf_source_files = []
            
            pdf_source_files_used = [f for f in pdf_source_files if f in source_documents]
            all_sources = list(set(source_documents + pdf_source_files_used))

            # 8. Source Links
            BASE_HF_URL = "https://sritharoon-sigma-llm.hf.space"
            source_links = []
            for doc in all_sources:
                if doc != "No Documents Retrieved":
                    if doc in pdf_source_files_used:
                        source_links.append({"name": doc, "url": f"{BASE_HF_URL}/api/download/{user.id}/{conversation_id}/{doc}"})
                    else:
                        source_links.append({"name": doc, "url": f"{BASE_HF_URL}/api/download_source_doc/{doc}"})
            
            source_links_str = json.dumps(source_links)

            # 9. Logging
            track_token_usage_and_store(conversation, cb)
            latency = time.time() - start_time
            
            QueryLog.objects.create(
                conversation=conversation,
                prompt=prompt,
                response=content_only,
                sources=source_links_str,
                tokens_used=conversation.tokens_used,
                prompt_tokens=conversation.prompt_tokens,
                completion_tokens=conversation.completion_tokens,
                total_cost=conversation.total_cost,
                latency=latency
            )
            print("Current_Stage:", current_stage)
            if current_stage == "done":
                conversation.active_intent = None
                conversation.save(update_fields=["active_intent"])


            return {
                "conversation_id": conversation_id,
                "response_text": content_only,
                "source_documents": source_links,
                "tokens_used": conversation.tokens_used,
                "prompt_tokens": conversation.prompt_tokens,
                "completion_tokens": conversation.completion_tokens,
                "total_cost": conversation.total_cost,
                "latency": latency,
            }

        except Exception as e:
            return {"conversation_id": conversation_id, "error": f"Agent error: {str(e)}"}
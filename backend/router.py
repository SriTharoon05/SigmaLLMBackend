
from core.llm.llm_provider import get_chat_model
from rich.pretty import pprint
router_llm = get_chat_model()

# 1. Define Valid Categories clearly
VALID_INTENTS = ["timesheet", "lms", "documents", "hubspot", "ubtilookup", "general"]

SYSTEM_TEMPLATE = """
You are an expert intent classifier for an enterprise chatbot.

Your job is to map the USER INPUT to exactly one of the following categories:
1. **timesheet**: If user wants to fill timesheet, Logging hours, projects, week ending dates, saving/submitting.
2. **lms**: Leave, holidays, birthday details,attendance, dashboard, employee stats.
3. **documents**: Technical docs, internal projects, code references, how-to guides.
4. **hubspot**: CRM, companies, contacts, deals, tasks.
5. **ubtilookup**: UBTI company info, services, "about us", leadership.
6. **general**: Greetings, small talk, questions about the bot itself.

### PREVIOUS CONVERSATION
{context_text}
### ACTIVE INTENT
{active_intent}

### CRITICAL RULES
 **Active Intent**: If ACTIVE INTENT is "timesheet" then return only the "timesheet" category, If its None then Classify based on the user message content.
 **Output**: Return ONLY the raw category name (lowercase). Do not add punctuation.

"""

def classify_intent(prompt: str, history: str = "", active_intent: str = None) -> str:
    # 2. Handle empty history more cleanly for the LLM
    context_text = history if history else "No previous conversation."
    print("------------History:", context_text)
    print("------------Active Intent for Router:", active_intent)
    user_message_content = f""" ### USER INPUT {prompt} """

    messages = [
        {"role": "system", "content": SYSTEM_TEMPLATE.format(context_text=context_text, active_intent=active_intent)},
        {"role": "user", "content": user_message_content}
    ]
    
    try:
        response = router_llm.invoke(messages)
        intent = response.content.strip().lower()
        pprint(f"Router LLM Response Intent: {intent}")
        # 3. Safety Check: If LLM hallucinates a new category, default to general
        if intent not in VALID_INTENTS:
            # Fallback logic: check if "timesheet" is in the intent string just in case
            if "timesheet" in intent: return "timesheet"
            return "general"
            
        return intent

    except Exception as e:
        print(f"Router Error: {e}")
        return "general"
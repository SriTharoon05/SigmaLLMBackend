import os
import json
from typing import TypedDict, Annotated, List
import operator
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from rich.pretty import pprint
# Import your existing tools
from backend.tools import fetch_timesheet, select_project, log_hours, save_timesheet
from datetime import datetime
from core.llm.llm_provider import get_chat_model

llm = get_chat_model()

# --- 2. Define State ---
def replace(_, new):
    return new

class TimesheetState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    current_stage: Annotated[str, replace]
    project_list_context: Annotated[str, replace]
    week_ending: Annotated[str, replace]        # ← ADD
    selected_project: Annotated[str, replace]
# --- 3. Define Nodes ---

def intent_router(state: TimesheetState, config):
    thread_id = config.get("configurable", {}).get("thread_id", "UNKNOWN")
    current_stage = state.get("current_stage", "init")
    messages = state.get("messages", [])

    pprint(f"\n{'='*40}")
    pprint(f"DEBUG: SESSION ID   >> {thread_id}")
    pprint(f"DEBUG: CURRENT STAGE >> {current_stage}")
    pprint(f"DEBUG: HISTORY SIZE  >> {len(messages)} messages")
    pprint(f"{'='*40}\n")

    if messages and isinstance(messages[-1], BaseMessage):
        last_msg = messages[-1].content.lower()

        # 🔁 RESTART INTENT (THIS IS THE KEY)
        restart_triggers = [
            "fill timesheet",
            "timesheet",
            "log time",
            "log hours",
            "new timesheet"
        ]

        if current_stage == "done" and any(t in last_msg for t in restart_triggers):
            pprint("DEBUG: Restart intent detected -> Resetting to init")
            return "init"

        # Existing heuristics
        days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        has_day = any(day in last_msg for day in days)
        has_number = any(char.isdigit() for char in last_msg)

        if has_day and has_number:
            pprint("DEBUG: Router detected hours input -> Forcing 'log'")
            return "log"

        if state.get("project_list_context") and current_stage == "init":
            pprint("DEBUG: Router detected project context -> Forcing 'project'")
            return "project"

    VALID_STAGES = {"init", "project", "log", "submit", "done"}
    if current_stage in VALID_STAGES:
        return current_stage
    return "init"


def init_node(state: TimesheetState, config):
    """Step 1: Check for Week Ending Date -> Fetch Timesheet"""
    messages = state["messages"]
    pprint((f"-------------------------messages:", messages))
    last_user_msg = messages[-1].content
    pprint((f"-------------------------last_user_msg:", last_user_msg))
    # --- Check: Did the user provide a date? ---
    currentDate = datetime.now().date()
    pprint(f"Current Date: {currentDate}")
    check_prompt = f"""
    Analyze the user input: "{last_user_msg}"
    
    Task: Extract the specific date reference if present.
    IF user told "Last Friday" or "This Friday" use Current Date : {currentDate} and find the corresponding date.
    CRITICAL OUTPUT RULES:
    1. If a date is found, convert it to MM/dd/yyyy format.
    2. Return ONLY the date string (e.g., 01/16/2026). 
    3. Do NOT include words like "The date is", "Extracted:", or any markdown formatting (no bold **).
    4. If NO date is found (e.g., input is just "fill timesheet"), return exactly: MISSING
    """
    
    extracted_date = llm.invoke(check_prompt).content.strip()
    pprint((f"-------------------------extracted_date:", extracted_date))
    if "MISSING" in extracted_date:
        # User didn't give a date. Ask for it and STAY in 'init' stage.
        return {
            "messages": [AIMessage(content="Sure! Please provide the **Week Ending Date** for the timesheet (e.g., 'Last Friday' or 'Oct 27').")],
            "current_stage": "init" 
        }

    # --- Date found. Fetch Data. ---
    result = fetch_timesheet.invoke({"week_ending": extracted_date}, config=config)
    
    if "Error" in result:
        # API Error (e.g., bad date format). Ask again.
        return {
            "messages": [AIMessage(content=f"{result} Please provide a valid Week Ending Date.")],
            "current_stage": "init" 
        }
    else:
        # Success: List projects is handled by the tool output. Move to next stage.
        # --- 3. FORMATTING USING PROMPT (The Change) ---
        # We ask the LLM to prettify the raw tool output
        format_prompt = f"""
        The following is the raw output from a database query:
        "{result}"

        Please rewrite this information to be clean and readable for the user:
        1. Start with the success message.
        2. List every project on a **new line** with a bullet point.
        3. **Bold** every project name.
        4. Add a blank line after the list.
        5. End exactly with: "Great! Now, which **Project** would you like to work on?"
        """
        
        formatted_msg = llm.invoke(format_prompt).content
        
        return {
            "messages": [AIMessage(content=formatted_msg)],
            "current_stage": "project",
            "project_list_context": result,
            "week_ending": extracted_date 
        }

def project_node(state: TimesheetState, config):
    """Step 2: Handle Project Selection with LLM Matching"""
    messages = state["messages"]
    pprint((f"-------------------------messages:", messages))
    # 1. Get User Input ("power automate coe")
    last_user_msg = messages[-1].content
    pprint((f"-------------------------last_user_msg:", last_user_msg))
    # 2. Get the Project List from the PREVIOUS AI message
    # We look at [-2] because [-1] is the user, so [-2] is what the bot just said (the list)
    project_list_str = state.get("project_list_context", "")
    pprint((f"-------------------------project_list_str:", project_list_str))
    # 3. LLM Match Step
    # We ask the LLM to pick the exact string from the list based on user input
    matcher_prompt = f"""
    Context: The user needs to select a project from a specific list.
    
    1. HERE IS THE LIST OF AVAILABLE PROJECTS:
    \"""
    {project_list_str}
    \"""
    
    2. HERE IS WHAT THE USER TYPED:
    "{last_user_msg}"
    
    TASK:
    - Find the project from the list that best matches the user's input.
    - You must handle acronyms (e.g., "CoE" = "Center of Excellence") and partial matches.
    - Return ONLY the EXACT full project name string from the list without altering any spacing or formatting.
    - Do not add explanations.
    - If you cannot find a match, return 'NO_MATCH'.
    """
    
    # Invoke LLM to get the clean name
    pprint((f"-------------------------matcher_prompt:", matcher_prompt))
    full_project_name = llm.invoke(matcher_prompt).content.strip()
    pprint((f"-------------------------full_project_name:", full_project_name))
    # If LLM failed to match, we default to passing the raw user input 
    # (letting the tool handle the error)
    if "NO_MATCH" in full_project_name:
        target_name = last_user_msg
    else:
        target_name = full_project_name.replace('"', '') # Clean up quotes if LLM added them
    pprint((f"-------------------------target_name:", target_name))
    # 4. Call the Tool with the CLEAN Name
    result = select_project.invoke(target_name)

    if "Error" in result or "Multiple projects" in result:
        return {
            "messages": [AIMessage(content=result)],
            "current_stage": "project"
        }
    else:
        return {
            "messages": [AIMessage(content=f"{result}\n\nPlease provide the hours (e.g., 'Monday - 9 hours, Tuesday - 9 hours').")],
            "current_stage": "log",
            "selected_project": target_name,
        }

def log_node(state: TimesheetState, config):
    """Step 3: Handle Logging Hours"""
    messages = state["messages"]
    last_user_msg = messages[-1].content

    extractor_prompt = f"""
    The user input describes hours worked: "{last_user_msg}"
    
    Extract the hours for each day mentioned.
    Input format examples:
    If user mentioned Mon to Fri each day 9 hours means fill json according to that.
    If user mentioned Mon to wed 9 hrs and rest 2 days 8 hrs then fill accordingly.
    You must understand the mapping of short forms to full day names.
    "Monday - 9 hours", "Mon: 9", "9 hours on Monday".
    
    Return STRICT JSON: {{"monday": 9, "tuesday": 9}}. 
    - Keys must be lowercase full day names.
    - Values must be numbers (float or int).
    - If no valid hours found, return 'INVALID'.
    """

    extraction = llm.invoke(extractor_prompt).content
    pprint((f"-------------------------extraction:", extraction))

    if "INVALID" in extraction:
        return {
            "messages": [AIMessage(content="I couldn't understand those hours. Please use the format: 'Monday - 9 hours'.")],
            "current_stage": "log"
        }

    try:
        json_str = extraction.replace("```json", "").replace("```", "").strip()
        hours_dict = json.loads(json_str)

        # ✅ Inject week_ending and selected_project from state into config
        config["configurable"]["week_ending"] = state.get("week_ending", "")
        config["configurable"]["selected_project"] = state.get("selected_project", "")

        result = log_hours.invoke({"day_hours": hours_dict}, config=config)

        return {
            "messages": [AIMessage(content=f"{result}\n\nDo you want to **SAVE** or **SUBMIT** this timesheet?")],
            "current_stage": "submit"
        }
    except Exception as e:
        return {
            "messages": [AIMessage(content=f"Error processing hours: {str(e)}. Please try again.")],
            "current_stage": "log"
        }


def submit_node(state: TimesheetState, config):
    """Step 4: Save or Submit"""
    messages = state["messages"]
    last_user_msg = messages[-1].content.lower()

    if "submit" in last_user_msg:
        action = "submit"
    elif "save" in last_user_msg:
        action = "save"
    else:
        return {
            "messages": [AIMessage(content="Please clarify: do you want to **Save** or **Submit**?")],
            "current_stage": "submit"
        }

    # ✅ Inject week_ending from state into config so save_timesheet tool can access it
    config["configurable"]["week_ending"] = state.get("week_ending", "")
    config["configurable"]["selected_project"] = state.get("selected_project", "")

    result = save_timesheet.invoke({"action": action}, config=config)

    return {
        "messages": [AIMessage(content=f"{result}\n\nTimesheet process complete!")],
        "current_stage": "done",
        "project_list_context": "",
        "week_ending": "",          # ✅ reset after done
        "selected_project": "",     # ✅ reset after done
    }


# --- 4. Build Graph ---
def get_timesheet_agent(checkpointer):
    workflow = StateGraph(TimesheetState)

    # Add Nodes
    workflow.add_node("init_node", init_node)
    workflow.add_node("project_node", project_node)
    workflow.add_node("log_node", log_node)
    workflow.add_node("submit_node", submit_node)

    # Set Entry Point based on 'current_stage'
    workflow.set_conditional_entry_point(
        intent_router,
        {
            "init": "init_node",
            "project": "project_node",
            "log": "log_node",
            "submit": "submit_node",
            "done": END
        }
    )

    # Define Edges: After each node runs, STOP and wait for user input (END)
    workflow.add_edge("init_node", END)
    workflow.add_edge("project_node", END)
    workflow.add_edge("log_node", END)
    workflow.add_edge("submit_node", END)

    return workflow.compile(checkpointer=checkpointer)
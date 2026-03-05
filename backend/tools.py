from difflib import get_close_matches
import json
import logging
import os
from typing import Dict, List
import django
from dotenv import load_dotenv
import requests
from langchain_core.runnables import RunnableConfig
from sentence_transformers import SentenceTransformer
# ------------------- Django setup -------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()
from langchain_core.tools import tool,StructuredTool

from langchain_community.document_loaders import WebBaseLoader

from qdrant_client import QdrantClient

load_dotenv()

# ------------------- Config -------------------
embedding_fn = SentenceTransformer("all-MiniLM-L6-v2")

QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "docs")
QDRANT_URL = os.getenv("QDRANT_URL", "qdrant")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
TOP_K = int(os.getenv("QDRANT_TOP_K", 5))

qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
MAX_WEEKLY_HOURS = 45
DAY_MAP = {
    "saturday": "D1", "sunday": "D2", "monday": "D3", "tuesday": "D4",
    "wednesday": "D5", "thursday": "D6", "friday": "D7"
}
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TimesheetAgent")
 
# ----------------------------
# Global state (per user/session)
# ----------------------------
SESSION_STATE = {
    "week_ending": None,
    "timesheet_data": None,
    "hours_payload": [],
    "current_project_id": None, # NEW: Tracks the currently selected project
    "current_budget_id": None   # NEW: Tracks the currently selected budget
}
 
# ----------------------------
# Helpers Func
# ----------------------------
def init_hours_payload(timesheet_data: dict) -> List[Dict]:
    payload = []
    for p in timesheet_data.get("projects", []):
        entry = {
            "BudgetID": p["budgetId"],
            "TTBudgetAssignmentID": p["budgetAssignmentId"],
            "ProjectID": p["projectId"],
            "HourlyTypeName": p.get("hourlyTypeName", "Absolute")
        }
        for i in range(1, 8):
            dn = f"D{i}"
            entry[dn] = p.get("dailyHours", {}).get(dn, 0)
            entry[f"{dn}ID"] = p.get("dailyHours", {}).get(f"{dn}ID", 0)
        payload.append(entry)
    return payload

def compute_total_hours(hours_payload: List[Dict]) -> float:
    total = 0.0
    for entry in hours_payload:
        for i in range(1, 8):
            total += float(entry.get(f"D{i}", 0))
    return total

def load_ubti_page(page: str):
    url_map = {
        "about": "https://ubtiinc.com/our-story/",      # UBTI About page
        "services": "https://ubtiinc.com/services/"     # UBTI Services page
    }
    url = url_map.get(page.lower())
    if not url:
        return {"content": "Invalid page", "url": None}
    print(f"Loading URL:", url)
 
    # Load the page content (optional)
    loader = WebBaseLoader(url)
    docs = loader.load()
    text = docs[0].page_content[:6000]
 
 
    # Return only the canonical URL in the tool output
    return {"content": text, "url": url}


@tool(
    description="Fetch a list of companies from HubSpot CRM including their industry, location, and phone details.",
    response_format="content"
)
def fetch_hubspot_companies():
    """
    Fetch HubSpot company records and return specific business details
    including name, industry, city, country, and phone.
    """

    # Endpoint with requested properties
    url = "https://api.hubapi.com/crm/v3/objects/companies"
    params = {
        "properties": "name,industry,city,country,phone",
        "limit": 25  # Adjust limit as needed
    }

    headers = {
        "Authorization": f"Bearer {os.getenv('HUBSPOT_API_KEY')}", # Replace with your PAT
        "Content-Type": "application/json"
    }

    try:
        # Using params argument for cleaner URL management
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        filtered_companies = []

        for company in data.get("results", []):
            props = company.get("properties", {})
            filtered_companies.append({
                "id": company.get("id"),
                "name": props.get("name"),
                "industry": props.get("industry"),
                "city": props.get("city"),
                "country": props.get("country"),
                "phone": props.get("phone"),
                "link": f"https://app.hubspot.com/contacts/YOUR_PORTAL_ID/company/{company.get('id')}"
            })

        return filtered_companies

    except requests.exceptions.HTTPError as http_err:
        return f"HTTP error occurred: {http_err}"
    except Exception as e:
        return f"An error occurred: {e}"

@tool(
    description="View HubSpot CRM tasks.",
    response_format="content"
)
def fetch_hubspot_tasks():
    """
    Fetch HubSpot tasks and return only selected fields
    """

    url = "https://api.hubapi.com/crm/objects/v3/tasks?properties=hs_task_subject,hs_task_body,hs_task_status,hs_task_priority,hs_task_due_date,hubspot_owner_id:&limit=5"


    headers = {
        "Authorization": f"Bearer {os.getenv('HUBSPOT_API_KEY')}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        filtered_tasks = []

        for task in data.get("results", []):
            filtered_tasks.append({
                "id": task.get("id"),
                "properties": {
                    "hs_createdate": task["properties"].get("hs_createdate"),
                    "hs_lastmodifieddate": task["properties"].get("hs_lastmodifieddate"),
                    "hs_object_id": task["properties"].get("hs_object_id"),
                    "hs_task_body": task["properties"].get("hs_task_body"),
                    "hs_task_priority": task["properties"].get("hs_task_priority"),
                    "hs_task_status": task["properties"].get("hs_task_status"),
                    "hs_task_subject": task["properties"].get("hs_task_subject"),
                },
                "createdAt": task.get("createdAt"),
                "updatedAt": task.get("updatedAt")
            })
        print(f"FILTERED TASKS:", filtered_tasks)
        return filtered_tasks

    except Exception as e:
        return f"Failed to fetch HubSpot tasks: {e}"


@tool(
    description="Fetch the LMS dashboard, which includes TEAM LEAVES, COMPANY HOLIDAYS, and personal stats.",
    response_format="content"
)
def fetch_lms_dashboard(config: RunnableConfig):
    """
    Fetch the full LMS dashboard.
    
    Returns:
    - List of employees currently on leave (Who is on leave).
    - Upcoming holidays.
    - Personal leave balance and stats.
    
    Useful for answering: "Who is on leave?", "What are the holidays?", "My leave balance".
    """

    # Read config values (sent from your Django view)
    configurable = config.get("configurable", {})
    emp_id = configurable.get("strEmpID")
    lms_token = configurable.get("lms_jwt_token")

    # print(f"CONFIG RECEIVED:", configurable)
    # print(f"EMP ID:", emp_id)
    # print(f"LMS TOKEN:", lms_token)

    if not emp_id:
        return "Error: Employee ID (strEmpID) is required."

    if not lms_token:
        return "Error: LMS JWT Token is required."

    # Your deployed proxy endpoint:
    url = "https://nextjs-boilerplate-git-main-princebhowras-projects.vercel.app/api/lms/dashboard"

    payload = {
        "empId": emp_id,
        "token": lms_token
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        dashboard = resp.json()

        # Store in session if you want for chained queries
        SESSION_STATE["lms_dashboard"] = dashboard

        # print(f"LMS DASHBOARD FETCHED:", dashboard)
        return dashboard

    except Exception as e:
        return f"Failed to fetch LMS dashboard: {str(e)}"


@tool(response_format="content")
def retrieve_documents(query: str, top_k: int = TOP_K) -> dict:
    """Retrieve top-k relevant documents from Qdrant using embeddings."""
    try:
        query_vector = embedding_fn.encode(query).tolist()
        results = qdrant.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        limit=5,  # fetch more for re-ranking
    )

        if not results:
            return {"content": "No relevant documents found.", "source_documents": []}

        content_lines = []
        source_documents = []

        for r in results.points:
            payload = r.payload or {}
            title = payload.get("source", "Untitled")
            text = payload.get("page_content", payload.get("text", ""))
            content_lines.append(f"Title: {title}\n{text}")
            source_documents.append(payload.get("source", "Untitled"))

        return {
            "content": "\n---\n".join(content_lines),
            "source_documents": source_documents
        }

    except Exception as e:
        return {"content": f"Error retrieving documents: {str(e)}", "source_documents": []}
    
ubti_lookup = StructuredTool.from_function(
    name="ubti_lookup",
    description="Fetch information from the public UBTI website. Arg must be 'about' or 'services'.",
    func=load_ubti_page
)    

# ----------------------------
# 1. Fetch Tool
# ----------------------------
@tool(
    description="Fetch the user's timesheet for a given week-ending date. Always call this first.",
    response_format="content"
)
def fetch_timesheet(week_ending: str, config: RunnableConfig):
    """Fetch timesheet JSON and initialize hours_payload"""
    configurable = config.get("configurable", {})
    trinity_auth = configurable.get("trinity_auth")

    if not trinity_auth:
        return "Error: Missing TrinityAuth token."

    url = "https://nextjs-boilerplate-git-main-princebhowras-projects.vercel.app/api/timesheet"
    
    # Simple validation to ensure format is roughly correct (optional)
    if not week_ending:
        return "Error: Week ending date is required."

    payload = {
        "trinityAuth": trinity_auth,
        "weekEndingDay": week_ending
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Reset Session
        SESSION_STATE["week_ending"] = week_ending
        SESSION_STATE["timesheet_data"] = data
        SESSION_STATE["hours_payload"] = init_hours_payload(data)
        SESSION_STATE["current_project_id"] = None # Reset selection
        print(f"Timesheet Data:", json.dumps(data) )
        project_list = ", ".join([p["projectName"] for p in data.get("projects", [])])
        return f"Timesheet fetched successfully for {week_ending}. Available Projects: {project_list}"
    except Exception as e:
        return f"Failed to fetch timesheet: {e}"

# ----------------------------
# 2. Select Project Tool (Step 1 of Entry)
# ----------------------------
@tool(
    description="Select and verify a project from the fetched timesheet.",
    response_format="content"
)
def select_project(project_name: str) -> str:
    """Verifies project existence and sets it as the active project."""
    timesheet_data = SESSION_STATE.get("timesheet_data")
    
    if not timesheet_data:
        return "Error: No timesheet loaded. Please ask for the week-ending date first."

    projects = timesheet_data.get("projects", [])
    
    print(f"Available Projects:", [p["projectName"].lower() for p in projects])
    print(f"Requested Project Name:", project_name.lower())
    # Simple Case-Insensitive Lookup
    # We expect the LLM to have sent the correct full string, but .lower() is a good safety net.
    matched_project = next(
        (p for p in projects if p["projectName"].lower() == project_name.lower()),
        None
    )

    if not matched_project:
        # If the LLM Hallucinated a name that doesn't exist, we return the valid list.
        existing_names = [p["projectName"] for p in projects]
        # Using bullet points makes it easier for the LLM to read the error
        list_str = "\n".join([f"- {name}" for name in existing_names])
        return f"Error: Project '{project_name}' not found in the loaded timesheet. Here are the valid projects:\n{list_str}"

    # Set Session State
    SESSION_STATE["current_project_id"] = matched_project["projectId"]
    SESSION_STATE["current_budget_id"] = matched_project["budgetId"]
    
    return f"Project '{matched_project['projectName']}' selected successfully."

# ----------------------------
# 3. Log Hours Tool (Step 2 of Entry)
# ----------------------------
@tool(
    description="Log hours for the CURRENTLY selected project. Input format: {'monday': 9, 'tuesday': 8}.",
    response_format="content"
)
def log_hours(day_hours: dict) -> str:
    """Updates hours for the selected project in session state."""
    
    # 1. Validation: Is a project selected?
    if not SESSION_STATE["current_project_id"]:
        return "Error: No project selected. Please select a project first."

    # 2. Update logic
    updated = False
    target_pid = SESSION_STATE["current_project_id"]
    target_bid = SESSION_STATE["current_budget_id"]

    # Search existing payload to update
    for entry in SESSION_STATE["hours_payload"]:
        if entry["ProjectID"] == target_pid and entry["BudgetID"] == target_bid:
            for wday, hrs in day_hours.items():
                if wday.lower() in DAY_MAP:
                    dn = DAY_MAP[wday.lower()]
                    entry[dn] = float(hrs)
                    # Ensure ID exists
                    if f"{dn}ID" not in entry:
                        entry[f"{dn}ID"] = 0
            updated = True
            break
    
    # If not found in payload (rare if init worked, but safe to handle), create new
    if not updated:
        # Find original project data to get metadata
        p_data = next(p for p in SESSION_STATE["timesheet_data"]["projects"] if p["projectId"] == target_pid)
        
        new_entry = {
            "BudgetID": target_bid,
            "TTBudgetAssignmentID": p_data["budgetAssignmentId"],
            "ProjectID": target_pid,
            "HourlyTypeName": p_data.get("hourlyTypeName", "Absolute")
        }
        # Initialize zeros
        for i in range(1, 8):
            dn = f"D{i}"
            new_entry[dn] = 0
            new_entry[f"{dn}ID"] = 0
            
        # Apply hours
        for wday, hrs in day_hours.items():
            if wday.lower() in DAY_MAP:
                new_entry[DAY_MAP[wday.lower()]] = float(hrs)
        
        SESSION_STATE["hours_payload"].append(new_entry)

    # 3. Validation: Total Hours
    total_hours = compute_total_hours(SESSION_STATE["hours_payload"])
    
    # If over limit, we save it anyway but warn the user? Or block it? 
    # Based on prompt requirements, let's return the status.
    msg = f"Hours logged successfully. Current Weekly Total: {total_hours}h."
    if total_hours > MAX_WEEKLY_HOURS:
        msg += f" WARNING: You have exceeded the limit of {MAX_WEEKLY_HOURS}h."

    return msg

# ----------------------------
# 4. Save/Submit Tool
# ----------------------------
@tool(description="Save or submit the timesheet to the server.", response_format="content")
def save_timesheet(action: str, config: RunnableConfig) -> str:
    """Action should be 'save' or 'submit'"""
    configurable = config.get("configurable", {})
    trinity_auth = configurable.get("trinity_auth")
    
    if not trinity_auth:
        return "Error: Missing TrinityAuth token."
    
    if not SESSION_STATE["week_ending"]:
        return "Error: Week ending date not set."

    url = "https://nextjs-boilerplate-git-main-princebhowras-projects.vercel.app/api/trinity/save"
    headers = {"Cookie": f".TrinityAuth={trinity_auth}"}

    payload = {
        "dt": SESSION_STATE["week_ending"],
        "action": action.lower(),
        "hours": SESSION_STATE["hours_payload"]
    }
    print(json.dumps(payload, indent=4))
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        return f"Timesheet {action}ed successfully."
    except Exception as e:
        return f"Failed to {action} timesheet: {str(e)}"
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import uuid
from google.cloud import firestore
from google.adk.tools import ToolContext

# HARDCODED GCP PROJECT ID as required by Agent Platform
PROJECT_ID = "qwiklabs-gcp-01-0482b2deb94b"


def _get_db():
    return firestore.Client(project=PROJECT_ID)


def list_tasks(status: str | None = None, priority: str | None = None) -> list[dict]:
    """Retrieve tasks from the Firestore 'tasks' collection.

    Args:
        status: Optional filter by status ('Pending', 'In Progress', 'Completed').
        priority: Optional filter by priority ('High', 'Medium', 'Low').

    Returns:
        List of task dictionaries.
    """
    db = _get_db()
    query = db.collection("tasks")

    if status:
        query = query.where("status", "==", status)
    if priority:
        query = query.where("priority", "==", priority)

    docs = query.stream()
    tasks = [doc.to_dict() for doc in docs]
    return tasks


def create_task(
    title: str,
    description: str = "",
    priority: str = "Medium",
    due_date: str = "",
    status: str = "Pending",
) -> str:
    """Create a new task in the Firestore 'tasks' collection.

    Args:
        title: Short title for the task.
        description: Detailed explanation of the task.
        priority: Task priority ('High', 'Medium', 'Low').
        due_date: Due date string (e.g., '2026-09-30').
        status: Task status ('Pending', 'In Progress', 'Completed').

    Returns:
        Confirmation string containing task_id.
    """
    db = _get_db()
    task_id = f"task-{uuid.uuid4().hex[:6]}"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    task_data = {
        "task_id": task_id,
        "title": title,
        "description": description,
        "priority": priority,
        "status": status,
        "due_date": due_date,
        "created_at": now,
        "updated_at": now,
    }

    db.collection("tasks").document(task_id).set(task_data)
    return f"Task created successfully: ID {task_id} ('{title}')"


def update_task_status(task_id: str, status: str) -> str:
    """Update the status of an existing task in Firestore.

    Args:
        task_id: Unique task identifier (e.g., 'task-1' or 'task-a1b2c3').
        status: New status ('Pending', 'In Progress', 'Completed').

    Returns:
        Confirmation message.
    """
    db = _get_db()
    doc_ref = db.collection("tasks").document(task_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Error: Task with ID '{task_id}' was not found in Firestore."

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    doc_ref.update({"status": status, "updated_at": now})
    return f"Task {task_id} status updated to '{status}' successfully."


def export_productivity_report(report_title: str = "Daily Work Planner Report") -> str:
    """Generate and publish a formatted productivity report to Cloud Storage.

    Args:
        report_title: Title for the generated report.

    Returns:
        Public HTTP URL of the published report.
    """
    from google.cloud import storage

    tasks = list_tasks()
    bucket_name = "work-planner-assets-qwiklabs-gcp-01-0482b2deb94b"

    rows = ""
    for t in tasks:
        rows += f"<tr><td>{t.get('task_id')}</td><td>{t.get('title')}</td><td>{t.get('priority')}</td><td>{t.get('status')}</td><td>{t.get('due_date')}</td></tr>\n"

    html_content = f"""<!Schema html>
<html>
<head>
    <title>{report_title}</title>
    <style>
        body {{ font-family: sans-serif; margin: 2rem; background: #f8f9fa; color: #202124; }}
        h1 {{ color: #1a73e8; }}
        table {{ width: 100%; border-collapse: collapse; background: white; margin-top: 1rem; }}
        th, td {{ padding: 12px; border: 1px solid #dadce0; text-align: left; }}
        th {{ background: #e8f0fe; color: #1967d2; }}
    </style>
</head>
<body>
    <h1>📋 {report_title}</h1>
    <p>Generated at: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    <table>
        <thead>
            <tr><th>Task ID</th><th>Title</th><th>Priority</th><th>Status</th><th>Due Date</th></tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
</body>
</html>"""

    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob("reports/productivity_report.html")
    blob.upload_from_string(html_content, content_type="text/html")

    public_url = f"https://storage.googleapis.com/{bucket_name}/reports/productivity_report.html"
    return f"Productivity report published successfully! View report at: {public_url}"


def get_upcoming_deadlines(days_ahead: int = 3) -> list[dict]:
    """Fetch tasks with upcoming deadlines within the specified number of days.

    Args:
        days_ahead: Maximum number of days from today to consider as upcoming (default 3).

    Returns:
        List of tasks due within days_ahead, enriched with 'days_remaining'.
    """
    tasks = list_tasks()
    today = datetime.date.today()
    upcoming = []

    for task in tasks:
        if task.get("status") == "Completed":
            continue

        due_date_str = task.get("due_date", "")
        if not due_date_str:
            continue

        try:
            due_date = datetime.datetime.strptime(due_date_str, "%Y-%m-%d").date()
            days_remaining = (due_date - today).days

            if days_remaining <= days_ahead:
                task_copy = dict(task)
                task_copy["days_remaining"] = days_remaining
                upcoming.append(task_copy)
        except ValueError:
            continue

    return sorted(upcoming, key=lambda x: x["days_remaining"])


def calculate_workload_analytics() -> dict:
    """Calculate productivity, task completion velocity, and workload metrics.

    Returns:
        Dictionary containing task statistics and estimated remaining effort hours.
    """
    tasks = list_tasks()
    total = len(tasks)
    pending = sum(1 for t in tasks if t.get("status") == "Pending")
    in_progress = sum(1 for t in tasks if t.get("status") == "In Progress")
    completed = sum(1 for t in tasks if t.get("status") == "Completed")
    high_priority = sum(1 for t in tasks if t.get("priority") == "High")

    # Estimated effort hours: High=4h, Medium=2h, Low=1h for non-completed tasks
    effort_map = {"High": 4, "Medium": 2, "Low": 1}
    estimated_remaining_hours = sum(
        effort_map.get(t.get("priority", "Medium"), 2)
        for t in tasks
        if t.get("status") != "Completed"
    )

    completion_rate = round((completed / total * 100), 1) if total > 0 else 0.0

    return {
        "total_tasks": total,
        "pending_tasks": pending,
        "in_progress_tasks": in_progress,
        "completed_tasks": completed,
        "high_priority_tasks": high_priority,
        "completion_rate_pct": completion_rate,
        "estimated_remaining_hours": estimated_remaining_hours,
    }


def get_daily_motivation_quote() -> str:
    """Fetch a live daily motivational/focus quote from ZenQuotes public API.

    Returns:
        String with inspirational quote and author.
    """
    import json
    import os
    import urllib.request

    # Read optional API key from env var if configured
    api_key = os.environ.get("ZENQUOTES_API_KEY", "")
    url = f"https://zenquotes.io/api/random/{api_key}" if api_key else "https://zenquotes.io/api/random"
    headers = {"User-Agent": "WorkPlannerAgent/1.0"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if isinstance(data, list) and len(data) > 0:
                quote = data[0].get("q", "")
                author = data[0].get("a", "Unknown")
                return f'"{quote}" — {author}'
    except Exception:
        pass

    return '"Focus on being productive instead of busy." — Tim Ferriss'


def consult_recipe_corpus(query: str) -> str:
    """Search the grounded Classic Shredded Chicken Salad Recipe corpus and return matched passages.

    Args:
        query: What to look up in the recipe corpus (ingredients, steps, preparation, macros, storage, or serving suggestions).

    Returns:
        The matched passages from the grounded recipe corpus.
    """
    import os

    base_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(base_dir, "..", "data", "chicken_salad_recipe.txt"),
        os.path.join(base_dir, "data", "chicken_salad_recipe.txt"),
        "app/data/chicken_salad_recipe.txt",
        "data/chicken_salad_recipe.txt",
        "/config/Desktop/Session1/work-planner-agent/data/chicken_salad_recipe.txt",
    ]

    text = ""
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
                if text:
                    break
            except Exception:
                pass

    if not text:
        text = (
            "Classic Shredded Chicken Salad Recipe\n"
            "Servings: 4 | Prep Time: 15 mins | Cook Time: 15 mins\n"
            "INGREDIENTS:\n"
            "* 2 large chicken breasts (1 lb / 450g), 4 cups water/broth, 1 tsp salt, 1/2 tsp peppercorns, 1 bay leaf\n"
            "* 2 stalks celery (diced), 1/2 medium red onion (minced), 1/2 cup green grapes (halved), 1/4 cup toasted almonds\n"
            "* 1/2 cup mayonnaise, 1 tbsp Dijon mustard, 1 tbsp lemon juice, 1/2 tsp garlic powder, salt, pepper, 2 tbsp dill/parsley\n"
            "POACHING INSTRUCTIONS:\n"
            "1. Submerge chicken in seasoned liquid in saucepan over medium-high heat.\n"
            "2. Bring to gentle boil, then immediately reduce heat to low, cover, and simmer 12-15 minutes until internal temp is 165°F (74°C).\n"
            "3. Cool for 10 minutes, then shred and fold into mixed dressing and crunch ingredients.\n"
            "ESTIMATED NUTRITION PER SERVING:\n"
            "* Calories: 290 kcal | Protein: 26g | Carbohydrates: 4g | Fat: 19g\n"
        )

    try:
        query_words = [w.lower() for w in query.split() if len(w) > 2]
        sections = text.split("================================================================================")

        matches = []
        for sec in sections:
            sec_lower = sec.lower()
            if any(w in sec_lower for w in query_words):
                matches.append(sec.strip())

        if matches:
            return "\n\n---\n\n".join(matches)
        return text
    except Exception as e:
        return f"Retrieval error: {e}"


def generate_task_image(description: str, tool_context: ToolContext = None) -> str:
    """Generate a visual image illustration for a work planner task or item using gemini-3.1-flash-lite-image.

    Args:
        description: Description of the task or item to generate an image for.
        tool_context: Optional ADK ToolContext for saving image artifacts.

    Returns:
        The public HTTPS URL of the uploaded image in Cloud Storage.
    """
    import uuid
    import google.genai as genai
    from google.genai import types
    from google.cloud import storage

    bucket_name = "work-planner-assets-qwiklabs-gcp-01-0482b2deb94b"
    project_id = "qwiklabs-gcp-01-0482b2deb94b"

    genai_client = genai.Client(vertexai=True, project=project_id, location="global")
    prompt = f"A high-quality minimalist visual illustration for a work task or project item: {description}"

    resp = genai_client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
    )

    part = resp.candidates[0].content.parts[0]
    image_bytes = part.inline_data.data
    mime_type = getattr(part.inline_data, "mime_type", "image/png") or "image/png"

    ext = "png" if "png" in mime_type.lower() else "jpg"
    filename = f"generated_task_{uuid.uuid4().hex[:12]}.{ext}"

    # 1. Save artifact to Playground if tool_context is present
    if tool_context is not None and hasattr(tool_context, "save_artifact"):
        try:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=filename, artifact=artifact_part)
        except Exception:
            pass

    # 2. Upload image bytes directly to public GCS bucket
    object_path = f"generated_images/{filename}"
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(object_path)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{bucket_name}/{object_path}"
    return public_url







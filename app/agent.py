# ruff: noqa
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
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

# Hardcoded Agent Engine and Sandbox resource IDs for sandbox execution
AGENT_ENGINE_RESOURCE = "projects/15860563349/locations/us-east1/reasoningEngines/8511427262753538048"
SANDBOX_RESOURCE = "projects/15860563349/locations/us-east1/reasoningEngines/8511427262753538048/sandboxEnvironments/3903301462976888832"

code_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name=SANDBOX_RESOURCE,
    agent_engine_resource_name=AGENT_ENGINE_RESOURCE,
)


from app.tools.firestore_tools import (
    calculate_workload_analytics,
    consult_recipe_corpus,
    create_task,
    export_productivity_report,
    generate_task_image,
    get_daily_motivation_quote,
    get_upcoming_deadlines,
    list_tasks,
    update_task_status,
)


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None


from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from app.a2ui_utils import a2ui_callback

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description="You are a dedicated Personal Work Planner assistant.",
    workflow_description="Analyze the task or request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction + "\n\n" + (
        "Specific Domain Rules:\n"
        "1. You manage the user's tasks using your Firestore task tools (`list_tasks`, `create_task`, `update_task_status`).\n"
        "2. Whenever the user asks about upcoming deadlines, call `get_upcoming_deadlines()`.\n"
        "3. Whenever the user requests workload statistics, analytics, or capacity estimates, call `calculate_workload_analytics()`.\n"
        "4. Whenever the user requests to publish or export a productivity report, call `export_productivity_report()`.\n"
        "5. Whenever the user seeks a daily motivational quote, focus inspiration, or daily kickoff advice, call `get_daily_motivation_quote()`.\n"
        "6. Whenever the user asks recipe, meal preparation, or food questions (e.g. shredded chicken salad ingredients, steps, macros), call `consult_recipe_corpus()` to retrieve and answer from the recipe corpus.\n"
        "7. Whenever the user asks to generate, visualize, or create an image/illustration for a task or item, call `generate_task_image()`.\n"
        "8. Whenever complex mathematical, data processing, or custom calculations are needed, write and execute Python code using your sandbox code executor.\n"
        "9. Use your preloaded memories and long-term memory bank to remember user habits, preferences, and work context across sessions."
    ),
    code_executor=code_executor,
    tools=[
        get_weather,
        get_current_time,
        PreloadMemoryTool(),
        list_tasks,
        create_task,
        update_task_status,
        export_productivity_report,
        get_upcoming_deadlines,
        calculate_workload_analytics,
        get_daily_motivation_quote,
        consult_recipe_corpus,
        generate_task_image,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)

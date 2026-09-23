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
import subprocess
from google.cloud import firestore
import google.auth
import google.oauth2.credentials

# HARDCODED GCP PROJECT ID as required by Agent Platform
PROJECT_ID = "qwiklabs-gcp-01-0482b2deb94b"


def get_firestore_client():
    try:
        token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
        if token:
            creds = google.oauth2.credentials.Credentials(token)
            return firestore.Client(project=PROJECT_ID, credentials=creds)
    except Exception:
        pass
    return firestore.Client(project=PROJECT_ID)


def seed_database():
    db = get_firestore_client()
    tasks_ref = db.collection("tasks")

    sample_tasks = [
        {
            "task_id": "task-1",
            "title": "Finalize Q4 Architecture Proposal",
            "description": "Draft baseline specs for Agent Runtime integration and memory bank.",
            "priority": "High",
            "status": "In Progress",
            "due_date": "2026-09-26",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "task_id": "task-2",
            "title": "Review Security & IAM Roles",
            "description": "Audit service account permissions and Secret Manager bindings.",
            "priority": "High",
            "status": "Pending",
            "due_date": "2026-09-25",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "task_id": "task-3",
            "title": "Setup Daily Standup Updates",
            "description": "Configure automated task progress summaries and notifications.",
            "priority": "Medium",
            "status": "Pending",
            "due_date": "2026-09-28",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    ]

    for task in sample_tasks:
        tasks_ref.document(task["task_id"]).set(task)
        print(f"Seeded task: {task['task_id']} ({task['title']})")


if __name__ == "__main__":
    seed_database()

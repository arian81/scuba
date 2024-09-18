import json
from typing import List
from todoist_api_python.api import TodoistAPI
from textblob import TextBlob
import spacy
from dotenv import load_dotenv
import os

load_dotenv()

# python -m spacy download en_core_web_sm

# Load the spaCy English model
nlp = spacy.load("./en_core_web_sm-3.7.1/en_core_web_sm/en_core_web_sm-3.7.1")


def prioritize_emails_to_todoist(emails: List[dict]) -> str:

    print("EMAILSSSSSSSSSSSSSSSSS", emails)
    # Initialize Todoist client
    api = TodoistAPI(os.environ["TODOIST_API_TOKEN"])

    # Create a new project
    project = api.add_project(name="Prioritized Tasks")

    for email in emails:
        subject = email["subject"]
        snippet = email["snippet"]
        content = f"{subject}\n\n{snippet}"

        # Perform sentiment analysis
        blob = TextBlob(content)
        sentiment = blob.sentiment.polarity

        # Perform NER
        doc = nlp(content)
        entities = [ent.label_ for ent in doc.ents]

        # Determine priority based on sentiment, entities, and keywords
        priority = determine_priority(sentiment, entities, content)

        # Create a task with the email content
        task_content = f"[{email['sender']['name']}] {subject}"
        task_description = f"From: {email['sender']['email']}\n\n{snippet}"
        due_date = email["due_date"]

        # Map our priority to Todoist priority (4 is highest, 1 is lowest)
        todoist_priority = 4 if priority == "high" else 3 if priority == "medium" else 2

        api.add_task(
            content=task_content,
            description=task_description,
            project_id=project.id,
            priority=todoist_priority,
            due_date=due_date,
        )

    return f"https://todoist.com/app/project/{project.id}"


def determine_priority(sentiment: float, entities: List[str], content: str) -> str:
    # Priority keywords
    high_priority_keywords = ["urgent", "important", "deadline", "asap"]
    medium_priority_keywords = ["meeting", "project", "report"]

    # Check for high priority indicators
    if any(keyword in content.lower() for keyword in high_priority_keywords):
        return "high"
    if sentiment < -0.3 or "ORG" in entities or "PERSON" in entities:
        return "high"

    # Check for medium priority indicators
    if any(keyword in content.lower() for keyword in medium_priority_keywords):
        return "medium"
    if -0.3 <= sentiment < 0.3:
        return "medium"

    # Default to low priority
    return "low"

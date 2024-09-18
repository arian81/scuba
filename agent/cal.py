import re
from datetime import datetime, timedelta
from typing import List, Tuple
from googleapiclient.errors import HttpError

import dateutil.parser
from dateutil.tz import tzlocal
from auth import google_auth

import logging

# If modifying these scopes, delete the file token.json.
# SCOPES = ['https://www.googleapis.com/auth/calendar']


def extract_time_slots(email_content: str) -> List[Tuple[datetime, datetime]]:
    # Regular expression to match date and time ranges
    pattern = r"(\w+), (\w+ \d{1,2}): ([\d:]+\s*(?:AM|PM))\s*-\s*([\d:]+\s*(?:AM|PM))"
    matches = re.findall(pattern, email_content)

    time_slots = []
    for match in matches:
        day, date, start_time, end_time = match
        year = datetime.now().year
        full_date = f"{day} {date} {year}"

        start_datetime = dateutil.parser.parse(f"{full_date} {start_time}")
        end_datetime = dateutil.parser.parse(f"{full_date} {end_time}")

        time_slots.append((start_datetime, end_datetime))

    return time_slots


def get_free_slot(
    time_slots: List[Tuple[datetime, datetime]], duration: timedelta
) -> Tuple[datetime, datetime]:
    for start, end in time_slots:
        # Ensure start and end are timezone-aware
        start = start.replace(tzinfo=tzlocal()) if start.tzinfo is None else start
        end = end.replace(tzinfo=tzlocal()) if end.tzinfo is None else end

        # Convert to RFC3339 timestamp
        time_min = start.isoformat()
        time_max = end.isoformat()

        _, service = google_auth()

        try:
            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=10,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])

            if not events:
                # No events, so the entire slot is free
                return (start, start + duration)

            # Check for gaps between events
            current_time = start
            for event in events:
                event_start = datetime.fromisoformat(
                    event["start"].get("dateTime", event["start"].get("date"))
                )
                event_start = (
                    event_start.replace(tzinfo=tzlocal())
                    if event_start.tzinfo is None
                    else event_start
                )
                if current_time + duration <= event_start:
                    return (current_time, current_time + duration)
                event_end = datetime.fromisoformat(
                    event["end"].get("dateTime", event["end"].get("date"))
                )
                event_end = (
                    event_end.replace(tzinfo=tzlocal())
                    if event_end.tzinfo is None
                    else event_end
                )
                current_time = max(current_time, event_end)

            # Check after the last event
            if current_time + duration <= end:
                return (current_time, current_time + duration)

        except HttpError as error:
            logging.error(f"An error occurred: {error}")
            continue

    return None  # No free slot found


def schedule_meeting(email_content: str, sender_email: str, calendar_id: str) -> str:
    """Schedule a meeting using google calendar"""
    time_slots = extract_time_slots(email_content)
    meeting_duration = timedelta(minutes=30)

    free_slot = get_free_slot(time_slots, meeting_duration)

    if not free_slot:
        return "No suitable time slot found."

    start_time, end_time = free_slot

    event = {
        "summary": f"Meeting with {sender_email}",
        "description": "Automatically scheduled meeting from email request.",
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "America/New_York",
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "America/New_York",
        },
        "attendees": [
            {"email": sender_email},
        ],
    }

    try:
        _, service = google_auth()
        event = (
            service.events()
            .insert(calendarId=calendar_id, body=event, sendUpdates="all")
            .execute()
        )
        return f"Meeting scheduled for {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%H:%M')}. Calendar invite sent."
    except HttpError as error:
        print(f"An error occurred: {error}")


# def main():
#     # google_auth()
#     # Example usage
#     email_content = """
#     Hi Vishakh.
#     I hope you are doing well.
#     My name is Morgan Lella, and I am a sophomore studying Economics and Mathematics. I would appreciate the opportunity to speak with you and learn more about your experience in B&F.
#     My general availability is as follows, but my schedule is flexible with yours.
#     Monday, September 16: 4:15 PM - 5:30 PM
#     Tuesday, September 17: 9:30 PM - 10:30 PM
#     Wednesday, September 18: 9:30 AM - 12:00 PM, after 4:00 PM
#     Thursday, September 19: 8:00 AM - 10:30 AM, after 4:00 PM
#     Friday, September 20: After 11:30 AM
#     Best regards,
#     Morgan Lella
#     --
#     Morgan Lella
#     New York University '27
#     B.S. Economics and Mathematics
#     ml8650@nyu.edu | LinkedIn | (914) 414-1082
#     """

#     sender_email = "mlx8650@nyu.edu"

#     _, service = google_auth()
#     calendar_id = "vs2800@nyu.edu"

#     result = schedule_meeting(service, email_content, sender_email, calendar_id)
#     print(result)


# if __name__ == "__main__":
#     main()  # Call the main function to execute the code

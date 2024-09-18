import os

import base64
from auth import google_auth


# If modifying these scopes, delete the file token.json.


def get_email_content(service, user_id, msg_id):
    try:
        message = (
            service.users()
            .messages()
            .get(userId=user_id, id=msg_id, format="full")
            .execute()
        )
        headers = {
            header["name"]: header["value"] for header in message["payload"]["headers"]
        }

        parts = message["payload"].get("parts", [])
        body = ""
        for part in parts:
            if part["mimeType"] == "text/plain":
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                break

        attachments = []
        for part in parts:
            if "filename" in part and part["filename"]:
                attachment = {
                    "filename": part["filename"],
                    "mimeType": part["mimeType"],
                    "headers": part.get("headers", []),
                }

                # Download attachment
                if "body" in part and "attachmentId" in part["body"]:
                    att_id = part["body"]["attachmentId"]
                    att = (
                        service.users()
                        .messages()
                        .attachments()
                        .get(userId=user_id, messageId=msg_id, id=att_id)
                        .execute()
                    )
                    file_data = base64.urlsafe_b64decode(att["data"].encode("UTF-8"))

                    # Create a 'downloads' directory if it doesn't exist
                    if not os.path.exists("downloads"):
                        os.makedirs("downloads")

                    # Save the file
                    file_path = os.path.join("downloads", part["filename"])
                    with open(file_path, "wb") as f:
                        f.write(file_data)

                    # Store the local file path instead of the attachment link
                    attachment["local_path"] = file_path

                attachments.append(attachment)

        email_data = {
            "content": body,
            "attachments": attachments,
            # "id": message["id"],
            "sender": {
                "name": headers.get("From", "").split("<")[0].strip(),
                "email": headers.get("From", "").split("<")[-1].rstrip(">"),
            },
            # "recipients": headers.get("To", "").split(","),
            # "cc": headers.get("Cc", "").split(",") if "Cc" in headers else [],
            "subject": headers.get("Subject", ""),
            "snippet": message["snippet"],
            # "payload": {
            #     "partId": message["payload"].get("partId", ""),
            #     "mimeType": message["payload"]["mimeType"],
            #     "filename": message["payload"].get("filename", ""),
            #     "content": body,
            #     "headers": [f"{k}:{v}" for k, v in headers.items()],
            #     "parts": attachments,
            # },
        }
        return email_data
    except Exception as error:
        print(f"An error occurred: {error}")
        return None


def run_email():
    gmail_service, _ = google_auth()
    user_id = "me"

    labels = gmail_service.users().labels().list(userId=user_id).execute()
    label_id = next(
        (label["id"] for label in labels["labels"] if label["name"] == "interaction"),
        None,
    )

    if not label_id:
        print("Label interaction not found.")
        return []

    results = (
        gmail_service.users()
        .messages()
        .list(userId=user_id, labelIds=[label_id])
        .execute()
    )
    messages = results.get("messages", [])

    if not messages:
        print("No messages found.")
    else:
        print("Messages:")
        data = []
        for message in messages:
            email_data = get_email_content(gmail_service, user_id, message["id"])
            if email_data:
                data.append(email_data)
    return data


print(run_email())

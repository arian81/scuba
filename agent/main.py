import PIL
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI
from llama_index.core.agent import ReActAgent
from pdf2image import convert_from_path
from pypdf import PdfReader, PdfWriter
from typing import List, Dict, Any, Annotated
import difflib
import subprocess
from get_emails import run_email
from email_priority import prioritize_emails_to_todoist
from controls.codeagents import (
    read_pull,
    post_comment_to_pr,
    find_commit_sha_by_code_segment,
)
from controls.docvision import (
    encode_images,
    create_content,
    get_openai_response,
    get_bounding_boxes,
    match_boxes,
    place_answers_on_image,
)
from fastapi import FastAPI
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from cal import schedule_meeting
from llama_index.core import set_global_handler
import sys
import asyncio
from contextlib import redirect_stdout
from io import StringIO

# Function to capture output in real-time
class CapturingOutput(StringIO):
    def __init__(self, websocket=None):
        super().__init__()
        self.websocket = websocket

    def write(self, s):
        super().write(s)
        # Send output to WebSocket in real-time
        if self.websocket:
            asyncio.create_task(self.websocket.send_text(s.strip()))

todos = []


def get_data() -> str:
    """returns the data needed to fill out a pdf file"""
    return """Vehicle/Vessel Description:
Identification Number: 1HGCM82633A123456
Year Model: 2015
Make: Toyota
License Plate or CF #: ABC1234
Motorcycle Engine #: (Leave blank if not a motorcycle)
Seller Information:
Seller's Name: John Doe
Date of Sale: 09/14/2024
Selling Price: $15,000
Gift Value: (Leave blank if not a gift)
Seller's Certification:
Seller's Name: John Doe
Signature: John Doe
Date: 09/14/2024
DL, ID, or Dealer #: D1234567 (if applicable)
Mailing Address:
City: Los Angeles
State: CA
Zip: 90001
Daytime Phone Number: (310) 555-1234
Buyer Information:
Buyer's Name: Jane Smith
Mailing Address:
City: San Francisco
State: CA
Zip: 94105
"""


def get_fields(pdf_name: str) -> List[str]:
    """returns fields needed to fill out a pdf file"""
    reader = PdfReader(pdf_name)
    fields = reader.get_fields()

    return list(fields)


def fill_pdf(pdf_name: str, data: Dict[str, str]) -> str:
    """Fills out a pdf file with the given data in the form of a dictionary of field names and values"""
    reader = PdfReader(pdf_name)
    writer = PdfWriter()

    # page = reader.pages[0]
    fields = reader.get_fields()

    writer.append(reader)

    print("DATA:", data)
    for field in fields:
        try:
            writer.update_page_form_field_values(
                writer.pages[0],
                {field: data[field]},
                auto_regenerate=False,
            )
        except Exception:
            continue

    with open("output.pdf", "wb") as output_file:
        writer.write(output_file)
    return "pdf filled and saved to output.pdf"


def open_pdf(pdf_name: str) -> str:
    """opens pdf file using system default pdf reader"""
    subprocess.run(["open", pdf_name])
    return "file opened. Done processing the pdf."


def add_todo(todo: str) -> str:
    """add todo to a global variable"""
    todos.append(todo)
    return f"todo added to todos: {todo}"


def images_to_pdf(input_data: List[Any], output_path: str) -> None:
    """Convert an array of images into a pdf and writes it"""
    # Convert all images to RGB mode (PDF requires RGB mode)
    rgb_images = [img.convert("RGB") for img in input_data]
    print(input_data)
    # Save the first image and append the rest as additional pages
    rgb_images[0].save(
        output_path,
        save_all=True,
        append_images=rgb_images[1:],
        resolution=100.0,
        quality=95,
        optimize=True,
    )


def load_pdf_to_image(pdf_name: str) -> Dict[str, Any]:
    """Loads pdf to an array of images"""
    images = convert_from_path(pdf_name)
    encoded_images = encode_images(images)

    return {"images": images, "encoded": encoded_images}


def get_fields_from_image(pdf_name: str) -> List[str]:
    """returns fields needed to fill out a pdf file if the pdf consists of images only"""
    img_obj = load_pdf_to_image(pdf_name)
    content = create_content(
        img_obj["encoded"],
        "List all of the form field names as written on the document. Output it "
        "in a comma separated list. Don't bullet or enumerate.",
    )
    response = get_openai_response(content)
    return response.split(", ")


def fill_pdf_via_image(pdf_name: str, data: Dict[str, str]) -> str:
    """Fills out a pdf composing of images with the given data in the form of a dictionary of field names and values"""
    print("Data: ", data)
    img_obj = load_pdf_to_image(pdf_name)
    images = img_obj["images"]
    fields = get_fields_from_image(pdf_name)
    page_list = []
    for page in images:
        bounding_boxes = get_bounding_boxes(page)
        prompts, coords = match_boxes(bounding_boxes, fields)

        answers = []
        try:
            for p in prompts:
                matched = False
                for data_key in data.keys():
                    r = difflib.SequenceMatcher(None, p, data_key).ratio()
                    if r >= 0.7:
                        answers.append(data[data_key])
                        matched = True
                        break
                if not matched:
                    answers.append("")
        except Exception:
            continue

        new_page = place_answers_on_image(page, answers, coords)
        print("Appending...")
        page_list.append(new_page)
    images_to_pdf(page_list, "output.pdf")
    return "success, written to output.pdf"


get_fields_function = FunctionTool.from_defaults(fn=get_fields)
get_data_function = FunctionTool.from_defaults(fn=get_data)
fill_pdf_function = FunctionTool.from_defaults(fn=fill_pdf)
open_pdf_function = FunctionTool.from_defaults(fn=open_pdf)
add_todo_function = FunctionTool.from_defaults(fn=add_todo)
images_to_pdf_function = FunctionTool.from_defaults(fn=images_to_pdf)
get_fields_from_image_function = FunctionTool.from_defaults(fn=get_fields_from_image)
fill_pdf_via_image_function = FunctionTool.from_defaults(fn=fill_pdf_via_image)
read_pull_function = FunctionTool.from_defaults(fn=read_pull)
find_commit_sha_by_code_segment_function = FunctionTool.from_defaults(
    fn=find_commit_sha_by_code_segment
)
post_comment_to_pr_function = FunctionTool.from_defaults(fn=post_comment_to_pr)
prioritize_emails_to_todoist_function = FunctionTool.from_defaults(
    fn=prioritize_emails_to_todoist
)
schedule_meeting_function = FunctionTool.from_defaults(fn=schedule_meeting)

# initialize llm
llm = OpenAI(model="gpt-4o")

# initialize ReAct agent
agent = ReActAgent.from_tools(
    [
        get_fields_function,
        get_data_function,
        fill_pdf_function,
        open_pdf_function,
        add_todo_function,
        images_to_pdf_function,
        get_fields_from_image_function,
        fill_pdf_via_image_function,
        read_pull_function,
        post_comment_to_pr_function,
        find_commit_sha_by_code_segment_function,
        schedule_meeting_function,
    ],
    llm=llm,
    verbose=True,
    max_iterations=10,
)

app = FastAPI()

# Store connected clients in a list
clients = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        await websocket.send_text("Worker 1 has started...")
        emails = run_email()

        # Start the email processing with WebSocket logging
        await process_emails(agent, emails, websocket)
        if len(todos) != 0:
            prioritize_emails_to_todoist(todos)
    except WebSocketDisconnect:
        clients.remove(websocket)
        print("Client disconnected")


# Function to broadcast logs to all connected WebSocket clients
async def broadcast_log(log_message: str):
    for client in clients:
        await client.send_text(log_message)


async def process_emails(agent, emails, websocket):
    for email in emails:
        try:
            await broadcast_log(f"Processing email from {email['sender']}")
            email_content = f"""
                        email body: {email['content']}
                        email attachments: {email['attachments']}
                        email sender: {email['sender']}
                        email subject: {email['subject']}
                        Based on the email above, do one of the following tasks:
                        1. Download the attachment, fill out the pdf with appropriate function (if there's no fields use image-related functions), and open the edited version.
                        2. Add the email as a dictionary to the todo list. Dictionary should have the following keys: subject, sender, snippet, due_date. Summarize the body.
                        3. Schedule a meeting with the sender of the email if the email has timeslots instead of todo tasks.
                        4. Review the pull-request and suggest any changes to make before merging. Write code suggestions to GitHub as a comment.
                        """
            # Redirect stdout to capture agent's output in real-time
            with CapturingOutput(websocket=websocket) as output_buffer:
                with redirect_stdout(output_buffer):
                    # Run the agent and capture output in real-time
                    agent.chat(email_content)
        except Exception as e:
            await websocket.send_text(f"Error processing email: {str(e)}")


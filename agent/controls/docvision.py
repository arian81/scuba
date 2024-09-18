from typing import Dict, List, Any, Tuple

import PIL
from openai import OpenAI
from dotenv import dotenv_values
from pdf2image import convert_from_path
import base64
from io import BytesIO
from PIL import ImageDraw, ImageFont
from google.cloud import vision
import io

config = dotenv_values(".env")
client = OpenAI(api_key=config["OPENAI_API_KEY"])


def encode_images(images):
    base64_images = []
    for i, image in enumerate(images):
        # Save each image
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        img_bytes = buffered.getvalue()

        # Encode bytes to base64
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        base64_images.append(img_base64)
    return base64_images


def create_content(base64_images, text):
    content = [{"type": "text", "text": text}]
    for img in base64_images:
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}}
        )
    return content


def get_openai_response(content):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": content}],
        max_tokens=300,
    )
    return response.choices[0].message.content


def place_answers_on_image(
    image: PIL.Image, answers: List[str], coordinates: List[List[Tuple[int]]]
):
    # Open the image
    draw = ImageDraw.Draw(image)
    img_width, img_height = image.size
    # Load a font
    try:
        font = ImageFont.truetype(
            "./arial.ttf", 30
        )  # You may need to adjust the font path or size
    except IOError:
        print("Error loading font...")
        font = ImageFont.load_default()
    old_answer = ""
    # Place each answer at the specified coordinates
    for answer, coord in zip(answers, coordinates):
        if answer == old_answer:
            continue
        old_answer = answer
        x = coord[0][0]
        y = coord[0][1]
        draw.text((x, y), answer, fill="black", font=font)

    # Save the result
    return image


def match_boxes(boxes, fields):
    prompts = []
    coords = []
    to_skip = 0
    for box in boxes:
        if to_skip != 0:
            to_skip -= 1
            continue
        for field in fields:
            if (
                box["text"].description in field
                and not len(box["text"].description) <= 2
            ):
                prompts.append(field)
                coords.append(box["box"])
                # to_skip = max(len(field.split(" ")) - 1, 0)
                break
    return prompts, coords


def get_bounding_boxes(image):
    vision_client = vision.ImageAnnotatorClient(
        credentials=None, client_options={"api_key": config["GCLOUD"]}
    )

    # Convert the PIL image to a byte stream
    image_byte_array = io.BytesIO()
    image.save(image_byte_array, format="JPEG")  # Ensure to use the right format
    image_byte_array = image_byte_array.getvalue()
    # Use Vision API to detect text
    image = vision.Image(content=image_byte_array)
    response = vision_client.text_detection(image=image)
    texts = response.text_annotations

    # Extract bounding boxes for words (ignore first entry as it contains the entire text block)
    bounding_boxes = []
    for text in texts[1:]:
        box = [(vertex.x, vertex.y) for vertex in text.bounding_poly.vertices]
        bounding_boxes.append({"text": text, "box": box})

    return bounding_boxes

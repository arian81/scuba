# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Create and activate a virtual environment
RUN python -m venv /app/venv

# Install any needed packages specified in requirements.txt
RUN /app/venv/bin/pip install --upgrade pip
RUN /app/venv/bin/pip install -r requirements.txt

# Command to run your app (db.py)
CMD ["/bin/bash", "-c", "/app/venv/bin/python db.py && /app/venv/bin/python query.py 'What is this user's name?'"]

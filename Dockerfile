# Use an official Python runtime as a base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN apt-get update && apt-get install -y gcc libssl-dev libffi-dev \
    && pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . /app/

# Command to run the bot
CMD ["python", "meow.py"]

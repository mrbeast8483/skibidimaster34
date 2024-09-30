# Use a minimal Python runtime as a base image
FROM python:3.11-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Install dependencies (gcc, g++, and necessary libraries)
RUN apk add --no-cache gcc g++ libffi-dev openssl-dev python3-dev musl-dev make

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . /app/

# Command to run the bot
CMD ["python", "meow.py"]

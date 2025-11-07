# Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
# psycopg2-binary pre-compiles this, but it's good practice for other libraries
# RUN apt-get update && apt-get install -y build-essential

# Install dependencies
# We copy our requirements file first to leverage Docker's cache.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . .
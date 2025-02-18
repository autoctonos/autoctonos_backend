# Stage 1: Base build stage
FROM python:3.13-slim AS builder
 
# Set the working directory
WORKDIR /app

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 

# Upgrade pip and install dependencies
RUN pip install --upgrade pip 

# Copy the requirements file first (better caching)
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code (this is missing in your original Dockerfile)
COPY . /app/

# Expose Django development server port
EXPOSE 8000 

# Start the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--noreload"]

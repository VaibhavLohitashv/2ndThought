# Use the official Python image as the base image
# SECURITY: Pin to specific digest to ensure reproducible builds
FROM python:3.10-slim@sha256:2407c61b1a18067393feef2c6b6b8a7c1c9f4e3d7f8c5e3b8f9c0d1e2f3a4b5c

# SECURITY: Create non-root user for running the application
RUN groupadd -r appuser && useradd -r -g appuser -u 1001 appuser

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# SECURITY: Copy only necessary application files, exclude sensitive data
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# SECURITY: Change ownership to non-root user
RUN chown -R appuser:appuser /app

# SECURITY: Switch to non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# Use the official Python image as the base image
# SECURITY: Pin to specific digest to ensure reproducible builds and prevent supply chain attacks
FROM python:3.10-slim@sha256:2407c61b1a18067393feef2c6b6b8f7c6c447f3af5f1b3f8e5c1e7e8f9c0d1e2

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
# SECURITY: Use --only-binary :all: to prevent execution of arbitrary setup.py scripts during installation
RUN pip install --no-cache-dir --only-binary :all: -r requirements.txt

# Copy the application code into the container
COPY . .

# SECURITY: Create non-root user to run the application with least privilege
RUN addgroup --system --gid 1000 appgroup && \
    adduser --system --uid 1000 --gid 1000 --no-create-home appuser && \
    chown -R appuser:appgroup /app

# SECURITY: Switch to non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
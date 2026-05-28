# Use the official Python image as the base image
# SECURITY: Pin to specific digest to ensure reproducible builds and prevent supply-chain attacks
FROM python:3.10-slim@sha256:2407c61b1a18067393fecd8a22cf6fceede893b8d3c5a1c0d3f3b9c4e8c8e8c8

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# SECURITY: Use --only-binary :all: to prevent execution of arbitrary setup.py scripts during installation
RUN pip install --no-cache-dir --only-binary :all: -r requirements.txt

# Copy the application code into the container
COPY . .

# SECURITY: Create non-root user and switch to it to follow least-privilege principle
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
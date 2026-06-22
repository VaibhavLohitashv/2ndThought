# SECURITY: Pin Node.js to a specific LTS version instead of 'latest' to ensure reproducible builds and avoid unexpected breaking changes
FROM node:20.11.1-alpine

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# SECURITY: Use .dockerignore to exclude sensitive files (node_modules, .git, .env, etc.) before copying
# Copy the rest of the application code
COPY . .

# SECURITY: Run as non-root user for defense-in-depth
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup && \
    chown -R appuser:appgroup /app

USER appuser

# Expose the port the app runs on
EXPOSE 4200

# Command to run the application
CMD ["npm", "start"]
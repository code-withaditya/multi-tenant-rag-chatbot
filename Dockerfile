FROM python:3.10-slim

WORKDIR /app

# Install system dependencies needed for building certain Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Force the frontend to look at the local backend inside the same container
ENV BACKEND_URL=http://127.0.0.1:8000

# Give Windows permission to execute our startup script
RUN chmod +x start.sh

# Expose the precise port that Hugging Face expects
EXPOSE 7860

# Run our orchestration script to boot both apps together
CMD ["./start.sh"]
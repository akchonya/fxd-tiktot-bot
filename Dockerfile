FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for pyktok and browser automation
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y \
    google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot code
COPY main.py .

# Environment variables will be passed when running the container
# using docker run -e BOT_TOKEN=your_token -e ADMIN_ID=your_id

# Run the bot
CMD ["python", "main.py"] 
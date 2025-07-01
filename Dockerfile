# Use an official Python runtime
FROM selenium/standalone-chrome:latest AS base_image

USER root

# RUN apt-get update && apt-get install -y \
#     wget unzip curl gnupg \
#     chromium-driver \
#     chromium \
#     && rm -rf /var/lib/apt/lists/*

# FROM base_image AS pip_image

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base_image AS final_image
# FROM pip_image AS final_image
# Copy application code
COPY . .

# Expose port if needed (adjust based on your Flask app)
EXPOSE 5002

# Run the bot
CMD ["gunicorn", "--bind", "0.0.0.0:5002", "main:app"]

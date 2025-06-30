# Use an official Python runtime
FROM selenium/standalone-chrome AS base_image

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port if needed (adjust based on your Flask app)
EXPOSE 5002

# Run the bot
CMD ["gunicorn", "--bind", "0.0.0.0:5002", "main:app"]

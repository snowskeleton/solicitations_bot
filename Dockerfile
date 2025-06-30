# Use an official Python runtime
FROM selenium/standalone-chrome AS base_image

USER root
# Set work directory
WORKDIR /app
# Copy application code
COPY . .
RUN chown -R seluser:seluser /app
RUN chmod 644 /app/solicitations.db

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set user expected by Selenium
USER seluser

# Expose port if needed (adjust based on your Flask app)
EXPOSE 5002

# Run the bot
CMD ["gunicorn", "--bind", "0.0.0.0:5002", "main:app"]

# Solicitations Bot
This program checks government websites for open solicitation requests and emails the user based on filters and a schedule


## Setup
Clone this repo
`git clone https://github.com/snowskeleton/solicitations_bot.git`
Setup your application secrets
```
cp example.env.py env.py
vi env.py
```
```
# email configuration -- check your email vendors instructions for what these values should be
SMTP_SERVER = ""
SMTP_PORT = 587
SMTP_USERNAME = ""
SMTP_PASSWORD = ""
FROM_ADDRESS = ""

# General configuration
ADMIN_EMAIL = ""  # Used for the first login to add other users
MAGIC_LINK_EXPIRY_SECONDS = 300  # 5 minutes
COOKIE_SECRET = "your-secret-key"  # Replace with a secure random key

URI = "https://yourdomain.com"  # Replace with your actual domain
```

Start with Docker
`docker compose up -d`

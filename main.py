import urllib3

from env import ADMIN_EMAIL
from routes import app
from storage import setup_db, add_user


if __name__ == "__main__":
    # Suppress SSL warnings for self-signed certs
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    setup_db()
    add_user(ADMIN_EMAIL, is_admin=True)
    app.run(host="0.0.0.0", port=5002, debug=True)

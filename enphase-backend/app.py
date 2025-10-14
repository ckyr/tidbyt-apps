from flask import Flask, jsonify
import requests
import os
import time

app = Flask(__name__)

# Environment variables (set in Render dashboard)
CLIENT_ID = os.getenv("ENPHASE_CLIENT_ID")
CLIENT_SECRET = os.getenv("ENPHASE_CLIENT_SECRET")
SYSTEM_ID = os.getenv("ENPHASE_SYSTEM_ID")
ACCESS_TOKEN = os.getenv("ENPHASE_ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("ENPHASE_REFRESH_TOKEN")

# Token expiration tracking (simple runtime storage)
TOKEN_EXPIRES_AT = 0


def refresh_access_token():
    global ACCESS_TOKEN, TOKEN_EXPIRES_AT, REFRESH_TOKEN
    url = "https://api.enphaseenergy.com/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print("Error refreshing token:", response.text)
        return False

    data = response.json()
    ACCESS_TOKEN = data["access_token"]
    REFRESH_TOKEN = data.get("refresh_token", REFRESH_TOKEN)
    TOKEN_EXPIRES_AT = time.time() + data.get("expires_in", 3600)
    print("Access token refreshed successfully.")
    return True


def fetch_summary():
    """Fetch system production and consumption from Enphase API"""
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    summary_url = f"https://api.enphaseenergy.com/api/v4/systems/{SYSTEM_ID}/summary"

    resp = requests.get(summary_url, headers=headers)
    if resp.status_code != 200:
        print("Error fetching summary:", resp.text)
        return None

    return resp.json()


@app.route("/enphase_summary")
def enphase_summary():
    global TOKEN_EXPIRES_AT

    # Refresh token if expired
    if time.time() >= TOKEN_EXPIRES_AT:
        refresh_access_token()

    data = fetch_summary()
    if not data:
        return jsonify({"error": "Failed to load Enphase data"}), 500

    # Parse Enphase JSON safely
    prod = data.get("production", {})
    cons = data.get("consumption", {})

    result = {
        "production": {
            "today": prod.get("today", 0),
            "month": prod.get("month_to_date", 0),
            "year": prod.get("year_to_date", 0),
            "lifetime": prod.get("lifetime", 0)
        },
        "consumption": {
            "today": cons.get("today", 0),
            "month": cons.get("month_to_date", 0),
            "year": cons.get("year_to_date", 0),
            "lifetime": cons.get("lifetime", 0)
        }
    }
    return jsonify(result)


@app.route("/")
def home():
    return "✅ Enphase backend running."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

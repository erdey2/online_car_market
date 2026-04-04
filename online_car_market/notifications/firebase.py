import os
import json
import firebase_admin
from firebase_admin import credentials


def init_firebase():
    firebase_json = os.getenv("FIREBASE_CREDENTIALS_JSON")

    if not firebase_json:
        print("Firebase not configured")
        return

    try:
        # Convert JSON string → dict
        cred_dict = json.loads(firebase_json)

        # Create temp file
        temp_path = "/tmp/firebase.json"

        with open(temp_path, "w") as f:
            json.dump(cred_dict, f)

        cred = credentials.Certificate(temp_path)

        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)

    except Exception as e:
        print(f"Firebase init failed: {e}")

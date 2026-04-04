import os, json, base64
import firebase_admin
from firebase_admin import credentials

def init_firebase():
    if not firebase_admin._apps:
        b64 = os.getenv("FIREBASE_CREDENTIALS_B64")

        if not b64:
            print("Firebase not configured")
            return

        decoded = base64.b64decode(b64).decode("utf-8")
        cred_dict = json.loads(decoded)

        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)

        print("Firebase initialized")

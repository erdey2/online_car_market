import os
import json
import base64
import firebase_admin
from firebase_admin import credentials

def init_firebase():
    if firebase_admin._apps:
        print("Firebase already initialized")
        return

    b64 = os.getenv("FIREBASE_CREDENTIALS_B64")

    if not b64:
        raise ValueError("FIREBASE_CREDENTIALS_B64 not found")

    try:
        decoded = base64.b64decode(b64)
        service_account_info = json.loads(decoded)

        cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)

        print("Firebase initialized successfully")

    except Exception as e:
        print("Firebase init failed")
        print(str(e))

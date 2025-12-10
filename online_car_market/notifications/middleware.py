from urllib.parse import parse_qs
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import close_old_connections
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

User = get_user_model()

@database_sync_to_async
def get_user_for_token(token):
    try:
        validated_token = UntypedToken(token)
        user = JWTAuthentication().get_user(validated_token)
        return user
    except Exception:
        return AnonymousUser()

class TokenAuthMiddleware(BaseMiddleware):
    """
    Token auth middleware for channels. Expects token in querystring like ?token=<jwt>
    """
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token = params.get("token")
        if token:
            token = token[0]
            scope["user"] = await get_user_for_token(token)
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)

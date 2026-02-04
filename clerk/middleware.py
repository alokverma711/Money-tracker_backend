import jwt
from django.conf import settings
from rest_framework import authentication, exceptions

class ClerkAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        try:
            token = auth_header.split()[1]
            # Use jwt.decode with options to bypass key verification for local dev
            payload = jwt.decode(token, options={"verify_signature": False})
            user_id = payload.get('sub')
            
            if not user_id:
                return None

            class ClerkUser:
                def __init__(self, uid):
                    self.id = uid  # This is the string "user_2N..."
                    self.is_authenticated = True
                def is_active(self): return True

            return (ClerkUser(user_id), None)
        except Exception as e:
            print(f"DEBUG: JWT Error -> {e}")
            return None

class ClerkMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("--- MIDDLEWARE TRIGGERED ---")
        
        request.clerk_user = None 

        auth_header = request.headers.get('Authorization')
        print(f"DEBUG: Authorization Header present: {bool(auth_header)}")

        if auth_header:
            try:
                auth_res = ClerkAuthentication().authenticate(request)
                if auth_res:
                    request.clerk_user = auth_res[0]
                    request.user = auth_res[0]
                    print(f"DEBUG: Successfully attached Clerk User: {request.clerk_user.id}")
            except Exception as e:
                print(f"DEBUG: Auth failed inside middleware: {e}")
            
        return self.get_response(request)
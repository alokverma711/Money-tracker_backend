
from django.http import HttpResponse

class ForceCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin")
        allow_origin = origin if origin else "*"

        if request.method == "OPTIONS":
            response = HttpResponse()
        else:
            response = self.get_response(request)

        response["Access-Control-Allow-Origin"] = allow_origin
        response["Access-Control-Allow-Credentials"] = "true"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, Origin, X-Requested-With, X-CSRFToken"
        response["Access-Control-Max-Age"] = "600"
        return response

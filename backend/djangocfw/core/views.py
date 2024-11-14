from django.http import JsonResponse
from django.utils import timezone

def health_check(request):
    return JsonResponse({
        "status": "healthy",
        "timestamp": timezone.now().isoformat()
    })
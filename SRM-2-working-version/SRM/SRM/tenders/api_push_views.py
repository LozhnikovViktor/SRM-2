from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import PushSubscription


@api_view(['GET'])
@permission_classes([AllowAny])
def get_vapid_public_key(request):
    return Response({
        'public_key': settings.VAPID_PUBLIC_KEY_RAW
    })


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def subscribe_push(request):
    try:
        data = request.data
        endpoint = data.get('endpoint')
        keys = data.get('keys', {})
        
        if not endpoint or not keys.get('auth') or not keys.get('p256dh'):
            return Response(
                {'error': 'Missing required fields'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        subscription, created = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'auth': keys['auth'],
                'p256dh': keys['p256dh']
            }
        )
        
        return Response({
            'status': 'subscribed',
            'created': created
        })
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def unsubscribe_push(request):
    try:
        endpoint = request.data.get('endpoint')
        if not endpoint:
            return Response(
                {'error': 'Missing endpoint'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        PushSubscription.objects.filter(endpoint=endpoint).delete()
        return Response({'status': 'unsubscribed'})
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

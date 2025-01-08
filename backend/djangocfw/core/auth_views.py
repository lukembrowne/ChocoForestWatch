from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
import random
import string
import os
import logging
from .serializers import UserSerializer

logger = logging.getLogger(__name__)

def get_frontend_url():
    """Get the frontend URL from environment variable"""
    return os.getenv('FRONTEND_URL', 'http://localhost:9000')

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    print("TESTING TO SEE IF THIS WORKS")
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(username=username, password=password)
    if user:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username
        })
    else:
        return Response(
            {'error': 'Invalid credentials'}, 
            status=status.HTTP_401_UNAUTHORIZED
        ) 

@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    email = request.data.get('email')
    logger.info(f"Password reset requested for email: {email}")
    
    try:
        user = User.objects.get(email=email)
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        frontend_url = get_frontend_url()
        reset_url = f"{frontend_url}/reset-password/{uid}/{token}"
        logger.info(f"Generated reset URL: {reset_url}")
        
        try:
            send_mail(
                'Password Reset Request - Choco Forest Watch',
                f"""
Hello {user.username},

You recently requested to reset your password for your Choco Forest Watch account. 
Click the link below to reset it:

{reset_url}

Your username is: {user.username}

If you did not request this reset, please ignore this email or contact support if you have concerns.

This link will expire in 24 hours.

Best regards,
The Choco Forest Watch Team
                """,
                os.getenv('DEFAULT_FROM_EMAIL'),
                [email],
                fail_silently=False,
            )
            logger.info(f"Password reset email sent successfully to {email}")
            return Response({
                'message': 'Password reset instructions sent to your email',
                'email': email
            })
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}. Error: {str(e)}")
            return Response({
                'error': 'Failed to send email. Please check email configuration.'
            }, status=500)
            
    except User.DoesNotExist:
        logger.warning(f"Password reset attempted for non-existent email: {email}")
        return Response({
            'message': 'If an account exists with this email, you will receive password reset instructions.'
        }, status=200)
    except Exception as e:
        logger.error(f"Unexpected error during password reset for {email}. Error: {str(e)}")
        return Response({
            'error': 'Unable to process password reset request. Please try again later.'
        }, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request, uidb64, token):
    print("Resetting password with uid: ", uidb64, "and token: ", token)
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        
        if default_token_generator.check_token(user, token):
            new_password = request.data.get('new_password')
            user.set_password(new_password)
            user.save()
            return Response({'message': 'Password reset successful'})
        else:
            return Response({'error': 'Invalid reset link'}, status=400)
    except (TypeError, ValueError, User.DoesNotExist):
        return Response({'error': 'Invalid reset link'}, status=400)

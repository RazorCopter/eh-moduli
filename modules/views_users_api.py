import json
import secrets
import logging
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from .models import User
from .utils import log_action

try:
    from django_ratelimit.decorators import ratelimit
except ImportError:
    def ratelimit(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator

logger = logging.getLogger('modules')


def is_admin_user(user):
    """Strictly administrators and superusers (for user management)"""
    return bool(user and user.is_authenticated and (user.is_superuser or (hasattr(user, 'role') and user.role == 'admin')))


@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["GET"])
def admin_user_list(request):
    """Return list of all operators and admins in JSON format"""
    users = User.objects.filter(is_staff=True).values(
        'id', 'username', 'email', 'first_name', 'last_name', 'role', 'last_login', 'last_login_ip'
    ).order_by('username')
    users_list = list(users)
    for u in users_list:
        if u['last_login']:
            u['last_login'] = u['last_login'].strftime('%Y-%m-%d %H:%M')
        else:
            u['last_login'] = 'Mai'
    return JsonResponse(users_list, safe=False)


@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["POST"])
@ratelimit(key='ip', rate='20/m', method='POST', block=False)
def admin_user_create(request):
    """Create new user"""
    if getattr(request, 'limited', False):
        return JsonResponse({'success': False, 'error': 'Limite di richieste superato. Attendi qualche istante prima di riprovare.'}, status=429)

    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        role = data.get('role', 'operator')

        if not username or not email or not password:
            return JsonResponse({'error': 'Username, email e password sono obbligatori'}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username già esistente'}, status=400)

        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Email già esistente'}, status=400)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_staff=True
        )
        log_action(request.user, 'create_user', 'User', str(user.id), f"Created user {username} ({role})")
        return JsonResponse({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role
        }, status=201)
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["POST", "PUT"])
def admin_user_update(request, user_id):
    """Update existing user"""
    try:
        user = get_object_or_404(User, id=user_id, is_staff=True)
        data = json.loads(request.body)

        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        role = data.get('role', 'operator')

        if username and username != user.username and User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username già esistente'}, status=400)

        if email and email != user.email and User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Email già esistente'}, status=400)

        if username:
            user.username = username
        if email:
            user.email = email
        if password:
            user.set_password(password)
        if first_name:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if role:
            user.role = role

        user.save()
        log_action(request.user, 'update_user', 'User', str(user.id), f"Updated user {user.username}")
        return JsonResponse({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role
        })
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["DELETE"])
def admin_user_delete(request, user_id):
    """Delete user"""
    try:
        user = get_object_or_404(User, id=user_id, is_staff=True)
        if user.id == request.user.id:
            return JsonResponse({'error': 'Non puoi eliminare il tuo stesso account'}, status=400)

        username = user.username
        user.delete()
        log_action(request.user, 'delete_user', 'User', str(user_id), f"Deleted user {username}")
        return JsonResponse({'message': 'Utente eliminato con successo'})
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["POST"])
def admin_user_password_generate(request):
    """Generate random password"""
    try:
        data = json.loads(request.body)
        length = data.get('length', 12)
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*'
        password = ''.join(secrets.choice(chars) for _ in range(length))
        return JsonResponse({'password': password})
    except Exception as e:
        logger.error(f"Error generating password: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

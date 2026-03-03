"""Authentication package - exports the main authentication function"""

from auth.clerk_auth import get_current_user

# Try production auth, fallback to basic
try:
    from auth.clerk_verify import get_current_user_production
    get_authenticated_user = get_current_user_production
except (ImportError, AttributeError):
    get_authenticated_user = get_current_user

__all__ = ['get_authenticated_user', 'get_current_user']

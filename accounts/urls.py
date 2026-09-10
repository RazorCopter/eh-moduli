from django.urls import path
from .views import RateLimitedLoginView, logout_view

urlpatterns = [
    path('login/', RateLimitedLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
]

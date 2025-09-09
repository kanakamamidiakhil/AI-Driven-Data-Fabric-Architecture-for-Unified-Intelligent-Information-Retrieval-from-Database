from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Main API endpoints
    path('query/', views.process_ai_query, name='ai_query'),
    path('examples/', views.get_query_examples, name='examples'),
    path('health/', views.health_check, name='health_check'),
    path('info/', views.api_info, name='api_info'),
]
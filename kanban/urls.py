from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.kanban_board, name='kanban_board'),
    path('api/v1/', include('kanban.api.urls')),
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('contacts/', views.contact_list, name='contact_list'),
]

from django.urls import path
from kanban import views

urlpatterns = [
    path('move-container/', views.move_container, name='api_move_container'),
    path('create-container/', views.create_container, name='api_create_container'),
    path('create-vehicle/', views.create_vehicle, name='api_create_vehicle'),
    path('create-stage/', views.create_stage, name='api_create_stage'),
    path('create-whatsapp-account/', views.create_whatsapp_account, name='api_create_whatsapp_account'),
    path('create-contact/', views.create_contact, name='api_create_contact'),
    path('send-mass/', views.send_mass_messages, name='api_send_mass'),
    path('update-stage-template/<int:pk>/', views.update_stage_template, name='api_update_stage_template'),

    path('delete-container/<int:pk>/', views.delete_container, name='api_delete_container'),
    path('delete-vehicle/<int:pk>/', views.delete_vehicle, name='api_delete_vehicle'),
    path('delete-contact/<int:pk>/', views.delete_contact, name='api_delete_contact'),
    path('twilio-webhook/', views.twilio_webhook, name='api_twilio_webhook'),
]
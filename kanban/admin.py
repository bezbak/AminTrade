from django.contrib import admin
from .models import Container, Vehicle, Contact, WhatsAppAccount, PipelineStage, Messages, CallBack
# Register your models here.
admin.site.register(Container)
admin.site.register(Vehicle)
admin.site.register(Contact)
admin.site.register(WhatsAppAccount)
admin.site.register(PipelineStage)
admin.site.register(CallBack)
admin.site.register(Messages)
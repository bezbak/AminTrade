from django.db import models


class PipelineStage(models.Model):
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)
    message_template = models.TextField(blank=True, default="")
    message_template_ru = models.TextField(blank=True, default="")
    message_template_kg = models.TextField(blank=True, default="")

    def __str__(self):
        return self.name


class WhatsAppAccount(models.Model):
    number = models.CharField(max_length=20)

    def __str__(self):
        return self.number


class Contact(models.Model):
    name = models.CharField(max_length=100)
    whatsapp = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.name} ({self.whatsapp})"


class Vehicle(models.Model):
    number = models.CharField(max_length=50)
    model_car = models.CharField(max_length=100, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    vin = models.CharField(max_length=100, blank=True)
    phone_primary = models.CharField(max_length=20, blank=True)
    phone_secondary = models.CharField(max_length=20, blank=True)
    responsible = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='responsible_vehicles')
    contacts = models.ManyToManyField(Contact, related_name='vehicles')
    whatsapp_accounts = models.ManyToManyField(
        'WhatsAppAccount', related_name='vehicles', blank=True)

    def __str__(self):
        return f"{self.number} - {self.model_car}"


class Container(models.Model):
    name = models.CharField(max_length=100)
    stage = models.ForeignKey(PipelineStage, on_delete=models.CASCADE)
    vehicles = models.ManyToManyField(
        Vehicle, related_name='containers', through='ContainerVehicle')
    responsible = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name='responsible_containers')
    whatsapp_sid = models.ForeignKey(
        WhatsAppAccount, on_delete=models.SET_NULL, related_name='containers', null=True, blank=True)
    arrival_date = models.DateTimeField(null=True, blank=True)
    mute_client = models.BooleanField(default=False)
    mute_manager = models.BooleanField(default=False)
    destination = models.CharField(max_length=100, blank=True, default="")
    arrival_time_bishkek = models.DateTimeField(null=True, blank=True)
    arrival_time_osh = models.DateTimeField(null=True, blank=True)
    transit_erkishtam = models.BooleanField(default=False)
    location = models.CharField(max_length=200, blank=True)


class Text(models.Model):
    content = models.TextField()
    container = models.ForeignKey(
        Container, on_delete=models.CASCADE, related_name='texts')

    def __str__(self):
        return self.content[:50]  # Показать первые 50 символов


class ContainerVehicle(models.Model):
    container = models.ForeignKey(Container, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    responsible = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='container_vehicle_responsible')

    def __str__(self):
        return f"{self.container.name}: {self.vehicle.number}"


class Messages(models.Model):
    from_number = models.CharField(max_length=20)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message for {self.content[:20]} at {self.timestamp}"


class CallBack(models.Model):
    from_number = models.CharField(max_length=20)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Callback from {self.from_number} at {self.timestamp}"
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from twilio.rest import Client
import json
from django.utils import timezone
from .models import CallBack, Container, PipelineStage, Vehicle, Contact, WhatsAppAccount, Text, Messages, ContainerVehicle
import threading
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from datetime import datetime
# ...existing code...


@login_required
def vehicle_list(request):
    query = request.GET.get('q', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    vehicles = Vehicle.objects.all()
    if query:
        vehicles = vehicles.filter(
            Q(number__icontains=query) |
            Q(model_car__icontains=query) |
            Q(vin__icontains=query)
        )
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            vehicles = vehicles.filter(
                containers__arrival_date__gte=date_from_obj)
        except Exception:
            pass
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            vehicles = vehicles.filter(
                containers__arrival_date__lte=date_to_obj)
        except Exception:
            pass
    vehicles = vehicles.distinct()
    contacts = Contact.objects.all()
    return render(request, 'vehicle_list.html', {
        'vehicles': vehicles,
        'q': query,
        'date_from': date_from,
        'date_to': date_to,
        'contacts': contacts,
    })


@login_required
def contact_list(request):
    query = request.GET.get('q', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    contacts = Contact.objects.all()
    if query:
        contacts = contacts.filter(
            Q(name__icontains=query) |
            Q(whatsapp__icontains=query)
        )
    if date_from or date_to:
        contacts = contacts.filter(
            vehicles__containers__arrival_date__gte=date_from if date_from else '1900-01-01')
        if date_to:
            contacts = contacts.filter(
                vehicles__containers__arrival_date__lte=date_to)
    contacts = contacts.distinct()
    return render(request, 'contact_list.html', {'contacts': contacts, 'q': query, 'date_from': date_from, 'date_to': date_to})


@login_required
def kanban_board(request):
    stages = PipelineStage.objects.all().order_by('order')
    vehicles = Vehicle.objects.all()
    contacts = Contact.objects.all()
    return render(request, 'kanban.html', {
        'stages': stages,
        'vehicles': vehicles,
        'contacts': contacts,
        'destinations': stages,
    })


@login_required
def create_container(request):
    if request.method == 'POST':
        name = request.POST['name']
        stage_id = request.POST['stage']
        responsible_id = request.POST['responsible']
        destination = request.POST.get('destination', '')
        arrival_time_bishkek = request.POST.get('arrival_time_bishkek') or None
        arrival_time_osh = request.POST.get('arrival_time_osh') or None
        transit_erkishtam = bool(request.POST.get('transit_erkishtam'))
        mute_client = bool(request.POST.get('mute_client'))
        mute_manager = bool(request.POST.get('mute_manager'))

        container = Container.objects.create(
            name=name,
            stage_id=stage_id,
            responsible_id=responsible_id,
            destination=destination,
            arrival_time_bishkek=arrival_time_bishkek,
            arrival_time_osh=arrival_time_osh,
            transit_erkishtam=transit_erkishtam,
            mute_client=mute_client,
            mute_manager=mute_manager,
        )
        # text = Text.objects.create(
        #     content=text,
        #     container=container
        # )

        # Получаем данные по всем машинам
        numbers = request.POST.getlist('vehicle_number[]')
        models = request.POST.getlist('vehicle_model[]')
        years = request.POST.getlist('vehicle_year[]')
        vins = request.POST.getlist('vehicle_vin[]')
        primary_phones = request.POST.getlist('vehicle_phone_primary[]')
        secondary_phones = request.POST.getlist('vehicle_phone_secondary[]')
        vehicle_responsibles = request.POST.getlist('vehicle_responsible[]')
        for number, model, year, vin in zip(numbers, models, years, vins):
            vehicle = Vehicle.objects.create(
                number=number,
                model_car=model,
                year=year,
                vin=vin,
                phone_primary=primary_phones.pop(0) if primary_phones else '',
                phone_secondary=secondary_phones.pop(
                    0) if secondary_phones else '',
            )
            resp_id = None
            if vehicle_responsibles:
                resp_id = vehicle_responsibles.pop(0) or None
            ContainerVehicle.objects.create(
                container=container,
                vehicle=vehicle,
                responsible_id=resp_id,
            )

        return redirect('kanban_board')
    return redirect('kanban_board')


@login_required
def create_vehicle(request):
    if request.method == 'POST':
        number = request.POST['number']
        model_car = request.POST['model_car']
        year = request.POST['year']
        vin = request.POST['vin']
        phone_primary = request.POST.get('phone_primary', '')
        phone_secondary = request.POST.get('phone_secondary', '')
        responsible_id = request.POST.get('responsible') or None
        contact_ids = request.POST.getlist('contacts')
        vehicle = Vehicle.objects.create(
            number=number,
            model_car=model_car,
            year=year,
            vin=vin,
            phone_primary=phone_primary,
            phone_secondary=phone_secondary,
            responsible_id=responsible_id,
        )
        if contact_ids:
            vehicle.contacts.set(contact_ids)
        return redirect('kanban_board')
    return redirect('kanban_board')


@login_required
def create_stage(request):
    if request.method == 'POST':
        name = request.POST['name']
        order = PipelineStage.objects.count()
        PipelineStage.objects.create(name=name, order=order)
        return redirect('kanban_board')
    return redirect('kanban_board')


@csrf_exempt
@login_required
def move_container(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        container = Container.objects.get(id=data['container_id'])
        new_stage = PipelineStage.objects.get(id=data['stage_id'])
        container.stage = new_stage
        container.arrival_date = timezone.now()
        container.save()
        print('Scheduling WhatsApp notifications for container', container.id)
        threading.Timer(3, send_whatsapp_notification,
                        args=[container.id]).start()
        return JsonResponse({'status': 'ok', "data": data})
    return JsonResponse({'status': 'error'}, status=400)


def send_whatsapp_notification(container_id):
    container = Container.objects.get(id=container_id)
    for vehicle in container.vehicles.all():
        message = build_message(container, vehicle)
        print('Sending WhatsApp message for container',
              container.id, 'to vehicle', vehicle.id)
        send_to_contacts_and_numbers(message, vehicle, container)


def build_message(container, vehicle):
    template_ru = (
        container.stage.message_template_ru or container.stage.message_template or '').strip()
    template_kg = (container.stage.message_template_kg or '').strip()
    text_obj = container.texts.order_by(
        '-id').first() if hasattr(container, 'texts') else None
    fallback = text_obj.content if text_obj else ''
    rendered_ru = render_tokens(template_ru or fallback, container, vehicle)
    rendered_kg = render_tokens(
        template_kg, container, vehicle) if template_kg else ''
    return rendered_ru + ('\n\n' + rendered_kg if rendered_kg else '')


def render_tokens(template, container, vehicle):
    if not template:
        template = 'Этап {stage}: контейнер {container} по машине {vehicle}'
    replacements = {
        'Название': container.name,
        'container': container.name,
        'stage': container.stage.name,
        'vehicle': vehicle.model_car or vehicle.number,
        'Номер': vehicle.number,
        'Модель': vehicle.model_car,
        'VIN': vehicle.vin,
        'Дата': timezone.now().strftime('%Y-%m-%d'),
        'System:Date': timezone.now().strftime('%Y-%m-%d'),
        'destination': container.destination or container.stage.name,
        'Стадия': container.stage.name,
    }
    rendered = template
    # Handle {{var}} style
    for key, value in replacements.items():
        rendered = rendered.replace('{{' + key + '}}', str(value))
    # Handle {=...:TITLE} style
    rendered = rendered.replace('{=System:Date}', replacements['System:Date'])
    rendered = rendered.replace(
        '{=A79665_42333_75296_53691:TITLE}', vehicle.model_car or vehicle.number)
    return rendered


def send_to_contacts_and_numbers(message, vehicle, container=None):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    skip_client = container.mute_client if container else False
    skip_manager = container.mute_manager if container else False
    if not skip_client:
        for contact in vehicle.contacts.all():
            print('Sending to contact:', contact.name, contact.whatsapp)
            if contact.whatsapp:
                try:
                    client.messages.create(
                        body=message,
                        from_=settings.TWILIO_WHATSAPP_FROM,
                        to=f'whatsapp:{contact.whatsapp}'
                    )
                except Exception:
                    pass
        for phone in [vehicle.phone_primary, vehicle.phone_secondary]:
            print('Sending to phone:', phone)
            if phone:
                try:
                    client.messages.create(
                        body=message,
                        from_=settings.TWILIO_WHATSAPP_FROM,
                        to=f'whatsapp:{phone}'
                    )
                except Exception:
                    pass
    if not skip_manager and vehicle.responsible and vehicle.responsible.whatsapp:
        try:
            client.messages.create(
                body=message,
                from_=settings.TWILIO_WHATSAPP_FROM,
                to=f'whatsapp:{vehicle.responsible.whatsapp}'
            )
        except Exception:
            pass


@login_required
@require_POST
def send_mass_messages(request):
    vehicle_ids = request.POST.getlist(
        'vehicles[]') or request.POST.getlist('vehicles')
    contact_ids = request.POST.getlist(
        'contacts[]') or request.POST.getlist('contacts')
    vehicles = list(Vehicle.objects.filter(
        id__in=vehicle_ids)) if vehicle_ids else []
    contacts = list(Contact.objects.filter(
        id__in=contact_ids)) if contact_ids else []
    total_sent = 0
    if not vehicles and contacts:
        for contact in contacts:
            vehicle = contact.vehicles.order_by('-id').first()
            container = get_latest_container(vehicle) if vehicle else None
            message = build_message(
                container, vehicle) if container and vehicle else 'Обновление по заказу'
            if contact.whatsapp:
                try:
                    Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN).messages.create(
                        body=message,
                        from_=settings.TWILIO_WHATSAPP_FROM,
                        to=f'whatsapp:{contact.whatsapp}'
                    )
                    total_sent += 1
                except Exception:
                    pass
        return JsonResponse({'status': 'ok', 'sent': total_sent})
    for vehicle in vehicles:
        container = get_latest_container(vehicle)
        message = build_message(
            container, vehicle) if container else f"Информация по машине {vehicle.number} ({vehicle.model_car})"
        target_contacts = contacts if contacts else list(
            vehicle.contacts.all())
        for contact in target_contacts:
            if contact.whatsapp:
                try:
                    Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN).messages.create(
                        body=message,
                        from_=settings.TWILIO_WHATSAPP_FROM,
                        to=f'whatsapp:{contact.whatsapp}'
                    )
                    total_sent += 1
                except Exception:
                    pass
        for phone in [vehicle.phone_primary, vehicle.phone_secondary]:
            if phone:
                try:
                    Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN).messages.create(
                        body=message,
                        from_=settings.TWILIO_WHATSAPP_FROM,
                        to=f'whatsapp:{phone}'
                    )
                    total_sent += 1
                except Exception:
                    pass
    return JsonResponse({'status': 'ok', 'sent': total_sent})


def get_latest_container(vehicle):
    return vehicle.containers.order_by('-arrival_date', '-id').first()


@login_required
@require_POST
def update_stage_template(request, pk):
    stage = PipelineStage.objects.get(pk=pk)
    stage.message_template = request.POST.get('message_template', '')
    stage.save()
    return redirect('kanban_board')


@csrf_exempt
def twilio_webhook(request):
    if request.method == 'POST':
        from_number = request.POST.get('From')
        body = request.POST.get('Body')
        response = """
        <Response>
            <Message>Received: {}</Message>
            <Message>from: {}</Message>
        </Response>
        """.format(body, from_number)
        Messages.objects.create(from_number=from_number, content=body)
        return HttpResponse(response, content_type='text/xml')
    return HttpResponse("Only POST requests are accepted.", status=405)

@csrf_exempt
def twilio_call(request):
    if request.method == 'POST':
        from_number = request.POST.get('From')
        body = request.POST.get('Body')
        response = """
        <Response>
            <Message>Received: {}</Message>
            <Message>from: {}</Message>
        </Response>
        """.format(body, from_number)
        print(request.POST)
        print(request.POST.get('Body'))
        CallBack.objects.create(from_number='tedAd', content='fesaf')
        return HttpResponse(response, content_type='text/xml')
    return HttpResponse("Only POST requests are accepted.", status=405)


@login_required
@require_POST
def delete_stage(request, pk):
    PipelineStage.objects.get(pk=pk).delete()
    return redirect('kanban_board')


@login_required
@require_POST
def delete_container(request, pk):
    Container.objects.get(pk=pk).delete()
    return redirect('kanban_board')


@login_required
@require_POST
def delete_vehicle(request, pk):
    Vehicle.objects.get(pk=pk).delete()
    return redirect('vehicle_list')


@login_required
@require_POST
def delete_contact(request, pk):
    Contact.objects.get(pk=pk).delete()
    return redirect('contact_list')


@login_required
def create_whatsapp_account(request):
    if request.method == 'POST':
        number = request.POST['number']
        WhatsAppAccount.objects.create(number=number)
        return redirect('kanban_board')
    return redirect('kanban_board')


@login_required
def create_contact(request):
    if request.method == 'POST':
        name = request.POST['name']
        whatsapp = request.POST['whatsapp']
        Contact.objects.create(name=name, whatsapp=whatsapp)
        return redirect('kanban_board')
    return redirect('kanban_board')

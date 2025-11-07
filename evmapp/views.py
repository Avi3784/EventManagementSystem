import csv, string, secrets, json
from django.views.decorators.csrf import csrf_exempt

import uuid
import razorpay
import qrcode
from io import BytesIO
from urllib.parse import quote_plus
from django.core.mail import EmailMessage
from django.shortcuts import render, redirect
from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from evmproject import settings
from .models import Booking, Event, Sponsor, Volunteer, Payment
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from datetime import datetime, timedelta
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, F, Min, Count
from django.db import transaction
from twilio.rest import Client
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    
    return render(request, 'evmapp/register.html', {'form':form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            error_message = "Invalid Credentials, Please try again"
            
    return render(request, 'evmapp/login.html', {'error_message':error_message if 'error_message' in locals() else ''})


@login_required(login_url='/login/')
def dashboard(request):
    # Basic counts
    events = Event.objects.all()
    total_events = events.count()
    volunteers = Volunteer.objects.count()
    total_sponsors = Sponsor.objects.count()
    
    # Financial analytics
    total_funds = Booking.objects.aggregate(total_funds=Sum('total_cost'))['total_funds'] or 0
    sponsor_funds = Sponsor.objects.aggregate(total_sponsor_funds=Sum('cost'))['total_sponsor_funds'] or 0
    net_revenue = total_funds - sponsor_funds

    # Event analytics
    events_with_stats = Event.objects.annotate(
        tickets_sold=Sum('booking__number_of_tickets'),
        revenue=Sum('booking__total_cost'),
        tickets_remaining=F('total_tickets') - Sum('booking__number_of_tickets'),
        booking_count=Count('booking')
    ).order_by('-date')

    # Category analytics
    category_stats = Event.objects.values('category').annotate(
        count=Count('id'),
        total_revenue=Sum('booking__total_cost'),
        total_tickets=Sum('booking__number_of_tickets')
    )

    # Time-based analytics
    from django.utils import timezone
    today = timezone.now().date()
    upcoming_events = events.filter(date__gte=today).order_by('date')[:5]
    recent_bookings = Booking.objects.select_related('event').order_by('-booking_date')[:5]

    # Calculate percentage of sold tickets and revenue targets
    for event in events_with_stats:
        event.tickets_sold = event.tickets_sold or 0
        event.revenue = event.revenue or 0
        event.tickets_remaining = event.tickets_remaining or event.total_tickets
        event.booking_count = event.booking_count or 0
        event.sold_percentage = (event.tickets_sold / event.total_tickets * 100) if event.total_tickets > 0 else 0

    context = {
        'total_events': total_events,
        'total_sponsors': total_sponsors,
        'total_funds': total_funds,
        'sponsor_funds': sponsor_funds,
        'net_revenue': net_revenue,
        'volunteers': volunteers,
        
        # Event data for charts
        'events': events_with_stats,
        'category_stats': category_stats,
        'upcoming_events': upcoming_events,
        'recent_bookings': recent_bookings,

        # Chart data
        'event_labels': [event.event_name for event in events_with_stats],
        'tickets_sold': [event.tickets_sold for event in events_with_stats],
        'revenue_data': [event.revenue for event in events_with_stats],
        'category_labels': [cat['category'] for cat in category_stats],
        'category_counts': [cat['count'] for cat in category_stats],
        'category_revenue': [cat['total_revenue'] or 0 for cat in category_stats],
    }
    

    return render(request, 'evmapp/dashboard.html', context)


def select_venue(request):
    """Render the Leaflet venue selection page or return selected coordinates as JSON."""
    if request.method == 'POST':
        venue = request.POST.get('venue')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')

        if venue and latitude and longitude:
            return JsonResponse({'venue': venue, 'latitude': latitude, 'longitude': longitude})

    return render(request, 'evmapp/venue_map.html')


@login_required(login_url='/login/')
def add_event(request):
    """Handle add event form submission with enhanced validation and Google Maps integration."""
    if request.method == 'POST':
        event_name = request.POST.get('event_name')
        organiser_name = request.POST.get('organiser_name')
        time = request.POST.get('time')
        date = request.POST.get('date')
        venue = request.POST.get('venue')
        theme = request.POST.get('theme') or 'General'
        total_tickets_raw = request.POST.get('total_tickets')
        price_per_ticket_raw = request.POST.get('price_per_ticket')
        description = request.POST.get('description')
        free_ticket = request.POST.get('free_ticket') == 'on'

        # Normalize numeric inputs
        try:
            total_tickets = int(total_tickets_raw) if total_tickets_raw and str(total_tickets_raw).strip() else 0
        except (ValueError, TypeError):
            total_tickets = 0

        # If free_ticket is checked, price per ticket should be zero
        if free_ticket:
            price_per_ticket = Decimal('0')
        else:
            try:
                price_per_ticket = Decimal(str(price_per_ticket_raw).strip()) if price_per_ticket_raw and str(price_per_ticket_raw).strip() else Decimal('0')
            except (InvalidOperation, TypeError):
                price_per_ticket = Decimal('0')

        # Create Event object
        event = Event.objects.create(
            event_name=event_name,
            organiser=organiser_name,
            time=time,
            date=date,
            venue=venue,
            theme=theme,
            total_tickets=total_tickets,
            price_per_ticket=price_per_ticket,
            description=description,
            free_ticket=free_ticket,
        )

        # Handling sponsors
        sponsor_names = request.POST.getlist('sponsor_name[]')
        purposes = request.POST.getlist('purpose[]')
        contacts = request.POST.getlist('contact[]')
        costs = request.POST.getlist('cost[]')

        for i in range(len(sponsor_names)):
            sponsor_name = sponsor_names[i].strip() if sponsor_names[i] else ''
            purpose = purposes[i].strip() if i < len(purposes) and purposes[i] else ''
            contact = contacts[i].strip() if i < len(contacts) and contacts[i] else ''
            cost_raw = costs[i] if i < len(costs) and costs[i] else ''

            # Try to coerce cost to Decimal, default to 0 if invalid/empty
            try:
                cost_val = Decimal(str(cost_raw).strip()) if cost_raw and str(cost_raw).strip() else Decimal('0')
            except (InvalidOperation, TypeError):
                cost_val = Decimal('0')

            # Only create sponsor if a name is provided (other fields optional)
            if sponsor_name:
                sponsor = Sponsor.objects.create(
                    name=sponsor_name,
                    purpose=purpose,
                    contact=contact,
                    cost=cost_val
                )
                event.sponsors.add(sponsor)

        messages.success(request, 'Event added successfully.')
        return redirect('dashboard')

    return render(request, 'evmapp/add_event.html')


@login_required(login_url='/login/')
def view_event(request):
    # Assuming you have an Event model and want to fetch all events
    events = Event.objects.all()
    total_tickets_sold = Booking.objects.aggregate(total_tickets_sold=Sum('number_of_tickets'))['total_tickets_sold'] or 0
    return render(request, 'evmapp/view_events.html', {'events': events, 'total_tickets_sold':total_tickets_sold})



def send_confirmation_sms(contact_number, message):
    # Initialize Twilio client
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    # Send SMS message
    try:
        client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=contact_number
        )
    except Exception as e:
        print(f"Failed to send SMS: {str(e)}")

def send_booking_confirmation_email(booking):
    """Send booking confirmation email with enhanced subject and content"""
    event = booking.event
    subject = f'🎫 Ticket Confirmed: {event.event_name} | Ticket ID: {booking.ticket_id}'
    
    # Add more context data for the email template
    context = {
        'booking': booking,
        'event': event,
        'payment_info': {
            'amount': booking.total_cost,
            'currency': 'INR',
            'is_free': booking.total_cost == 0
        },
    }
    
    # Build UPI URI for attachments and template (if UPI configured)
    upi_uri = None
    try:
        if getattr(settings, 'UPI_VPA', None) and booking.total_cost and float(booking.total_cost) > 0:
            note = getattr(settings, 'UPI_NOTE', '') or event.event_name
            upi_uri = f"upi://pay?pa={settings.UPI_VPA}&pn={quote_plus(getattr(settings, 'UPI_NAME', ''))}&am={booking.total_cost}&cu=INR&tn={quote_plus(note)}"
            context['upi_uri'] = upi_uri
    except Exception:
        upi_uri = None

    message = render_to_string('evmapp/email/booking_confirmation.html', context)

    # Use EmailMessage so we can attach the UPI QR image
    email = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, [booking.email])
    email.content_subtype = 'html'

    # Attach server-side generated UPI QR PNG for convenience
    if upi_uri:
        try:
            qr_img = qrcode.make(upi_uri)
            buf = BytesIO()
            qr_img.save(buf, format='PNG')
            buf.seek(0)
            email.attach(f'upi_{booking.id}.png', buf.read(), 'image/png')
        except Exception as e:
            # Log and continue without blocking email
            print(f"Failed to generate/attach UPI QR: {e}")

    try:
        email.send(fail_silently=False)
    except Exception as e:
        print(f"Failed to send booking confirmation email: {e}")

def send_event_reminder_email(booking, hours_remaining=24):
    """Send event reminder email with time-specific information"""
    event = booking.event
    if hours_remaining == 24:
        subject = f'⏰ 24 Hours to Go: {event.event_name} Tomorrow!'
    elif hours_remaining == 2:
        subject = f'🔔 Starting Soon: {event.event_name} in 2 Hours!'
    else:
        subject = f'Reminder: {event.event_name} is Coming Up!'
    
    context = {
        'booking': booking,
        'event': event,
        'hours_remaining': hours_remaining,
        'important_items': [
            'Your Ticket ID',
            'Valid ID proof',
            'Comfortable attire',
        ]
    }
    
    message = render_to_string('evmapp/email/event_reminder.html', context)
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [booking.email],
            html_message=message,
            fail_silently=False,
        )
        print(f"Reminder sent to {booking.email} for event {event.event_name}")
    except Exception as e:
        print(f"Failed to send reminder to {booking.email}: {str(e)}")

def check_and_send_reminders():
    """Check and send reminders at different intervals"""
    now = timezone.now()
    
    # Send 24-hour reminders
    tomorrow = now + timedelta(days=1)
    day_before_bookings = Booking.objects.filter(
        event__date=tomorrow.date(),
        reminder_24h_sent=False  # Add this field to Booking model
    )
    
    for booking in day_before_bookings:
        send_event_reminder_email(booking, hours_remaining=24)
        booking.reminder_24h_sent = True
        booking.save()
    
    # Send 2-hour reminders
    two_hours_from_now = now + timedelta(hours=2)
    upcoming_bookings = Booking.objects.filter(
        event__date=now.date(),
        event__time__hour=two_hours_from_now.hour,
        event__time__minute=two_hours_from_now.minute,
        reminder_2h_sent=False  # Add this field to Booking model
    )
    
    for booking in upcoming_bookings:
        send_event_reminder_email(booking, hours_remaining=2)
        booking.reminder_2h_sent = True
        booking.save()

def generate_ticket_id(length=5):
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def ticketbooking(request):
    events = Event.objects.filter(status=True)
    if not events.exists():
        messages.warning(request, 'No events are currently available for booking.')
        return render(request, 'evmapp/ticketbooking.html', {'events': []})

    if request.method == 'POST':
        try:
            # Validate event selection
            event_id = request.POST.get('event')
            if not event_id:
                messages.error(request, 'Please select an event')
                return render(request, 'evmapp/ticketbooking.html', {'events': events})
            
            event = Event.objects.filter(pk=event_id, status=True).first()
            if not event:
                messages.error(request, 'Selected event is not available for booking')
                return render(request, 'evmapp/ticketbooking.html', {'events': events})
            
            # Validate tickets
            try:
                number_of_tickets = int(request.POST.get('number_of_tickets', 0))
                if number_of_tickets <= 0:
                    raise ValueError
            except ValueError:
                messages.error(request, 'Please enter a valid number of tickets')
                return render(request, 'evmapp/ticketbooking.html', {'events': events})
            
            # Validate required fields
            name = request.POST.get('name')
            contact_number = request.POST.get('contact_number')
            email = request.POST.get('email')
            
            if not all([name, contact_number, email]):
                messages.error(request, 'Please fill in all required fields')
                return render(request, 'evmapp/ticketbooking.html', {'events': events})
            
            # Calculate cost
            total_cost = float(event.price_per_ticket * number_of_tickets)
            
            # Format phone number
            if not contact_number.startswith('+'):
                contact_number = f'+91{contact_number}'

            # Generate ticket ID
            ticket_id = str(uuid.uuid4().hex)[:5].upper()

            # Process payment and create booking
            if total_cost > 0:
                try:
                    # Use API credentials from settings so authentication works in dev/prod
                    client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
                    order = client.order.create({
                        'amount': int(total_cost * 100),
                        'currency': 'INR',
                        'receipt': str(ticket_id),
                        'payment_capture': '1'
                    })

                    # Create booking record (payment will be confirmed via webhook / confirm endpoint)
                    booking = Booking.objects.create(
                        event=event,
                        number_of_tickets=number_of_tickets,
                        name=name,
                        contact_number=contact_number,
                        email=email,
                        total_cost=total_cost,
                        ticket_id=ticket_id
                    )

                    # Persist order id for reconciliation
                    Payment.objects.create(
                        booking=booking,
                        razorpay_order_id=order.get('id'),
                        amount=total_cost,
                        currency='INR',
                        status='created',
                        raw_response=order
                    )

                    # Pass booking and order info so checkout can render Razorpay widget and UPI QR
                    return render(request, "evmapp/checkout.html", {
                        'payment': order,
                        'booking': booking,
                        'UPI_VPA': settings.UPI_VPA,
                        'UPI_NAME': settings.UPI_NAME,
                        'UPI_NOTE': getattr(settings, 'UPI_NOTE', ''),
                        'RAZORPAY_API_KEY': settings.RAZORPAY_API_KEY,
                    })
                except Exception as e:
                    messages.error(request, f'Payment processing failed: {str(e)}')
                    return render(request, 'evmapp/ticketbooking.html', {'events': events})
            else:
                # Handle free events
                booking = Booking.objects.create(
                    event=event,
                    number_of_tickets=number_of_tickets,
                    name=name,
                    contact_number=contact_number,
                    email=email,
                    total_cost=0,
                    ticket_id=ticket_id
                )
                
                send_booking_confirmation_email(booking)
                messages.success(request, "Your booking has been confirmed!")
                return redirect('home')
                
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return render(request, 'evmapp/ticketbooking.html', {'events': events})
    
    return render(request, 'evmapp/ticketbooking.html', {'events': events})


@csrf_exempt
def payment_confirm(request):
    """Endpoint the frontend calls after Razorpay checkout success to verify signature server-side."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'reason': 'invalid_method'}, status=405)

    try:
        payload = json.loads(request.body)
    except Exception:
        return JsonResponse({'status': 'error', 'reason': 'invalid_json'}, status=400)

    payment_id = payload.get('razorpay_payment_id')
    order_id = payload.get('razorpay_order_id')
    signature = payload.get('razorpay_signature')

    if not all([payment_id, order_id, signature]):
        return JsonResponse({'status': 'error', 'reason': 'missing_fields'}, status=400)

    client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        })
    except Exception:
        return JsonResponse({'status': 'error', 'reason': 'signature_verification_failed'}, status=400)

    payment_obj = Payment.objects.filter(razorpay_order_id=order_id).first()
    if not payment_obj:
        return JsonResponse({'status': 'error', 'reason': 'order_not_found'}, status=404)

    # Idempotency: if already processed, return ok
    if payment_obj.razorpay_payment_id:
        return JsonResponse({'status': 'ok', 'message': 'already_processed'})

    # Update payment and booking
    payment_obj.razorpay_payment_id = payment_id
    payment_obj.status = 'captured'
    payment_obj.raw_response = payload
    payment_obj.method = payload.get('method')
    payment_obj.save()

    booking = payment_obj.booking
    booking.paid = True
    booking.payment_id = payment_id
    booking.save()

    # Send confirmations now that payment is verified
    try:
        send_confirmation_sms(booking.contact_number, f"Dear {booking.name}, your booking for {booking.number_of_tickets} ticket(s) with ticket ID {booking.ticket_id} has been confirmed.")
    except Exception:
        pass
    try:
        send_booking_confirmation_email(booking)
    except Exception:
        pass

    return JsonResponse({'status': 'ok'})


@csrf_exempt
def razorpay_webhook(request):
    """Webhook endpoint for Razorpay events. Verify signature and process events idempotently."""
    payload = request.body
    signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE')
    webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
    client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

    # Verify signature
    try:
        client.utility.verify_webhook_signature(payload, signature, webhook_secret)
    except Exception:
        return HttpResponse(status=400)

    try:
        event = json.loads(payload)
    except Exception:
        return HttpResponse(status=400)

    ev_type = event.get('event')
    p = event.get('payload', {})
    payment_entity = p.get('payment', {}).get('entity', {})

    # Handle payment captured
    if ev_type == 'payment.captured' and payment_entity:
        order_id = payment_entity.get('order_id')
        payment_id = payment_entity.get('id')
        payment_obj = Payment.objects.filter(razorpay_order_id=order_id).first()
        if payment_obj and not payment_obj.razorpay_payment_id:
            payment_obj.razorpay_payment_id = payment_id
            payment_obj.status = 'captured'
            payment_obj.raw_response = payment_entity
            payment_obj.method = payment_entity.get('method')
            payment_obj.save()

            booking = payment_obj.booking
            booking.paid = True
            booking.payment_id = payment_id
            booking.save()
            # send confirmation
            try:
                send_confirmation_sms(booking.contact_number, f"Dear {booking.name}, your booking (Ticket ID: {booking.ticket_id}) is confirmed.")
            except Exception:
                pass
            try:
                send_booking_confirmation_email(booking)
            except Exception:
                pass

    # Handle payment failed
    if ev_type == 'payment.failed' and payment_entity:
        order_id = payment_entity.get('order_id')
        payment_obj = Payment.objects.filter(razorpay_order_id=order_id).first()
        if payment_obj:
            payment_obj.status = 'failed'
            payment_obj.raw_response = payment_entity
            payment_obj.save()

    return HttpResponse(status=200)


@login_required(login_url='/login/')
def payments_admin(request):
    """Staff view: list recent payments for reconciliation/audit."""
    if not request.user.is_staff:
        messages.error(request, 'Permission denied')
        return redirect('home')

    payments = Payment.objects.select_related('booking__event').order_by('-created_at')[:200]
    return render(request, 'evmapp/payments_list.html', {'payments': payments})


def update_event_status(request):
    event_id = request.POST.get('event_id') 
    status = request.POST.get('status')

    try:
        event = Event.objects.get(pk=event_id)
        event.status = (status == 'active')
        event.save()
        messages.success(request, 'Event status changed successfully')
    except Event.DoesNotExist:
        messages.error(request, 'Event not found')
    return redirect('viewevent')
 
@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    total_tickets_sold = Booking.objects.filter(event=event).aggregate(total_tickets_sold=Sum('number_of_tickets'))['total_tickets_sold'] or 0
    event_cost = event.sponsors.aggregate(total_cost=Sum('cost'))['total_cost'] or 0
    money_collected = total_tickets_sold * event.price_per_ticket
    percentage_collected = round((money_collected / event_cost) * 100, 2) if event_cost else 0
    bookings = Booking.objects.filter(event=event)
    name_filter = request.GET.get('name')
    contact_number_filter = request.GET.get('contact_number')

    bookings = Booking.objects.filter(event=event)
    if name_filter:
        bookings = bookings.filter(name__icontains=name_filter)
    if contact_number_filter:
        bookings = bookings.filter(contact_number__icontains=contact_number_filter)
    return render(request, "evmapp/event_detail.html", 
                  {'event':event, 
                   'total_tickets_sold':total_tickets_sold, 
                   'event_cost':event_cost, 
                   'percentage_collected':percentage_collected,
                   'bookings':bookings})


@csrf_exempt
def home(request):
    events = Event.objects.all()
    if request.method == 'POST':
        a = request.POST
        print(a)
        
    return render(request, "evmapp/home.html", {'events': events})

@login_required
def logout_view(request):
    logout(request)
    return redirect('home')

@login_required(login_url='/login/')
def edit_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.method == 'POST':
        try:
            # Extract form data from request.POST
            event.event_name = request.POST.get('event_name')
            event.organiser = request.POST.get('organiser_name')
            event.venue = request.POST.get('venue')
            event.theme = request.POST.get('theme')
            event.description = request.POST.get('description')
            
            # Handle time field - only update if not empty
            time = request.POST.get('time')
            if time and time.strip():
                event.time = time
                
            # Handle date field - only update if not empty
            date = request.POST.get('date')
            if not date or not date.strip():
                # Keep the existing date if no new date is provided
                messages.warning(request, 'No date provided - keeping existing date')
            else:
                # Try to use the new date
                event.date = date

            # Attempt to save and validate the model
            event.save()
            messages.success(request, 'Event details edited successfully')
            return redirect('viewevent')
            
        except Exception as e:
            # If validation fails, add error message and keep the existing values
            messages.error(request, f'Error updating event: Please ensure all required fields are filled correctly')
            return render(request, 'evmapp/edit_event.html', {
                'event': event,
                'error': str(e)
            })
            
    # If it's a GET request, render the edit_event template with the event object
    return render(request, 'evmapp/edit_event.html', {'event': event})

@login_required(login_url='/login/')
def sponsor(request):
    sponsors = Sponsor.objects.all()
    name_filter = request.GET.get('name')
    contact_number_filter = request.GET.get('contact_number')
    sponsors = Sponsor.objects.filter()
    if name_filter:
        sponsors = sponsors.filter(name__icontains=name_filter)
    if contact_number_filter:
        sponsors = sponsors.filter(contact_number__icontains=contact_number_filter)
    return render(request, 'evmapp/sponsor.html', {'sponsors':sponsors})



def download_participants_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="participants.csv"'

    writer = csv.writer(response)
    writer.writerow(['Name', 'Contact Number', 'Tickets', 'Total Cost', 'Ticket ID'])

    bookings = Booking.objects.all()
    for booking in bookings:
        writer.writerow([booking.name, booking.contact_number, booking.number_of_tickets, booking.total_cost, booking.ticket_id])

    return response



def add_volunteer(request):
    if request.method == 'POST':
        # Extract data from the request
        name = request.POST.get('name')
        contact_number = request.POST.get('contact_number')
        email = request.POST.get('email')
        flat_number = request.POST.get('flat_number')
        skills_interests = request.POST.get('skills_interests')
        previous_experience = request.POST.get('previous_experience')
        availability_period = request.POST.get('availability_period')
        volunteer_role = request.POST.get('volunteer_role')
        emergency_contact = request.POST.get('emergency_contact')

        # Create a new Volunteer object with the extracted data
        new_volunteer = Volunteer.objects.create(
            name=name,
            contact_number=contact_number,
            email=email,
            flat_number=flat_number,
            skills_interests=skills_interests,
            previous_experience=previous_experience,
            availability_period=availability_period,
            volunteer_role=volunteer_role,
            emergency_contact=emergency_contact
        )

        # Optionally, you can perform additional actions here, such as sending a confirmation email

        # Redirect to a success page or home page
        messages.success(request, 'Your Volunteer Form was Submitted Successfully, Our team will be reaching out to you soon!!')
        return redirect(home)
    
    return render(request, 'evmapp/add_volunteer.html')

@login_required(login_url='/login/')
def view_volunteers(request):
    volunteers = Volunteer.objects.all()
    return render(request, 'evmapp/view_volunteers.html', {'volunteers':volunteers})







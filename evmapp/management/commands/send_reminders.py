from django.core.management.base import BaseCommand
from django.utils import timezone
from evmapp.views import send_event_reminder_email
from evmapp.models import Booking
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send event reminders to participants'

    def handle(self, *args, **options):
        now = timezone.now()
        sent_count = 0
        error_count = 0

        # Send 24-hour reminders
        tomorrow = now + timedelta(days=1)
        day_before_bookings = Booking.objects.filter(
            event__date=tomorrow.date(),
            reminder_24h_sent=False
        ).select_related('event')
        
        for booking in day_before_bookings:
            try:
                send_event_reminder_email(booking, hours_remaining=24)
                booking.reminder_24h_sent = True
                booking.last_reminder_sent = now
                booking.save()
                sent_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Sent 24h reminder for {booking.event.event_name} to {booking.email}'
                    )
                )
            except Exception as e:
                error_count += 1
                logger.error(f'Failed to send 24h reminder to {booking.email}: {str(e)}')

        # Send 2-hour reminders
        two_hours_from_now = now + timedelta(hours=2)
        upcoming_bookings = Booking.objects.filter(
            event__date=now.date(),
            event__time__hour=two_hours_from_now.hour,
            event__time__minute=two_hours_from_now.minute,
            reminder_2h_sent=False
        ).select_related('event')
        
        for booking in upcoming_bookings:
            try:
                send_event_reminder_email(booking, hours_remaining=2)
                booking.reminder_2h_sent = True
                booking.last_reminder_sent = now
                booking.save()
                sent_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Sent 2h reminder for {booking.event.event_name} to {booking.email}'
                    )
                )
            except Exception as e:
                error_count += 1
                logger.error(f'Failed to send 2h reminder to {booking.email}: {str(e)}')

        # Print summary
        self.stdout.write(
            self.style.SUCCESS(
                f'Reminder task completed: {sent_count} reminders sent, {error_count} errors'
            )
        )
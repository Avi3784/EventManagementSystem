from django.core.management.base import BaseCommand
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
import sys

class Command(BaseCommand):
    help = 'Test email sending functionality'

    def handle(self, *args, **options):
        test_email = input("Enter the email address to send test email to: ")
        
        self.stdout.write("Testing email settings...")
        self.stdout.write(f"SMTP Settings:")
        self.stdout.write(f"  Host: {settings.EMAIL_HOST}")
        self.stdout.write(f"  Port: {settings.EMAIL_PORT}")
        self.stdout.write(f"  TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"  User: {settings.EMAIL_HOST_USER}")
        
        try:
            # Create test email
            subject = 'Test Email from Event Management System'
            message = 'This is a test email to verify the email settings are working correctly.'
            html_message = '''
                <html>
                    <body>
                        <h2>Test Email</h2>
                        <p>This is a test email to verify the email settings are working correctly.</p>
                        <p>If you received this email, it means the email configuration is working!</p>
                    </body>
                </html>
            '''
            
            # Try sending with EmailMessage
            try:
                self.stdout.write("Attempting to send email using EmailMessage...")
                email = EmailMessage(
                    subject=subject,
                    body=html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[test_email],
                )
                email.content_subtype = "html"
                email.send(fail_silently=False)
                self.stdout.write(self.style.SUCCESS('Successfully sent test email using EmailMessage!'))
            except Exception as email_error:
                self.stdout.write(self.style.ERROR(f'EmailMessage error: {str(email_error)}'))
                
                # Try with send_mail as fallback
                try:
                    self.stdout.write("Attempting to send email using send_mail as fallback...")
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[test_email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    self.stdout.write(self.style.SUCCESS('Successfully sent test email using send_mail!'))
                except Exception as send_mail_error:
                    self.stdout.write(self.style.ERROR(f'send_mail error: {str(send_mail_error)}'))
                    sys.exit(1)
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send test email: {str(e)}'))
            sys.exit(1)
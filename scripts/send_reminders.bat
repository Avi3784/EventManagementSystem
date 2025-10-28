@echo off
cd /d "C:\Users\laptop\OneDrive\Desktop\EVM-SE\EventManagementSystem"
python manage.py send_reminders >> "logs\reminders.log" 2>&1
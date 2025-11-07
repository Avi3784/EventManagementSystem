from django.contrib.auth import views as auth_views
from django.urls import path
from evmapp import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('addevent', views.add_event, name='addevent'),
    path('viewevent', views.view_event, name='viewevent'),
    path('sponsor/', views.sponsor, name='sponsor'),
    path('booktickets', views.ticketbooking, name='bookticket'),
    path('payments/confirm/', views.payment_confirm, name='payment_confirm'),
    path('payments/webhook/', views.razorpay_webhook, name='razorpay_webhook'),
    path('payments/admin/', views.payments_admin, name='payments_admin'),
    path('update_event_status', views.update_event_status, name='update_event_status'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('add_volunteer/', views.add_volunteer, name='add_volunteer'),
    path('logout/', views.logout_view, name='logout'),
    path('edit_event/<int:event_id>/', views.edit_event, name='edit_event'),
    path('download-participants-csv/', views.download_participants_csv, name='download_participants_csv'),
    path('view_volunteers/', views.view_volunteers, name='view_volunteers'),
]
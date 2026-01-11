from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('cash/', views.cash_dashboard, name='cash-dashboard'),
]
from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('roles/', views.roles, name='roles'),
    path('customers/', views.customers, name='customers'),
    path('leads/', views.leads, name='leads'),
    path('inventory/', views.inventory, name='inventory'),
    path('deals/', views.deals, name='deals'),
    path('cash/', views.cash_dashboard, name='cash-dashboard'),
]

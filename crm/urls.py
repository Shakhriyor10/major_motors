from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('roles/', views.roles, name='roles'),
    path('customers/', views.customers, name='customers'),
    path('leads/', views.leads, name='leads'),
    path('autosalon/', views.autosalon, name='autosalon'),
    path('inventory/', views.inventory, name='inventory'),
    path('deals/', views.deals, name='deals'),
    path('cash/', views.cash_dashboard, name='cash-dashboard'),
]

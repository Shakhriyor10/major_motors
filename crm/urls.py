from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from . import checkers as checkers_views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('settings/', views.theme_settings, name='theme-settings'),
    path('roles/', views.roles, name='roles'),
    path('customers/', views.customers, name='customers'),
    path('leads/', views.leads, name='leads'),
    path('autosalon/', views.autosalon, name='autosalon'),
    path('inventory/', views.inventory, name='inventory'),
    path('deals/', views.deals, name='deals'),
    path('cash/', views.cash_dashboard, name='cash-dashboard'),
    path('lounge/', views.lounge, name='lounge'),
    path('lounge/tic-tac-toe/lobby/', views.tic_tac_toe_lobby, name='tic-tac-toe-lobby'),
    path('lounge/tic-tac-toe/create/', views.tic_tac_toe_create, name='tic-tac-toe-create'),
    path('lounge/tic-tac-toe/<int:game_id>/join/', views.tic_tac_toe_join, name='tic-tac-toe-join'),
    path('lounge/tic-tac-toe/<int:game_id>/state/', views.tic_tac_toe_state, name='tic-tac-toe-state'),
    path('lounge/tic-tac-toe/<int:game_id>/move/', views.tic_tac_toe_move, name='tic-tac-toe-move'),
    path('lounge/checkers/', checkers_views.page, name='checkers'),
    path('lounge/checkers/lobby/', checkers_views.lobby, name='checkers-lobby'),
    path('lounge/checkers/create/', checkers_views.create, name='checkers-create'),
    path('lounge/checkers/<int:game_id>/join/', checkers_views.join, name='checkers-join'),
    path('lounge/checkers/<int:game_id>/state/', checkers_views.state, name='checkers-state'),
    path('lounge/checkers/<int:game_id>/move/', checkers_views.move, name='checkers-move'),
    path('lounge/checkers/<int:game_id>/resign/', checkers_views.resign, name='checkers-resign'),
    path('lounge/checkers/<int:game_id>/draw/', checkers_views.draw, name='checkers-draw'),
    path('lounge/checkers/<int:game_id>/rematch/', checkers_views.rematch, name='checkers-rematch'),
    path('cash/employees/save/', views.cash_employee_save, name='cash-employee-save'),
    path('cash/employees/delete/', views.cash_employee_delete, name='cash-employee-delete'),
]

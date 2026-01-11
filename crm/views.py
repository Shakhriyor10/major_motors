from decimal import Decimal, InvalidOperation

from django.db.models import Count
from django.shortcuts import redirect, render

from .models import (
    CashAccount,
    CashConversion,
    CurrencyRate,
    Customer,
    Deal,
    Lead,
    Role,
    Vehicle,
)


def home(request):
    exchange_rate = CurrencyRate.objects.order_by('-effective_date', '-created_at').first()
    return render(request, 'crm/home.html', {'exchange_rate': exchange_rate})


def dashboard(request):
    exchange_rate = CurrencyRate.objects.order_by('-effective_date', '-created_at').first()
    stats = {
        'customers': Customer.objects.count(),
        'leads': Lead.objects.count(),
        'vehicles': Vehicle.objects.count(),
        'deals': Deal.objects.count(),
    }
    leads_by_stage = Lead.objects.select_related('stage').values('stage__name').annotate(total=Count('id'))
    status_labels = dict(Vehicle.VehicleStatus.choices)
    vehicles_by_status = [
        {
            'status': status_labels.get(item['status'], item['status']),
            'total': item['total'],
        }
        for item in Vehicle.objects.values('status').annotate(total=Count('id'))
    ]
    return render(
        request,
        'crm/dashboard.html',
        {
            'exchange_rate': exchange_rate,
            'stats': stats,
            'leads_by_stage': leads_by_stage,
            'vehicles_by_status': vehicles_by_status,
        },
    )


def roles(request):
    roles_qs = Role.objects.select_related('permissions').order_by('name')
    return render(request, 'crm/roles.html', {'roles': roles_qs})


def customers(request):
    customers_qs = Customer.objects.select_related('lead_source', 'assigned_manager').order_by('-created_at')[:50]
    return render(request, 'crm/customers.html', {'customers': customers_qs})


def leads(request):
    leads_qs = Lead.objects.select_related('customer', 'stage', 'assigned_to').order_by('-created_at')[:50]
    return render(request, 'crm/leads.html', {'leads': leads_qs})


def inventory(request):
    vehicles_qs = Vehicle.objects.order_by('-created_at')[:50]
    return render(request, 'crm/inventory.html', {'vehicles': vehicles_qs})


def deals(request):
    deals_qs = Deal.objects.select_related('customer', 'vehicle', 'manager').order_by('-created_at')[:50]
    return render(request, 'crm/deals.html', {'deals': deals_qs})


def cash_dashboard(request):
    cash_account = CashAccount.get_current()
    if request.method == 'POST' and request.user.is_superuser:
        try:
            cash_account.uzs_balance = Decimal(request.POST.get('uzs_balance', cash_account.uzs_balance))
            cash_account.usd_balance = Decimal(request.POST.get('usd_balance', cash_account.usd_balance))
        except (InvalidOperation, TypeError):
            return redirect('cash-dashboard')
        cash_account.updated_by = request.user
        cash_account.save(update_fields=['uzs_balance', 'usd_balance', 'updated_by', 'updated_at'])
        return redirect('/cash/?reset_cash=1')
    exchange_rate = CurrencyRate.objects.order_by('-effective_date', '-created_at').first()
    conversions = CashConversion.objects.select_related('shift').order_by('-created_at')[:10]
    return render(
        request,
        'crm/cash.html',
        {
            'cash_account': cash_account,
            'exchange_rate': exchange_rate,
            'conversions': conversions,
        },
    )

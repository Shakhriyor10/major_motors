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
    VehicleOption,
    VehicleMedia,
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


def autosalon(request):
    default_options = [
        'Кондиционер',
        'Климат-контроль',
        'Кожаный салон',
        'Подогрев сидений',
        'Камера заднего вида',
        'Парктроник',
    ]
    for option_name in default_options:
        VehicleOption.objects.get_or_create(name=option_name)
    options_qs = VehicleOption.objects.order_by('name')

    if request.method == 'POST':
        def to_decimal(value):
            if value in (None, ''):
                return None
            try:
                return Decimal(value)
            except InvalidOperation:
                return None

        def to_int(value):
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        vehicle = Vehicle.objects.create(
            vin=request.POST.get('vin', '').strip(),
            name=request.POST.get('name', '').strip(),
            make=request.POST.get('make', '').strip(),
            model=request.POST.get('model', '').strip(),
            color=request.POST.get('color', '').strip(),
            body_type=request.POST.get('body_type', '').strip(),
            purchase_price=to_decimal(request.POST.get('purchase_price')) or Decimal('0'),
            sale_price=to_decimal(request.POST.get('sale_price')),
            stock_count=to_int(request.POST.get('stock_count')) or 0,
            engine_type=request.POST.get('engine_type') or Vehicle.EngineType.GASOLINE,
            engine_volume=to_decimal(request.POST.get('engine_volume')),
            horsepower=to_int(request.POST.get('horsepower')),
            transmission=request.POST.get('transmission', ''),
            fuel_consumption=to_decimal(request.POST.get('fuel_consumption')),
            condition=request.POST.get('condition') or Vehicle.Condition.NEW,
            country=request.POST.get('country', '').strip(),
            trim_level=request.POST.get('trim_level') or Vehicle.TrimLevel.STANDARD,
            description=request.POST.get('description', '').strip(),
            status=request.POST.get('status') or Vehicle.VehicleStatus.FOR_SALE,
        )
        selected_options = request.POST.getlist('options')
        if selected_options:
            vehicle.options.set(options_qs.filter(id__in=selected_options))

        for photo in request.FILES.getlist('photos'):
            vehicle.media.create(
                media_type=VehicleMedia.MediaType.PHOTO,
                file=photo,
            )

        return redirect('autosalon')

    vehicles_qs = Vehicle.objects.prefetch_related('options', 'media').order_by('-created_at')[:50]
    return render(request, 'crm/autosalon.html', {'vehicles': vehicles_qs, 'options': options_qs})


def inventory(request):
    return redirect('autosalon')


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
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import (
    CashAccount,
    CashConversion,
    CurrencyRate,
    Customer,
    CustomerDocument,
    Deal,
    Lead,
    LeadSource,
    Reservation,
    Role,
    Vehicle,
    VehicleOption,
    VehicleExpense,
    VehicleMedia,
)


@login_required
def home(request):
    exchange_rate = CurrencyRate.objects.order_by('-effective_date', '-created_at').first()
    return render(request, 'crm/home.html', {'exchange_rate': exchange_rate})


@login_required
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


@login_required
def roles(request):
    roles_qs = Role.objects.select_related('permissions').order_by('name')
    return render(request, 'crm/roles.html', {'roles': roles_qs})


@login_required
def customers(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_customer':
            customer_id = request.POST.get('customer_id')
            customer = Customer.objects.filter(pk=customer_id).first()
            if customer:
                customer.full_name = request.POST.get('full_name', customer.full_name).strip() or customer.full_name
                customer.phone = request.POST.get('phone', customer.phone).strip() or customer.phone
                customer.inn = request.POST.get('inn', customer.inn).strip()
                customer.pinfl = request.POST.get('pinfl', customer.pinfl).strip()
                customer.passport_series = request.POST.get('passport_series', customer.passport_series).strip()
                customer.passport_number = request.POST.get('passport_number', customer.passport_number).strip()
                customer.passport_issued_by = request.POST.get(
                    'passport_issued_by',
                    customer.passport_issued_by,
                ).strip()
                customer.address = request.POST.get('address', customer.address).strip()
                customer.notes = request.POST.get('notes', customer.notes).strip()
                customer.save(
                    update_fields=[
                        'full_name',
                        'phone',
                        'inn',
                        'pinfl',
                        'passport_series',
                        'passport_number',
                        'passport_issued_by',
                        'address',
                        'notes',
                    ],
                )
            return redirect('customers')
        if action == 'delete_customer':
            customer_id = request.POST.get('customer_id')
            customer = Customer.objects.filter(pk=customer_id).first()
            if customer:
                customer.delete()
            return redirect('customers')
        lead_source = None
        lead_source_id = request.POST.get('lead_source')
        if lead_source_id:
            lead_source = LeadSource.objects.filter(pk=lead_source_id).first()
        customer = Customer.objects.create(
            full_name=request.POST.get('full_name', '').strip(),
            phone=request.POST.get('phone', '').strip(),
            inn=request.POST.get('inn', '').strip(),
            passport_series=request.POST.get('passport_series', '').strip(),
            passport_number=request.POST.get('passport_number', '').strip(),
            pinfl=request.POST.get('pinfl', '').strip(),
            passport_issued_by=request.POST.get('passport_issued_by', '').strip(),
            address=request.POST.get('address', '').strip(),
            lead_source=lead_source,
            notes=request.POST.get('notes', '').strip(),
            contract_number=request.POST.get('contract_number', '').strip(),
            contract_file=request.FILES.get('contract_file'),
            contract_file_second=request.FILES.get('contract_file_second'),
            power_of_attorney_file=request.FILES.get('power_of_attorney_file'),
        )
        passport_front = request.FILES.get('passport_front')
        if passport_front:
            CustomerDocument.objects.create(
                customer=customer,
                document_type=CustomerDocument.DocumentType.PASSPORT,
                file=passport_front,
                uploaded_by=request.user if request.user.is_authenticated else None,
                description='Паспорт (лицевая сторона)',
            )
        passport_back = request.FILES.get('passport_back')
        if passport_back:
            CustomerDocument.objects.create(
                customer=customer,
                document_type=CustomerDocument.DocumentType.PASSPORT,
                file=passport_back,
                uploaded_by=request.user if request.user.is_authenticated else None,
                description='Паспорт (обратная сторона)',
            )
        return redirect('customers')

    search_query = request.GET.get('q', '').strip()
    customers_qs = (
        Customer.objects.select_related('lead_source', 'assigned_manager')
        .prefetch_related('documents')
        .order_by('full_name')
    )
    if search_query:
        customers_qs = customers_qs.filter(
            Q(full_name__icontains=search_query)
            | Q(phone__icontains=search_query)
            | Q(inn__icontains=search_query)
            | Q(pinfl__icontains=search_query)
        )
    return render(
        request,
        'crm/customers.html',
        {
            'customers': customers_qs,
            'lead_sources': LeadSource.objects.order_by('name'),
            'search_query': search_query,
        },
    )


@login_required
def leads(request):
    leads_qs = Lead.objects.select_related('customer', 'stage', 'assigned_to').order_by('-created_at')[:50]
    return render(request, 'crm/leads.html', {'leads': leads_qs})


def _create_vehicle_from_form(request, options_qs):
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

    purchase_currency = request.POST.get('purchase_currency') or Vehicle.Currency.UZS
    vehicle = Vehicle.objects.create(
        vin=request.POST.get('vin', '').strip(),
        name=request.POST.get('name', '').strip(),
        make=request.POST.get('make', '').strip(),
        model=request.POST.get('model', '').strip(),
        color=request.POST.get('color', '').strip(),
        body_type=request.POST.get('body_type', '').strip(),
        purchase_price=to_decimal(request.POST.get('purchase_price')) or Decimal('0'),
        purchase_currency=purchase_currency,
        sale_price=to_decimal(request.POST.get('sale_price')),
        sale_currency=purchase_currency,
        stock_count=to_int(request.POST.get('stock_count')) or 0,
        seat_count=to_int(request.POST.get('seat_count')),
        engine_type=request.POST.get('engine_type') or Vehicle.EngineType.GASOLINE,
        engine_volume=to_decimal(request.POST.get('engine_volume')),
        horsepower=to_int(request.POST.get('horsepower')),
        transmission=request.POST.get('transmission', ''),
        fuel_consumption=to_decimal(request.POST.get('fuel_consumption')),
        condition=request.POST.get('condition') or Vehicle.Condition.NEW,
        mileage=to_int(request.POST.get('mileage')),
        country=request.POST.get('country', '').strip(),
        trim_level=request.POST.get('trim_level') or Vehicle.TrimLevel.STANDARD,
        description=request.POST.get('description', '').strip(),
        status=request.POST.get('status') or Vehicle.VehicleStatus.FOR_SALE,
        acquisition_type=request.POST.get('acquisition_type') or Vehicle.AcquisitionType.PURCHASE,
        counterparty_name=request.POST.get('counterparty_name', '').strip(),
    )
    selected_options = request.POST.getlist('options')
    if selected_options:
        vehicle.options.set(options_qs.filter(id__in=selected_options))

    for photo in request.FILES.getlist('photos'):
        vehicle.media.create(
            media_type=VehicleMedia.MediaType.PHOTO,
            file=photo,
        )
    if vehicle.acquisition_type == Vehicle.AcquisitionType.PURCHASE:
        cash_account = CashAccount.get_current()
        total_cost = (vehicle.purchase_price or Decimal('0')) * Decimal(vehicle.stock_count or 0)
        if vehicle.purchase_currency == Vehicle.Currency.USD:
            cash_account.usd_balance -= total_cost
            cash_account.save(update_fields=['usd_balance', 'updated_at'])
        else:
            cash_account.uzs_balance -= total_cost
            cash_account.save(update_fields=['uzs_balance', 'updated_at'])
        VehicleExpense.objects.create(
            vehicle=vehicle,
            category=VehicleExpense.ExpenseCategory.PURCHASE,
            amount=total_cost,
            occurred_at=timezone.now().date(),
            notes='Автоматический расход при закупе автомобиля',
        )
    return vehicle


@login_required
def autosalon(request):
    def parse_datetime_value(value, default_value=None):
        if not value:
            return default_value
        parsed = parse_datetime(value)
        if not parsed:
            return default_value
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed

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
        action = request.POST.get('action')
        if action == 'sell_vehicle':
            vehicle_id = request.POST.get('vehicle_id')
            if vehicle_id:
                vehicle = Vehicle.objects.get(pk=vehicle_id)
                active_reservation = Reservation.objects.select_related('customer').filter(
                    vehicle=vehicle,
                    status=Reservation.ReservationStatus.ACTIVE,
                ).first()
                if active_reservation:
                    customer = active_reservation.customer
                else:
                    customer_id = request.POST.get('customer_id')
                    if customer_id:
                        customer = Customer.objects.get(pk=customer_id)
                        customer.full_name = request.POST.get('full_name', customer.full_name).strip() or customer.full_name
                        customer.phone = request.POST.get('phone', customer.phone).strip() or customer.phone
                        customer.passport_series = request.POST.get('passport_series', customer.passport_series).strip()
                        customer.passport_number = request.POST.get('passport_number', customer.passport_number).strip()
                        customer.passport_issued_by = request.POST.get('passport_issued_by', customer.passport_issued_by).strip()
                        customer.address = request.POST.get('address', customer.address).strip()
                        customer.save(
                            update_fields=[
                                'full_name',
                                'phone',
                                'passport_series',
                                'passport_number',
                                'passport_issued_by',
                                'address',
                            ],
                        )
                    else:
                        customer = Customer.objects.create(
                            full_name=request.POST.get('full_name', '').strip(),
                            phone=request.POST.get('phone', '').strip(),
                            passport_series=request.POST.get('passport_series', '').strip(),
                            passport_number=request.POST.get('passport_number', '').strip(),
                            passport_issued_by=request.POST.get('passport_issued_by', '').strip(),
                            address=request.POST.get('address', '').strip(),
                        )

                sale_price = request.POST.get('sale_price')
                try:
                    sale_price_value = Decimal(sale_price) if sale_price not in (None, '') else None
                except InvalidOperation:
                    sale_price_value = None
                if sale_price_value is None:
                    sale_price_value = vehicle.sale_price or vehicle.purchase_price

                deal = Deal.objects.create(
                    customer=customer,
                    vehicle=vehicle,
                    sale_price=sale_price_value,
                    financing_type=request.POST.get('financing_type') or Deal.FinancingType.CASH,
                    status=Deal.DealStatus.COMPLETED,
                    signed_at=timezone.now(),
                    notes=request.POST.get('deal_notes', '').strip(),
                )

                cash_account = CashAccount.get_current()
                sale_currency = vehicle.sale_currency or vehicle.purchase_currency or Vehicle.Currency.UZS
                if vehicle.acquisition_type == Vehicle.AcquisitionType.CONSIGNMENT:
                    profit_amount = sale_price_value - (vehicle.purchase_price or Decimal('0'))
                    if sale_currency == Vehicle.Currency.USD:
                        cash_account.usd_balance += profit_amount
                        cash_account.save(update_fields=['usd_balance', 'updated_at'])
                    else:
                        cash_account.uzs_balance += profit_amount
                        cash_account.save(update_fields=['uzs_balance', 'updated_at'])
                else:
                    if sale_currency == Vehicle.Currency.USD:
                        cash_account.usd_balance += sale_price_value
                        cash_account.save(update_fields=['usd_balance', 'updated_at'])
                    else:
                        cash_account.uzs_balance += sale_price_value
                        cash_account.save(update_fields=['uzs_balance', 'updated_at'])

                vehicle.stock_count = max(vehicle.stock_count - 1, 0)
                if vehicle.stock_count == 0:
                    vehicle.status = Vehicle.VehicleStatus.SOLD
                elif vehicle.status != Vehicle.VehicleStatus.RESERVED:
                    vehicle.status = Vehicle.VehicleStatus.FOR_SALE
                vehicle.save(update_fields=['stock_count', 'status'])
                Reservation.objects.filter(
                    vehicle=vehicle,
                    status=Reservation.ReservationStatus.ACTIVE,
                ).update(status=Reservation.ReservationStatus.COMPLETED)

                return redirect(f"{reverse('autosalon')}?receipt={deal.pk}")
        if action == 'reserve_vehicle':
            vehicle_id = request.POST.get('vehicle_id')
            if vehicle_id:
                vehicle = Vehicle.objects.get(pk=vehicle_id)
                customer_id = request.POST.get('customer_id')
                if customer_id:
                    customer = Customer.objects.get(pk=customer_id)
                    customer.full_name = request.POST.get('full_name', customer.full_name).strip() or customer.full_name
                    customer.phone = request.POST.get('phone', customer.phone).strip() or customer.phone
                    customer.passport_series = request.POST.get('passport_series', customer.passport_series).strip()
                    customer.passport_number = request.POST.get('passport_number', customer.passport_number).strip()
                    customer.passport_issued_by = request.POST.get('passport_issued_by', customer.passport_issued_by).strip()
                    customer.address = request.POST.get('address', customer.address).strip()
                    customer.save(
                        update_fields=[
                            'full_name',
                            'phone',
                            'passport_series',
                            'passport_number',
                            'passport_issued_by',
                            'address',
                        ],
                    )
                else:
                    customer = Customer.objects.create(
                        full_name=request.POST.get('full_name', '').strip(),
                        phone=request.POST.get('phone', '').strip(),
                        passport_series=request.POST.get('passport_series', '').strip(),
                        passport_number=request.POST.get('passport_number', '').strip(),
                        passport_issued_by=request.POST.get('passport_issued_by', '').strip(),
                        address=request.POST.get('address', '').strip(),
                    )

                now = timezone.now()
                start_at = parse_datetime_value(request.POST.get('start_at'), now)
                end_at = parse_datetime_value(request.POST.get('end_at'), start_at + timedelta(days=3))
                if end_at and start_at and end_at < start_at:
                    end_at = start_at + timedelta(days=3)

                deposit_amount = request.POST.get('deposit_amount')
                try:
                    deposit_value = Decimal(deposit_amount) if deposit_amount not in (None, '') else None
                except InvalidOperation:
                    deposit_value = None

                Reservation.objects.create(
                    vehicle=vehicle,
                    customer=customer,
                    reserved_by=request.user,
                    start_at=start_at,
                    end_at=end_at,
                    deposit_amount=deposit_value,
                    deposit_terms=request.POST.get('deposit_terms', '').strip(),
                    status=Reservation.ReservationStatus.ACTIVE,
                )

                vehicle.status = Vehicle.VehicleStatus.RESERVED
                vehicle.save(update_fields=['status'])
            return redirect('autosalon')
        if action == 'cancel_reservation':
            reservation_id = request.POST.get('reservation_id')
            if reservation_id:
                reservation = Reservation.objects.select_related('vehicle').filter(
                    pk=reservation_id,
                    status=Reservation.ReservationStatus.ACTIVE,
                ).first()
                if reservation:
                    reservation.status = Reservation.ReservationStatus.CANCELED
                    reservation.save(update_fields=['status', 'updated_at'])
                    has_active = Reservation.objects.filter(
                        vehicle=reservation.vehicle,
                        status=Reservation.ReservationStatus.ACTIVE,
                    ).exists()
                    if not has_active:
                        reservation.vehicle.status = Vehicle.VehicleStatus.FOR_SALE
                        reservation.vehicle.save(update_fields=['status'])
            return redirect('autosalon')

    active_reservations = Reservation.objects.select_related('customer').filter(
        status=Reservation.ReservationStatus.ACTIVE,
    )
    vehicles_qs = (
        Vehicle.objects.prefetch_related(
            'options',
            'media',
            Prefetch('reservations', queryset=active_reservations, to_attr='active_reservations'),
        )
        .filter(status__in=[Vehicle.VehicleStatus.FOR_SALE, Vehicle.VehicleStatus.RESERVED], stock_count__gt=0)
        .order_by('-created_at')
    )
    customers_qs = Customer.objects.order_by('full_name')
    receipt_deal = None
    receipt_id = request.GET.get('receipt')
    if receipt_id:
        receipt_deal = (
            Deal.objects.select_related('customer', 'vehicle')
            .filter(pk=receipt_id)
            .first()
        )
    sold_deals = (
        Deal.objects.select_related('customer', 'vehicle')
        .filter(status=Deal.DealStatus.COMPLETED)
        .order_by('-signed_at', '-created_at')
    )
    for vehicle in vehicles_qs:
        vehicle.primary_photo = next((media for media in vehicle.media.all() if media.media_type == 'photo'), None)
        vehicle.active_reservation = next(iter(getattr(vehicle, 'active_reservations', [])), None)
    return render(
        request,
        'crm/autosalon_showroom.html',
        {
            'vehicles': vehicles_qs,
            'customers': customers_qs,
            'receipt': receipt_deal,
            'sold_deals': sold_deals,
        },
    )


@login_required
def inventory(request):
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
        action = request.POST.get('action')
        if action == 'create_vehicle':
            _create_vehicle_from_form(request, options_qs)
            return redirect('inventory')
        if action == 'return_to_autosalon':
            vehicle_id = request.POST.get('vehicle_id')
            if vehicle_id:
                vehicle = Vehicle.objects.get(pk=vehicle_id)
                if vehicle.stock_count == 0:
                    vehicle.stock_count = 1
                vehicle.status = Vehicle.VehicleStatus.FOR_SALE
                vehicle.save(update_fields=['stock_count', 'status'])
            return redirect('inventory')

    vehicles_qs = Vehicle.objects.prefetch_related('options', 'media', 'deals__customer').order_by('-created_at')[:50]
    for vehicle in vehicles_qs:
        vehicle.latest_deal = next(iter(vehicle.deals.all()), None)
    return render(
        request,
        'crm/autosalon.html',
        {
            'vehicles': vehicles_qs,
            'options': options_qs,
            'vehicles_for_sale': Vehicle.objects.filter(status=Vehicle.VehicleStatus.FOR_SALE).count(),
        },
    )


@login_required
def deals(request):
    deals_qs = Deal.objects.select_related('customer', 'vehicle', 'manager').order_by('-created_at')[:50]
    return render(request, 'crm/deals.html', {'deals': deals_qs})


@login_required
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
    recent_deals = (
        Deal.objects.select_related('vehicle', 'customer')
        .filter(status=Deal.DealStatus.COMPLETED)
        .order_by('-signed_at', '-created_at')[:10]
    )
    incomes = []
    for deal in recent_deals:
        vehicle = deal.vehicle
        sale_currency = vehicle.sale_currency or vehicle.purchase_currency or Vehicle.Currency.UZS
        if vehicle.acquisition_type == Vehicle.AcquisitionType.CONSIGNMENT:
            amount = deal.sale_price - (vehicle.purchase_price or Decimal('0'))
            income_type = 'Комиссия'
        else:
            amount = deal.sale_price
            income_type = 'Продажа авто'
        incomes.append(
            {
                'deal': deal,
                'vehicle': vehicle,
                'customer': deal.customer,
                'amount': amount,
                'currency': sale_currency,
                'income_type': income_type,
            },
        )
    return render(
        request,
        'crm/cash.html',
        {
            'cash_account': cash_account,
            'exchange_rate': exchange_rate,
            'conversions': conversions,
            'incomes': incomes,
        },
    )

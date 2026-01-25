import json
import uuid
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.http import require_POST

from .models import (
    BankAccount,
    CashAccount,
    CashConversion,
    CashEmployee,
    CurrencyRate,
    Customer,
    CustomerDocument,
    Deal,
    Lead,
    LeadSource,
    PowerOfAttorney,
    Reservation,
    Role,
    Vehicle,
    VehicleOption,
    VehicleExpense,
    VehicleMedia,
)


@login_required
def home(request):
    return redirect('autosalon')


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
                update_fields = []
                customer.full_name = request.POST.get('full_name', customer.full_name).strip() or customer.full_name
                update_fields.append('full_name')
                customer.phone = request.POST.get('phone', customer.phone).strip() or customer.phone
                update_fields.append('phone')
                customer.inn = request.POST.get('inn', customer.inn).strip()
                update_fields.append('inn')
                customer.pinfl = request.POST.get('pinfl', customer.pinfl).strip()
                update_fields.append('pinfl')
                customer.passport_series = request.POST.get('passport_series', customer.passport_series).strip()
                update_fields.append('passport_series')
                customer.passport_number = request.POST.get('passport_number', customer.passport_number).strip()
                update_fields.append('passport_number')
                passport_issued_date_value = request.POST.get('passport_issued_date')
                customer.passport_issued_date = parse_date(passport_issued_date_value) if passport_issued_date_value else None
                update_fields.append('passport_issued_date')
                customer.passport_issued_by = request.POST.get(
                    'passport_issued_by',
                    customer.passport_issued_by,
                ).strip()
                update_fields.append('passport_issued_by')
                customer.address = request.POST.get('address', customer.address).strip()
                update_fields.append('address')
                customer.notes = request.POST.get('notes', customer.notes).strip()
                update_fields.append('notes')
                customer.contract_number = request.POST.get('contract_number', customer.contract_number).strip()
                update_fields.append('contract_number')

                contract_file = request.FILES.get('contract_file')
                if contract_file:
                    customer.contract_file = contract_file
                    update_fields.append('contract_file')
                contract_file_second = request.FILES.get('contract_file_second')
                if contract_file_second:
                    customer.contract_file_second = contract_file_second
                    update_fields.append('contract_file_second')
                power_of_attorney_file = request.FILES.get('power_of_attorney_file')
                if power_of_attorney_file:
                    customer.power_of_attorney_file = power_of_attorney_file
                    update_fields.append('power_of_attorney_file')

                customer.save(update_fields=update_fields)

                passport_front = request.FILES.get('passport_front')
                if passport_front:
                    front_doc = customer.documents.filter(
                        description='Паспорт (лицевая сторона)',
                        document_type=CustomerDocument.DocumentType.PASSPORT,
                    ).first()
                    if front_doc:
                        front_doc.file = passport_front
                        front_doc.save(update_fields=['file'])
                    else:
                        CustomerDocument.objects.create(
                            customer=customer,
                            document_type=CustomerDocument.DocumentType.PASSPORT,
                            file=passport_front,
                            uploaded_by=request.user if request.user.is_authenticated else None,
                            description='Паспорт (лицевая сторона)',
                        )

                passport_back = request.FILES.get('passport_back')
                if passport_back:
                    back_doc = customer.documents.filter(
                        description='Паспорт (обратная сторона)',
                        document_type=CustomerDocument.DocumentType.PASSPORT,
                    ).first()
                    if back_doc:
                        back_doc.file = passport_back
                        back_doc.save(update_fields=['file'])
                    else:
                        CustomerDocument.objects.create(
                            customer=customer,
                            document_type=CustomerDocument.DocumentType.PASSPORT,
                            file=passport_back,
                            uploaded_by=request.user if request.user.is_authenticated else None,
                            description='Паспорт (обратная сторона)',
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
            passport_issued_date=parse_date(request.POST.get('passport_issued_date') or ''),
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

    purchase_currency = Vehicle.Currency.UZS
    name = request.POST.get('name', '').strip()
    model = request.POST.get('model', '').strip()
    make = request.POST.get('make', '').strip() or model or name
    vin = request.POST.get('vin', '').strip() or uuid.uuid4().hex[:32]
    vehicle = Vehicle.objects.create(
        vin=vin,
        name=name,
        make=make,
        model=model,
        year=to_int(request.POST.get('year')),
        color=request.POST.get('color', '').strip(),
        body_type=request.POST.get('body_type', '').strip(),
        purchase_price=to_decimal(request.POST.get('purchase_price')) or Decimal('0'),
        purchase_currency=purchase_currency,
        sale_price=to_decimal(request.POST.get('sale_price')),
        sale_currency=Vehicle.Currency.UZS,
        stock_count=to_int(request.POST.get('stock_count')) or 1,
        seat_count=to_int(request.POST.get('seat_count')),
        engine_type=request.POST.get('engine_type') or Vehicle.EngineType.GASOLINE,
        engine_volume=to_int(request.POST.get('engine_volume')),
        horsepower=to_int(request.POST.get('horsepower')),
        transmission=request.POST.get('transmission', ''),
        fuel_consumption=to_decimal(request.POST.get('fuel_consumption')),
        range_km=to_int(request.POST.get('range_km')),
        condition=request.POST.get('condition') or Vehicle.Condition.NEW,
        mileage=to_int(request.POST.get('mileage')),
        country=request.POST.get('country', '').strip(),
        model_year=to_int(request.POST.get('model_year')),
        engine_number=request.POST.get('engine_number', '').strip(),
        gross_weight=to_int(request.POST.get('gross_weight')),
        description=request.POST.get('description', '').strip(),
        status=request.POST.get('status') or Vehicle.VehicleStatus.FOR_SALE,
        acquisition_type=request.POST.get('acquisition_type') or Vehicle.AcquisitionType.PURCHASE,
        counterparty_name=request.POST.get('counterparty_name', '').strip(),
    )

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


def _update_vehicle_from_form(request, vehicle, options_qs):
    def to_decimal(value):
        if value in (None, ''):
            return None
        try:
            return Decimal(value)
        except InvalidOperation:
            return None

    def to_int(value):
        if value in (None, ''):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    update_fields = []
    vin = request.POST.get('vin', '').strip()
    if vin:
        vehicle.vin = vin
        update_fields.append('vin')
    name = request.POST.get('name', '').strip()
    if name:
        vehicle.name = name
        update_fields.append('name')
    make = request.POST.get('make', '').strip()
    if make:
        vehicle.make = make
        update_fields.append('make')
    model = request.POST.get('model', '').strip()
    if model:
        vehicle.model = model
        update_fields.append('model')

    vehicle.year = to_int(request.POST.get('year'))
    update_fields.append('year')
    vehicle.mileage = to_int(request.POST.get('mileage'))
    update_fields.append('mileage')
    vehicle.color = request.POST.get('color', '').strip()
    update_fields.append('color')
    vehicle.body_type = request.POST.get('body_type', '').strip()
    update_fields.append('body_type')
    purchase_price_value = request.POST.get('purchase_price')
    if purchase_price_value not in (None, ''):
        vehicle.purchase_price = to_decimal(purchase_price_value) or Decimal('0')
        update_fields.append('purchase_price')
    vehicle.purchase_currency = Vehicle.Currency.UZS
    update_fields.append('purchase_currency')
    sale_price_value = request.POST.get('sale_price')
    if sale_price_value not in (None, ''):
        vehicle.sale_price = to_decimal(sale_price_value)
        update_fields.append('sale_price')
    vehicle.sale_currency = Vehicle.Currency.UZS
    update_fields.append('sale_currency')
    vehicle.stock_count = to_int(request.POST.get('stock_count')) or 1
    update_fields.append('stock_count')
    vehicle.seat_count = to_int(request.POST.get('seat_count'))
    update_fields.append('seat_count')
    vehicle.engine_type = request.POST.get('engine_type') or Vehicle.EngineType.GASOLINE
    update_fields.append('engine_type')
    vehicle.engine_volume = to_int(request.POST.get('engine_volume'))
    update_fields.append('engine_volume')
    vehicle.horsepower = to_int(request.POST.get('horsepower'))
    update_fields.append('horsepower')
    vehicle.transmission = request.POST.get('transmission', '')
    update_fields.append('transmission')
    vehicle.fuel_consumption = to_decimal(request.POST.get('fuel_consumption'))
    update_fields.append('fuel_consumption')
    vehicle.range_km = to_int(request.POST.get('range_km'))
    update_fields.append('range_km')
    vehicle.condition = request.POST.get('condition') or Vehicle.Condition.NEW
    update_fields.append('condition')
    vehicle.country = request.POST.get('country', '').strip()
    update_fields.append('country')
    vehicle.model_year = to_int(request.POST.get('model_year'))
    update_fields.append('model_year')
    vehicle.engine_number = request.POST.get('engine_number', '').strip()
    update_fields.append('engine_number')
    vehicle.gross_weight = to_int(request.POST.get('gross_weight'))
    update_fields.append('gross_weight')
    vehicle.description = request.POST.get('description', '').strip()
    update_fields.append('description')
    vehicle.status = request.POST.get('status') or Vehicle.VehicleStatus.FOR_SALE
    update_fields.append('status')
    vehicle.acquisition_type = request.POST.get('acquisition_type') or Vehicle.AcquisitionType.PURCHASE
    update_fields.append('acquisition_type')
    vehicle.counterparty_name = request.POST.get('counterparty_name', '').strip()
    update_fields.append('counterparty_name')
    vehicle.arrived_at = parse_date(request.POST.get('arrived_at') or '')
    update_fields.append('arrived_at')
    vehicle.location = request.POST.get('location', '').strip()
    update_fields.append('location')
    vehicle.notes = request.POST.get('notes', '').strip()
    update_fields.append('notes')

    vehicle.save(update_fields=update_fields)
    delete_photo_ids = request.POST.getlist('delete_photos')
    if delete_photo_ids:
        VehicleMedia.objects.filter(vehicle=vehicle, id__in=delete_photo_ids).delete()

    for photo in request.FILES.getlist('photos'):
        vehicle.media.create(
            media_type=VehicleMedia.MediaType.PHOTO,
            file=photo,
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

    def parse_bool(value, default=False):
        if value is None:
            return default
        return str(value).lower() in {'1', 'true', 'on', 'yes'}

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
        if action == 'save_attorney':
            attorney_id = request.POST.get('attorney_id')
            attorney_data = {
                'trustor_name': request.POST.get('attorney_trustor_name', '').strip(),
                'company_full_text': request.POST.get('attorney_company_full_text', '').strip(),
                'vehicle_name': request.POST.get('attorney_vehicle_name', '').strip(),
                'make': request.POST.get('attorney_make', '').strip(),
                'model_year': request.POST.get('attorney_model_year', '').strip(),
                'dvs': request.POST.get('attorney_dvs', '').strip(),
                'new_status': request.POST.get('attorney_new_status', '').strip(),
                'body_number': request.POST.get('attorney_body_number', '').strip(),
                'engine_number': request.POST.get('attorney_engine_number', '').strip(),
                'engine_type': request.POST.get('attorney_engine_type', '').strip(),
                'color': request.POST.get('attorney_color', '').strip(),
                'skd': request.POST.get('attorney_skd', '').strip(),
                'engine_volume': request.POST.get('attorney_engine_volume', '').strip(),
                'euro': request.POST.get('attorney_euro', '').strip(),
                'year': request.POST.get('attorney_year', '').strip(),
                'authorized_name_1': request.POST.get('attorney_authorized_name_1', '').strip(),
                'passport_1': request.POST.get('attorney_passport_1', '').strip(),
                'passport_issued_date_1': parse_date(request.POST.get('attorney_passport_issued_date_1') or ''),
                'passport_issued_by_1': request.POST.get('attorney_passport_issued_1', '').strip(),
                'authorized_name_2': request.POST.get('attorney_authorized_name_2', '').strip(),
                'passport_2': request.POST.get('attorney_passport_2', '').strip(),
                'passport_issued_date_2': parse_date(request.POST.get('attorney_passport_issued_date_2') or ''),
                'passport_issued_by_2': request.POST.get('attorney_passport_issued_2', '').strip(),
                'authorized_name_3': request.POST.get('attorney_authorized_name_3', '').strip(),
                'passport_3': request.POST.get('attorney_passport_3', '').strip(),
                'passport_issued_date_3': parse_date(request.POST.get('attorney_passport_issued_date_3') or ''),
                'passport_issued_by_3': request.POST.get('attorney_passport_issued_3', '').strip(),
                'start_date': parse_date(request.POST.get('attorney_start_date') or ''),
                'expiry_date': parse_date(request.POST.get('attorney_expiry') or ''),
                'logo_text': request.POST.get('attorney_logo_text', '').strip(),
                'logo_text_bold': parse_bool(request.POST.get('attorney_logo_text_bold')),
                'logo_text_italic': parse_bool(request.POST.get('attorney_logo_text_italic')),
                'logo_text_underline': parse_bool(request.POST.get('attorney_logo_text_underline')),
                'logo_width': request.POST.get('attorney_logo_width', '').strip(),
                'logo_font_size': request.POST.get('attorney_logo_font_size', '').strip(),
                'logo_align': request.POST.get('attorney_logo_align', '').strip(),
                'logo_margin_top': request.POST.get('attorney_logo_margin_top', '').strip(),
                'logo_margin_bottom': request.POST.get('attorney_logo_margin_bottom', '').strip(),
                'logo_show_image': parse_bool(request.POST.get('attorney_logo_show_image')),
                'logo_image_data': request.POST.get('attorney_logo_image_data', '').strip(),
                'address_text': request.POST.get('attorney_address_text', '').strip(),
                'header_city': request.POST.get('attorney_header_city', '').strip(),
                'address_font_size': request.POST.get('attorney_address_font_size', '').strip(),
                'address_bold': parse_bool(request.POST.get('attorney_address_bold')),
                'address_italic': parse_bool(request.POST.get('attorney_address_italic')),
                'address_underline': parse_bool(request.POST.get('attorney_address_underline')),
                'doc_text': request.POST.get('attorney_doc_text', '').strip(),
                'doc_show_image': parse_bool(request.POST.get('attorney_doc_show_image')),
                'doc_image_width': request.POST.get('attorney_doc_image_width', '').strip(),
                'doc_font_size': request.POST.get('attorney_doc_font_size', '').strip(),
                'doc_justify': request.POST.get('attorney_doc_justify', '').strip(),
                'doc_margin_top': request.POST.get('attorney_doc_margin_top', '').strip(),
                'doc_text_align': request.POST.get('attorney_doc_text_align', '').strip(),
                'doc_image_data': request.POST.get('attorney_doc_image_data', '').strip(),
            }
            attorney = PowerOfAttorney.objects.filter(pk=attorney_id).first() if attorney_id else None
            if attorney:
                for field, value in attorney_data.items():
                    setattr(attorney, field, value)
                if request.user.is_authenticated and attorney.created_by_id is None:
                    attorney.created_by = request.user
                attorney.save()
            else:
                attorney = PowerOfAttorney.objects.create(
                    created_by=request.user if request.user.is_authenticated else None,
                    **attorney_data,
                )
            return redirect(f"{reverse('autosalon')}?attorney_id={attorney.pk}#autosalon-attorney")
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
                        passport_issued_date_value = request.POST.get('passport_issued_date')
                        if passport_issued_date_value:
                            customer.passport_issued_date = parse_date(passport_issued_date_value)
                        customer.passport_issued_by = request.POST.get('passport_issued_by', customer.passport_issued_by).strip()
                        customer.address = request.POST.get('address', customer.address).strip()
                        customer.save(
                            update_fields=[
                                'full_name',
                                'phone',
                                'passport_series',
                                'passport_number',
                                'passport_issued_date',
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
                            passport_issued_date=parse_date(request.POST.get('passport_issued_date') or ''),
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

                manager = None
                manager_name = request.POST.get('manager_name', '').strip()
                if request.user.is_authenticated:
                    current_user_name = request.user.get_full_name() or request.user.get_username()
                    if not manager_name:
                        manager_name = current_user_name
                    if manager_name == current_user_name:
                        manager = request.user

                deal = Deal.objects.create(
                    customer=customer,
                    vehicle=vehicle,
                    manager=manager,
                    sold_by_name=manager_name,
                    sale_price=sale_price_value,
                    financing_type=request.POST.get('financing_type') or Deal.FinancingType.CASH,
                    status=Deal.DealStatus.COMPLETED,
                    signed_at=timezone.now(),
                    notes=request.POST.get('deal_notes', '').strip(),
                )

                cash_account = CashAccount.get_current()
                bank_account = BankAccount.get_current()
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
                    financing_type = request.POST.get('financing_type') or Deal.FinancingType.CASH
                    down_payment_value = request.POST.get('down_payment_amount')
                    try:
                        down_payment = Decimal(down_payment_value) if down_payment_value not in (None, '') else Decimal('0')
                    except InvalidOperation:
                        down_payment = Decimal('0')
                    if down_payment < 0:
                        down_payment = Decimal('0')
                    if down_payment > sale_price_value:
                        down_payment = sale_price_value
                    if financing_type == Deal.FinancingType.CREDIT:
                        if sale_currency == Vehicle.Currency.USD:
                            cash_account.usd_balance += down_payment
                            cash_account.save(update_fields=['usd_balance', 'updated_at'])
                        else:
                            cash_account.uzs_balance += down_payment
                            cash_account.save(update_fields=['uzs_balance', 'updated_at'])

                        remaining_amount = sale_price_value - down_payment
                        bank_rate_used = None
                        bank_amount_uzs = Decimal('0')
                        if remaining_amount > 0:
                            if sale_currency == Vehicle.Currency.USD:
                                posted_rate_value = request.POST.get('bank_rate_used')
                                try:
                                    posted_rate = (
                                        Decimal(posted_rate_value)
                                        if posted_rate_value not in (None, '')
                                        else None
                                    )
                                except InvalidOperation:
                                    posted_rate = None
                                if posted_rate and posted_rate > 0:
                                    bank_rate_used = posted_rate
                                    bank_amount_uzs = remaining_amount * posted_rate
                                else:
                                    exchange_rate = CurrencyRate.objects.order_by('-effective_date', '-created_at').first()
                                    if exchange_rate:
                                        bank_rate_used = exchange_rate.rate
                                        bank_amount_uzs = remaining_amount * exchange_rate.rate
                            else:
                                bank_amount_uzs = remaining_amount

                        if bank_amount_uzs > 0:
                            bank_account.uzs_balance += bank_amount_uzs
                            bank_account.save(update_fields=['uzs_balance', 'updated_at'])

                        deal.down_payment_amount = down_payment
                        deal.bank_transfer_amount_uzs = bank_amount_uzs
                        deal.bank_rate_used = bank_rate_used
                        deal.save(update_fields=['down_payment_amount', 'bank_transfer_amount_uzs', 'bank_rate_used'])
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
                    passport_issued_date_value = request.POST.get('passport_issued_date')
                    if passport_issued_date_value:
                        customer.passport_issued_date = parse_date(passport_issued_date_value)
                    customer.passport_issued_by = request.POST.get('passport_issued_by', customer.passport_issued_by).strip()
                    customer.address = request.POST.get('address', customer.address).strip()
                    customer.save(
                        update_fields=[
                            'full_name',
                            'phone',
                            'passport_series',
                            'passport_number',
                            'passport_issued_date',
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
                        passport_issued_date=parse_date(request.POST.get('passport_issued_date') or ''),
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

                reserved_by = None
                reserved_by_name = request.POST.get('reserved_by_name', '').strip()
                if request.user.is_authenticated:
                    current_user_name = request.user.get_full_name() or request.user.get_username()
                    if not reserved_by_name:
                        reserved_by_name = current_user_name
                    if reserved_by_name == current_user_name:
                        reserved_by = request.user

                Reservation.objects.create(
                    vehicle=vehicle,
                    customer=customer,
                    reserved_by=reserved_by,
                    reserved_by_name=reserved_by_name,
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

    active_reservations = Reservation.objects.select_related('customer', 'reserved_by').filter(
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
            Deal.objects.select_related('customer', 'vehicle', 'manager')
            .filter(pk=receipt_id)
            .first()
        )
    sold_deals = (
        Deal.objects.select_related('customer', 'vehicle', 'manager')
        .filter(status=Deal.DealStatus.COMPLETED)
        .order_by('-signed_at', '-created_at')
    )
    power_of_attorneys = PowerOfAttorney.objects.order_by('-updated_at')
    attorney_data = []
    for record in power_of_attorneys:
        attorney_data.append(
            {
                'id': record.pk,
                'trustor_name': record.trustor_name,
                'company_full_text': record.company_full_text,
                'vehicle_name': record.vehicle_name,
                'make': record.make,
                'model_year': record.model_year,
                'dvs': record.dvs,
                'new_status': record.new_status,
                'body_number': record.body_number,
                'engine_number': record.engine_number,
                'engine_type': record.engine_type,
                'color': record.color,
                'skd': record.skd,
                'engine_volume': record.engine_volume,
                'euro': record.euro,
                'year': record.year,
                'authorized_name_1': record.authorized_name_1,
                'passport_1': record.passport_1,
                'passport_issued_date_1': record.passport_issued_date_1.isoformat()
                if record.passport_issued_date_1
                else '',
                'passport_issued_by_1': record.passport_issued_by_1,
                'authorized_name_2': record.authorized_name_2,
                'passport_2': record.passport_2,
                'passport_issued_date_2': record.passport_issued_date_2.isoformat()
                if record.passport_issued_date_2
                else '',
                'passport_issued_by_2': record.passport_issued_by_2,
                'authorized_name_3': record.authorized_name_3,
                'passport_3': record.passport_3,
                'passport_issued_date_3': record.passport_issued_date_3.isoformat()
                if record.passport_issued_date_3
                else '',
                'passport_issued_by_3': record.passport_issued_by_3,
                'start_date': record.start_date.isoformat() if record.start_date else '',
                'expiry_date': record.expiry_date.isoformat() if record.expiry_date else '',
                'logo_text': record.logo_text,
                'logo_text_bold': record.logo_text_bold,
                'logo_text_italic': record.logo_text_italic,
                'logo_text_underline': record.logo_text_underline,
                'logo_width': record.logo_width,
                'logo_font_size': record.logo_font_size,
                'logo_align': record.logo_align,
                'logo_margin_top': record.logo_margin_top,
                'logo_margin_bottom': record.logo_margin_bottom,
                'logo_show_image': record.logo_show_image,
                'logo_image_data': record.logo_image_data,
                'address_text': record.address_text,
                'header_city': record.header_city,
                'address_font_size': record.address_font_size,
                'address_bold': record.address_bold,
                'address_italic': record.address_italic,
                'address_underline': record.address_underline,
                'doc_text': record.doc_text,
                'doc_show_image': record.doc_show_image,
                'doc_image_width': record.doc_image_width,
                'doc_font_size': record.doc_font_size,
                'doc_justify': record.doc_justify,
                'doc_margin_top': record.doc_margin_top,
                'doc_text_align': record.doc_text_align,
                'doc_image_data': record.doc_image_data,
            },
        )
    for vehicle in vehicles_qs:
        vehicle.primary_photo = next((media for media in vehicle.media.all() if media.media_type == 'photo'), None)
        vehicle.active_reservation = next(iter(getattr(vehicle, 'active_reservations', [])), None)
    selected_attorney_id = request.GET.get('attorney_id')
    return render(
        request,
        'crm/autosalon_showroom.html',
        {
            'vehicles': vehicles_qs,
            'customers': customers_qs,
            'receipt': receipt_deal,
            'sold_deals': sold_deals,
            'power_of_attorneys': power_of_attorneys,
            'attorney_data': attorney_data,
            'selected_attorney_id': selected_attorney_id,
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
        if action == 'update_vehicle':
            vehicle_id = request.POST.get('vehicle_id')
            if vehicle_id:
                vehicle = Vehicle.objects.filter(pk=vehicle_id).first()
                if vehicle:
                    _update_vehicle_from_form(request, vehicle, options_qs)
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
    bank_account = BankAccount.get_current()
    if request.method == 'POST' and request.user.is_superuser:
        action = request.POST.get('action')
        try:
            if action == 'update_bank_account':
                bank_account.uzs_balance = Decimal(request.POST.get('bank_uzs_balance', bank_account.uzs_balance))
                bank_account.usd_balance = Decimal(request.POST.get('bank_usd_balance', bank_account.usd_balance))
                bank_account.updated_by = request.user
                bank_account.save(update_fields=['uzs_balance', 'usd_balance', 'updated_by', 'updated_at'])
                return redirect('/cash/?reset_cash=1')
            if action == 'transfer_bank_cash':
                direction = request.POST.get('transfer_direction')
                currency = request.POST.get('transfer_currency')
                amount = Decimal(request.POST.get('transfer_amount', '0'))
                if amount <= 0:
                    return redirect('/cash/?reset_cash=1')
                if direction == 'bank_to_cash':
                    source_account = bank_account
                    target_account = cash_account
                elif direction == 'cash_to_bank':
                    source_account = cash_account
                    target_account = bank_account
                else:
                    return redirect('/cash/?reset_cash=1')

                if currency == 'usd':
                    if source_account.usd_balance < amount:
                        return redirect('/cash/?reset_cash=1')
                    source_account.usd_balance -= amount
                    target_account.usd_balance += amount
                else:
                    if source_account.uzs_balance < amount:
                        return redirect('/cash/?reset_cash=1')
                    source_account.uzs_balance -= amount
                    target_account.uzs_balance += amount
                source_account.updated_by = request.user
                target_account.updated_by = request.user
                source_account.save(update_fields=['uzs_balance', 'usd_balance', 'updated_by', 'updated_at'])
                target_account.save(update_fields=['uzs_balance', 'usd_balance', 'updated_by', 'updated_at'])
                return redirect('/cash/?reset_cash=1')
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
            'bank_account': bank_account,
            'exchange_rate': exchange_rate,
            'conversions': conversions,
            'incomes': incomes,
        },
    )


@login_required
@require_POST
def cash_employee_save(request):
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid_json'}, status=400)

    external_id = str(payload.get('id') or '').strip()
    if not external_id:
        return JsonResponse({'error': 'missing_id'}, status=400)

    start_date_value = payload.get('startDate')
    start_date = None
    if start_date_value:
        try:
            start_date = date.fromisoformat(start_date_value)
        except ValueError:
            start_date = None

    salary_day_value = payload.get('salaryDay')
    salary_day = None
    if salary_day_value not in (None, ''):
        try:
            salary_day = int(salary_day_value)
        except (TypeError, ValueError):
            salary_day = None

    salary_amount_value = payload.get('salaryAmount')
    salary_amount = None
    if salary_amount_value not in (None, ''):
        try:
            salary_amount = Decimal(str(salary_amount_value))
        except (InvalidOperation, TypeError, ValueError):
            salary_amount = None

    defaults = {
        'first_name': (payload.get('firstName') or '').strip(),
        'last_name': (payload.get('lastName') or '').strip(),
        'position': (payload.get('position') or '').strip(),
        'start_date': start_date,
        'phone_primary': (payload.get('phonePrimary') or '').strip(),
        'phone_secondary': (payload.get('phoneSecondary') or '').strip(),
        'salary_day': salary_day,
        'salary_amount': salary_amount,
        'status': (payload.get('status') or '').strip(),
        'updated_by': request.user,
    }

    employee, created = CashEmployee.objects.update_or_create(
        external_id=external_id,
        defaults=defaults,
    )
    if created and not employee.created_by:
        employee.created_by = request.user
        employee.save(update_fields=['created_by'])

    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def cash_employee_delete(request):
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid_json'}, status=400)

    external_id = str(payload.get('id') or '').strip()
    if not external_id:
        return JsonResponse({'error': 'missing_id'}, status=400)

    CashEmployee.objects.filter(external_id=external_id).delete()
    return JsonResponse({'status': 'ok'})
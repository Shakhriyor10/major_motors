from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Role(models.Model):
    class RoleName(models.TextChoices):
        ADMIN = 'admin', 'Админ'
        SALES_HEAD = 'sales_head', 'Руководитель отдела продаж'
        MANAGER = 'manager', 'Менеджер'
        CREDIT_SPECIALIST = 'credit_specialist', 'Кредитный специалист'
        ACCOUNTANT = 'accountant', 'Бухгалтер'
        LOGISTICS = 'logistics', 'Склад/логистика'
        SERVICE = 'service', 'Сервис/СТО'

    name = models.CharField(max_length=64, choices=RoleName.choices, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.get_name_display()


class RolePermission(models.Model):
    role = models.OneToOneField(Role, on_delete=models.CASCADE, related_name='permissions')
    can_view_finance = models.BooleanField(default=False)
    can_edit_prices = models.BooleanField(default=False)
    can_delete_deals = models.BooleanField(default=False)
    can_export_data = models.BooleanField(default=False)
    can_manage_inventory = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    can_access_documents = models.BooleanField(default=False)

    def __str__(self):
        return f'Права: {self.role.get_name_display()}'


class EmployeeProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.user} ({self.role.get_name_display()})'


class AuditEntry(models.Model):
    class ActionType(models.TextChoices):
        CREATE = 'create', 'Создание'
        UPDATE = 'update', 'Обновление'
        DELETE = 'delete', 'Удаление'
        LOGIN = 'login', 'Вход'
        EXPORT = 'export', 'Экспорт'

    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=32, choices=ActionType.choices)
    model_name = models.CharField(max_length=128)
    object_id = models.CharField(max_length=64)
    summary = models.CharField(max_length=255, blank=True)
    changes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_action_display()} {self.model_name} #{self.object_id}'


class LeadSource(models.Model):
    name = models.CharField(max_length=128, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class LeadStage(models.Model):
    name = models.CharField(max_length=128, unique=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_won = models.BooleanField(default=False)
    is_lost = models.BooleanField(default=False)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class LossReason(models.Model):
    name = models.CharField(max_length=128, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Customer(TimeStampedModel):
    class PurchaseType(models.TextChoices):
        CASH = 'cash', 'Наличные'
        CREDIT = 'credit', 'Кредит'
        LEASE = 'lease', 'Лизинг'
        TRADE_IN = 'trade_in', 'Обмен/трейд-ин'

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32)
    telegram = models.CharField(max_length=64, blank=True)
    instagram = models.CharField(max_length=64, blank=True)
    lead_source = models.ForeignKey(LeadSource, on_delete=models.SET_NULL, null=True, blank=True)
    preferred_make = models.CharField(max_length=128, blank=True)
    preferred_model = models.CharField(max_length=128, blank=True)
    preferred_year = models.PositiveIntegerField(null=True, blank=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    purchase_type = models.CharField(max_length=32, choices=PurchaseType.choices, blank=True)
    assigned_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customers',
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.full_name


class CustomerDocument(TimeStampedModel):
    class DocumentType(models.TextChoices):
        PASSPORT = 'passport', 'Паспорт'
        INCOME = 'income', 'Справка о доходах'
        CONSENT = 'consent', 'Согласие'
        OTHER = 'other', 'Другое'

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=32, choices=DocumentType.choices)
    file = models.FileField(upload_to='customer_documents/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    restricted_to_role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f'{self.get_document_type_display()} - {self.customer.full_name}'


class Interaction(TimeStampedModel):
    class InteractionType(models.TextChoices):
        CALL = 'call', 'Звонок'
        MESSAGE = 'message', 'Сообщение'
        MEETING = 'meeting', 'Встреча'

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='interactions')
    lead = models.ForeignKey('Lead', on_delete=models.SET_NULL, null=True, blank=True)
    interaction_type = models.CharField(max_length=32, choices=InteractionType.choices)
    channel = models.CharField(max_length=64, blank=True)
    summary = models.TextField(blank=True)
    occurred_at = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-occurred_at']

    def __str__(self):
        return f'{self.customer.full_name}: {self.get_interaction_type_display()}'


class ReminderTask(TimeStampedModel):
    class TaskStatus(models.TextChoices):
        OPEN = 'open', 'Открыта'
        IN_PROGRESS = 'in_progress', 'В работе'
        DONE = 'done', 'Выполнена'
        CANCELED = 'canceled', 'Отменена'

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    lead = models.ForeignKey('Lead', on_delete=models.SET_NULL, null=True, blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    due_at = models.DateTimeField()
    status = models.CharField(max_length=32, choices=TaskStatus.choices, default=TaskStatus.OPEN)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tasks',
    )

    def __str__(self):
        return self.title


class Lead(TimeStampedModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='leads')
    stage = models.ForeignKey(LeadStage, on_delete=models.PROTECT)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    source = models.ForeignKey(LeadSource, on_delete=models.SET_NULL, null=True, blank=True)
    loss_reason = models.ForeignKey(LossReason, on_delete=models.SET_NULL, null=True, blank=True)
    sla_minutes = models.PositiveIntegerField(default=10)
    first_response_at = models.DateTimeField(null=True, blank=True)
    last_contact_at = models.DateTimeField(null=True, blank=True)
    auto_assigned = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'Лид #{self.pk} - {self.customer.full_name}'


class Vehicle(TimeStampedModel):
    class VehicleStatus(models.TextChoices):
        IN_TRANSIT = 'in_transit', 'В пути'
        IN_STOCK = 'in_stock', 'На складе'
        ON_SHOW = 'on_show', 'На показе'
        RESERVED = 'reserved', 'Забронировано'
        SOLD = 'sold', 'Продано'
        SERVICE = 'service', 'На сервисе'

    class AcquisitionType(models.TextChoices):
        PURCHASE = 'purchase', 'Закуп'
        TRADE_IN = 'trade_in', 'Трейд-ин'
        CONSIGNMENT = 'consignment', 'Комиссия'

    vin = models.CharField(max_length=32, unique=True)
    make = models.CharField(max_length=128)
    model = models.CharField(max_length=128)
    year = models.PositiveIntegerField()
    mileage = models.PositiveIntegerField()
    color = models.CharField(max_length=64, blank=True)
    trim = models.CharField(max_length=128, blank=True)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=32, choices=VehicleStatus.choices, default=VehicleStatus.IN_STOCK)
    acquisition_type = models.CharField(max_length=32, choices=AcquisitionType.choices)
    arrived_at = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=128, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.make} {self.model} ({self.vin})'


class VehicleMedia(TimeStampedModel):
    class MediaType(models.TextChoices):
        PHOTO = 'photo', 'Фото'
        VIDEO = 'video', 'Видео'

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='media')
    media_type = models.CharField(max_length=16, choices=MediaType.choices)
    file = models.FileField(upload_to='vehicle_media/')
    description = models.TextField(blank=True)

    def __str__(self):
        return f'{self.vehicle} - {self.get_media_type_display()}'


class VehicleDefect(TimeStampedModel):
    class Severity(models.TextChoices):
        LOW = 'low', 'Низкая'
        MEDIUM = 'medium', 'Средняя'
        HIGH = 'high', 'Высокая'

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='defects')
    description = models.TextField()
    severity = models.CharField(max_length=16, choices=Severity.choices)
    detected_at = models.DateField(null=True, blank=True)

    def __str__(self):
        return f'{self.vehicle} - {self.get_severity_display()}'


class TradeInRecord(TimeStampedModel):
    vehicle = models.OneToOneField(Vehicle, on_delete=models.CASCADE, related_name='trade_in_record')
    appraised_value = models.DecimalField(max_digits=12, decimal_places=2)
    previous_owners_count = models.PositiveIntegerField(default=0)
    inspection_report = models.TextField(blank=True)
    evaluated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f'Трейд-ин {self.vehicle}'


class Reservation(TimeStampedModel):
    class ReservationStatus(models.TextChoices):
        ACTIVE = 'active', 'Активна'
        EXPIRED = 'expired', 'Истекла'
        CANCELED = 'canceled', 'Отменена'
        COMPLETED = 'completed', 'Завершена'

    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name='reservations')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    reserved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    deposit_terms = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=ReservationStatus.choices, default=ReservationStatus.ACTIVE)

    def __str__(self):
        return f'Бронь {self.vehicle} для {self.customer.full_name}'


class TestDrive(TimeStampedModel):
    class TestDriveStatus(models.TextChoices):
        PLANNED = 'planned', 'Запланирован'
        COMPLETED = 'completed', 'Завершен'
        CANCELED = 'canceled', 'Отменен'

    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=TestDriveStatus.choices, default=TestDriveStatus.PLANNED)
    signed_document = models.FileField(upload_to='test_drives/', blank=True)
    checklist_before = models.TextField(blank=True)
    checklist_after = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'Тест-драйв {self.vehicle} для {self.customer.full_name}'


class Deal(TimeStampedModel):
    class DealStatus(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        NEGOTIATION = 'negotiation', 'Переговоры'
        SIGNED = 'signed', 'Подписан'
        COMPLETED = 'completed', 'Завершен'
        CANCELED = 'canceled', 'Отменен'

    class FinancingType(models.TextChoices):
        CASH = 'cash', 'Наличные'
        CREDIT = 'credit', 'Кредит'
        LEASE = 'lease', 'Лизинг'
        TRADE_IN = 'trade_in', 'Трейд-ин'

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='deals')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name='deals')
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=16, choices=DealStatus.choices, default=DealStatus.DRAFT)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    financing_type = models.CharField(max_length=16, choices=FinancingType.choices)
    trade_in_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'Сделка #{self.pk} - {self.customer.full_name}'


class DealExtra(TimeStampedModel):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='extras')
    name = models.CharField(max_length=128)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f'{self.name} ({self.deal_id})'


class DealDocument(TimeStampedModel):
    class DocumentType(models.TextChoices):
        CONTRACT = 'contract', 'Договор купли-продажи'
        INVOICE = 'invoice', 'Счет'
        TRANSFER = 'transfer', 'Акт передачи'
        RECEIPT = 'receipt', 'Расписка'
        POWER_OF_ATTORNEY = 'power_of_attorney', 'Доверенность'
        OTHER = 'other', 'Другое'

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=32, choices=DocumentType.choices)
    file = models.FileField(upload_to='deal_documents/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'{self.get_document_type_display()} для сделки {self.deal_id}'


class Payment(TimeStampedModel):
    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'Наличные'
        CARD = 'card', 'Карта'
        TRANSFER = 'transfer', 'Перевод'

    class PaymentKind(models.TextChoices):
        DEPOSIT = 'deposit', 'Предоплата'
        ADDITIONAL = 'additional', 'Доплата'
        FINAL = 'final', 'Финальный платеж'
        REFUND = 'refund', 'Возврат'

    class PaymentStatus(models.TextChoices):
        PLANNED = 'planned', 'Запланирован'
        PAID = 'paid', 'Оплачен'
        OVERDUE = 'overdue', 'Просрочен'

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=16, choices=PaymentMethod.choices)
    payment_kind = models.CharField(max_length=16, choices=PaymentKind.choices)
    status = models.CharField(max_length=16, choices=PaymentStatus.choices, default=PaymentStatus.PLANNED)
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'Платеж {self.amount} по сделке {self.deal_id}'


class VehicleExpense(TimeStampedModel):
    class ExpenseCategory(models.TextChoices):
        DELIVERY = 'delivery', 'Доставка'
        REPAIR = 'repair', 'Ремонт'
        DETAILING = 'detailing', 'Химчистка'
        COMMISSION = 'commission', 'Комиссия'
        PENALTY = 'penalty', 'Штрафы'
        OTHER = 'other', 'Другое'

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='expenses')
    deal = models.ForeignKey(Deal, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.CharField(max_length=16, choices=ExpenseCategory.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    occurred_at = models.DateField()
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'{self.get_category_display()} {self.amount}'


class CashShift(TimeStampedModel):
    opened_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='opened_shifts')
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='closed_shifts')
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'Смена кассы #{self.pk}'


class CreditApplication(TimeStampedModel):
    class CreditStatus(models.TextChoices):
        SENT = 'sent', 'Отправлено'
        APPROVED = 'approved', 'Одобрено'
        DECLINED = 'declined', 'Отказ'
        IN_REVIEW = 'in_review', 'На рассмотрении'

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='credit_applications')
    deal = models.ForeignKey(Deal, on_delete=models.SET_NULL, null=True, blank=True)
    bank_name = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=CreditStatus.choices, default=CreditStatus.IN_REVIEW)
    requested_amount = models.DecimalField(max_digits=12, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    term_months = models.PositiveIntegerField()
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    monthly_payment = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'Кредит {self.bank_name} ({self.customer.full_name})'


class CreditPaymentSchedule(TimeStampedModel):
    class ScheduleStatus(models.TextChoices):
        PLANNED = 'planned', 'Запланирован'
        PAID = 'paid', 'Оплачен'
        OVERDUE = 'overdue', 'Просрочен'

    credit_application = models.ForeignKey(
        CreditApplication,
        on_delete=models.CASCADE,
        related_name='payment_schedule',
    )
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=16, choices=ScheduleStatus.choices, default=ScheduleStatus.PLANNED)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Платеж по кредиту {self.credit_application_id}'


class InsurancePolicy(TimeStampedModel):
    class PolicyType(models.TextChoices):
        OSAGO = 'osago', 'ОСАГО'
        KASKO = 'kasko', 'КАСКО'
        OTHER = 'other', 'Другое'

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='insurance_policies')
    deal = models.ForeignKey(Deal, on_delete=models.SET_NULL, null=True, blank=True)
    policy_type = models.CharField(max_length=16, choices=PolicyType.choices)
    insurer = models.CharField(max_length=128, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    premium = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'{self.get_policy_type_display()} для {self.customer.full_name}'


class Warranty(TimeStampedModel):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='warranties')
    provider = models.CharField(max_length=128)
    start_date = models.DateField()
    end_date = models.DateField()
    terms = models.TextField(blank=True)

    def __str__(self):
        return f'Гарантия {self.provider} для сделки {self.deal_id}'


class AddonSale(TimeStampedModel):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='addons')
    name = models.CharField(max_length=128)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f'{self.name} ({self.deal_id})'


class ServiceOrder(TimeStampedModel):
    class ServiceStatus(models.TextChoices):
        OPEN = 'open', 'Открыт'
        IN_PROGRESS = 'in_progress', 'В работе'
        CLOSED = 'closed', 'Закрыт'
        CANCELED = 'canceled', 'Отменен'

    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name='service_orders')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=ServiceStatus.choices, default=ServiceStatus.OPEN)
    mileage = models.PositiveIntegerField(null=True, blank=True)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'Заказ-наряд {self.vehicle}'


class ServiceItem(TimeStampedModel):
    service_order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name='items')
    description = models.TextField()
    cost = models.DecimalField(max_digits=12, decimal_places=2)
    labor_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    parts = models.TextField(blank=True)

    def __str__(self):
        return f'Работа {self.service_order_id}'

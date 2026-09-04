from django.contrib import admin

from . import models


admin.site.site_header = 'Major Motors — управление'
admin.site.site_title = 'Major Motors'
admin.site.index_title = 'Панель управления'
admin.site.enable_nav_sidebar = True
admin.ModelAdmin.list_per_page = 50
admin.ModelAdmin.save_on_top = True
admin.ModelAdmin.empty_value_display = '—'

FIELD_TITLES = {
    'id': 'ID', 'name': 'Название', 'description': 'Описание', 'status': 'Статус',
    'created_at': 'Создано', 'updated_at': 'Изменено', 'created_by': 'Создал',
    'updated_by': 'Изменил', 'user': 'Пользователь', 'role': 'Роль', 'phone': 'Телефон',
    'is_active': 'Активен', 'actor': 'Пользователь', 'action': 'Действие',
    'model_name': 'Раздел', 'object_id': 'ID объекта', 'summary': 'Описание действия',
    'order': 'Порядок', 'is_won': 'Успешный этап', 'is_lost': 'Проигранный этап',
    'full_name': 'ФИО', 'inn': 'ИНН', 'pinfl': 'ПИНФЛ', 'lead_source': 'Источник',
    'assigned_manager': 'Менеджер', 'purchase_type': 'Тип покупки', 'customer': 'Клиент',
    'document_type': 'Тип документа', 'uploaded_by': 'Загрузил',
    'restricted_to_role': 'Доступ для роли', 'interaction_type': 'Тип взаимодействия',
    'occurred_at': 'Дата взаимодействия', 'title': 'Название', 'assigned_to': 'Ответственный',
    'due_at': 'Срок', 'stage': 'Этап', 'sla_minutes': 'SLA, минут',
    'auto_assigned': 'Назначен автоматически', 'visit_date': 'Дата посещения',
    'visit_count': 'Посещений', 'last_call_at': 'Последний звонок', 'call_count': 'Звонков',
    'employee': 'Менеджер', 'next_action_date': 'Следующее действие',
    'next_action_notified_date': 'Уведомление отправлено для даты', 'vin': 'VIN',
    'make': 'Марка', 'model': 'Модель', 'year': 'Год', 'purchase_price': 'Цена закупки',
    'sale_price': 'Цена продажи', 'stock_count': 'Количество', 'acquisition_type': 'Тип поступления',
    'media_type': 'Тип файла', 'vehicle': 'Автомобиль', 'severity': 'Серьёзность',
    'detected_at': 'Дата обнаружения', 'appraised_value': 'Оценочная стоимость',
    'previous_owners_count': 'Количество владельцев', 'evaluated_by': 'Оценил',
    'reserved_by': 'Забронировал', 'reserved_by_name': 'Имя менеджера', 'start_at': 'Начало',
    'end_at': 'Окончание', 'manager': 'Менеджер', 'scheduled_at': 'Запланировано',
    'financing_type': 'Форма оплаты', 'down_payment_amount': 'Первоначальный взнос',
    'bank_transfer_amount_uzs': 'Банковский перевод, UZS', 'last_name': 'Фамилия',
    'first_name': 'Имя', 'position': 'Должность', 'phone_primary': 'Основной телефон',
    'start_date': 'Дата начала', 'deal': 'Сделка', 'price': 'Цена', 'amount': 'Сумма',
    'method': 'Способ оплаты', 'payment_kind': 'Тип платежа', 'due_date': 'Срок оплаты',
    'category': 'Категория', 'uzs_balance': 'Остаток UZS', 'usd_balance': 'Остаток USD',
    'opened_by': 'Открыл', 'opened_at': 'Открыта', 'closed_at': 'Закрыта',
    'opening_balance': 'Начальный остаток', 'closing_balance': 'Конечный остаток',
    'base_currency': 'Базовая валюта', 'quote_currency': 'Валюта курса', 'rate': 'Курс',
    'effective_date': 'Дата курса', 'shift': 'Смена', 'from_currency': 'Из валюты',
    'to_currency': 'В валюту', 'amount_from': 'Отдано', 'amount_to': 'Получено',
    'bank_name': 'Банк', 'requested_amount': 'Запрошено', 'approved_amount': 'Одобрено',
    'credit_application': 'Кредитная заявка', 'policy_type': 'Тип полиса',
    'premium': 'Страховая премия', 'provider': 'Поставщик', 'service_order': 'Заказ сервиса',
    'total_cost': 'Общая стоимость', 'cost': 'Стоимость', 'labor_hours': 'Часы работы',
}


class RussianModelAdmin(admin.ModelAdmin):
    """Translate field captions in admin without modifying database migrations."""

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if formfield and db_field.name in FIELD_TITLES:
            formfield.label = FIELD_TITLES[db_field.name]
        return formfield

    def get_list_display(self, request):
        translated = []
        for item in super().get_list_display(request):
            if not isinstance(item, str) or item not in FIELD_TITLES:
                translated.append(item)
                continue
            try:
                field = self.model._meta.get_field(item)
            except Exception:
                translated.append(item)
                continue

            def value(obj, field_name=item, choices=bool(field.choices)):
                if choices:
                    return getattr(obj, f'get_{field_name}_display')()
                return getattr(obj, field_name)

            value.short_description = FIELD_TITLES[item]
            value.admin_order_field = item
            value.boolean = field.get_internal_type() == 'BooleanField'
            translated.append(value)
        return translated


# All CRM registrations below inherit the localized behavior.
admin.ModelAdmin = RussianModelAdmin

# Русские названия в меню без миграций базы данных.
models.Role._meta.app_config.verbose_name = 'Major Motors CRM'
MODEL_TITLES = {
    models.Role: ('Роль', 'Роли'),
    models.RolePermission: ('Права роли', 'Права ролей'),
    models.EmployeeProfile: ('Профиль сотрудника', 'Профили сотрудников'),
    models.AuditEntry: ('Запись аудита', 'Журнал действий'),
    models.LeadSource: ('Источник лида', 'Источники лидов'),
    models.LeadStage: ('Этап лида', 'Этапы лидов'),
    models.LossReason: ('Причина отказа', 'Причины отказа'),
    models.Customer: ('Клиент', 'Клиенты'),
    models.CustomerDocument: ('Документ клиента', 'Документы клиентов'),
    models.Interaction: ('Взаимодействие', 'Взаимодействия'),
    models.ReminderTask: ('Задача', 'Задачи и напоминания'),
    models.Lead: ('Лид CRM', 'Лиды CRM'),
    models.LeadEntry: ('Обращение лида', 'Обращения лидов'),
    models.Vehicle: ('Автомобиль', 'Автомобили'),
    models.VehicleOption: ('Опция автомобиля', 'Опции автомобилей'),
    models.VehicleMedia: ('Фото или видео', 'Фото и видео автомобилей'),
    models.VehicleDefect: ('Дефект автомобиля', 'Дефекты автомобилей'),
    models.TradeInRecord: ('Оценка Trade-in', 'Оценки Trade-in'),
    models.Reservation: ('Бронирование', 'Бронирования'),
    models.TestDrive: ('Тест-драйв', 'Тест-драйвы'),
    models.Deal: ('Сделка', 'Сделки'),
    models.CashEmployee: ('Сотрудник', 'Сотрудники'),
    models.DealExtra: ('Дополнение к сделке', 'Дополнения к сделкам'),
    models.DealDocument: ('Документ сделки', 'Документы сделок'),
    models.Payment: ('Платёж', 'Платежи'),
    models.VehicleExpense: ('Расход по автомобилю', 'Расходы по автомобилям'),
    models.CashAccount: ('Касса', 'Касса'),
    models.BankAccount: ('Банковский счёт', 'Банковские счета'),
    models.CashShift: ('Кассовая смена', 'Кассовые смены'),
    models.CurrencyRate: ('Курс валюты', 'Курсы валют'),
    models.CashConversion: ('Обмен валюты', 'Обмены валюты'),
    models.CreditApplication: ('Кредитная заявка', 'Кредитные заявки'),
    models.CreditPaymentSchedule: ('Платёж по кредиту', 'Графики кредитных платежей'),
    models.InsurancePolicy: ('Страховой полис', 'Страховые полисы'),
    models.Warranty: ('Гарантия', 'Гарантии'),
    models.AddonSale: ('Дополнительная продажа', 'Дополнительные продажи'),
    models.ServiceOrder: ('Заказ сервиса', 'Заказы сервиса'),
    models.ServiceItem: ('Работа сервиса', 'Работы сервиса'),
}
for model, (singular, plural) in MODEL_TITLES.items():
    model._meta.verbose_name = singular
    model._meta.verbose_name_plural = plural


@admin.register(models.Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


@admin.register(models.RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = (
        'role',
        'can_view_finance',
        'can_edit_prices',
        'can_delete_deals',
        'can_export_data',
        'can_manage_inventory',
        'can_manage_users',
        'can_access_documents',
    )


@admin.register(models.EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'is_active')


@admin.register(models.AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'actor', 'action', 'model_name', 'object_id')
    list_filter = ('action', 'model_name')
    search_fields = ('summary', 'object_id')


@admin.register(models.LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)


@admin.register(models.LeadStage)
class LeadStageAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'is_active', 'is_won', 'is_lost')
    list_filter = ('is_active', 'is_won', 'is_lost')


@admin.register(models.LossReason)
class LossReasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')


@admin.register(models.Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'inn', 'pinfl', 'lead_source', 'assigned_manager')
    search_fields = ('full_name', 'phone', 'inn', 'pinfl', 'telegram', 'instagram')
    list_filter = ('lead_source', 'purchase_type')
    list_select_related = ('lead_source', 'assigned_manager')
    ordering = ('full_name',)
    fieldsets = (
        ('Основная информация', {'fields': ('full_name', 'phone', 'address')}),
        ('Документы', {'fields': ('inn', 'pinfl', 'passport_series', 'passport_number', 'passport_issued_date', 'passport_issued_by'), 'classes': ('collapse',)}),
        ('Продажа', {'fields': ('lead_source', 'assigned_manager', 'purchase_type', 'budget', 'preferred_make', 'preferred_model', 'preferred_year')}),
        ('Контакты и заметки', {'fields': ('telegram', 'instagram', 'notes')}),
        ('Файлы договора', {'fields': ('contract_number', 'contract_file', 'contract_file_second', 'power_of_attorney_file'), 'classes': ('collapse',)}),
    )


@admin.register(models.CustomerDocument)
class CustomerDocumentAdmin(admin.ModelAdmin):
    list_display = ('customer', 'document_type', 'uploaded_by', 'restricted_to_role')
    list_filter = ('document_type', 'restricted_to_role')


@admin.register(models.Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ('customer', 'interaction_type', 'occurred_at', 'created_by')
    list_filter = ('interaction_type',)


@admin.register(models.ReminderTask)
class ReminderTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'assigned_to', 'status', 'due_at')
    list_filter = ('status',)


@admin.register(models.Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'stage', 'assigned_to', 'sla_minutes', 'auto_assigned')
    list_filter = ('stage', 'auto_assigned')


@admin.register(models.LeadEntry)
class LeadEntryAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'phone',
        'visit_date',
        'visit_count',
        'last_call_at',
        'call_count',
        'status',
        'employee',
        'next_action_date',
    )
    list_filter = ('status', 'employee', 'next_action_date')
    search_fields = ('name', 'phone')
    ordering = ('next_action_date', '-updated_at')
    date_hierarchy = 'next_action_date'
    readonly_fields = ('next_action_notified_date', 'created_at', 'updated_at')
    fieldsets = (
        ('Клиент', {'fields': ('name', 'phone', 'employee', 'status')}),
        ('Следующее действие', {'fields': ('next_action_date', 'next_action_notified_date')}),
        ('История обращений', {'fields': (('visit_date', 'visit_count'), ('last_call_at', 'call_count'))}),
        ('Комментарий', {'fields': ('comment',)}),
        ('Системная информация', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(models.Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vin', 'name', 'make', 'model', 'status', 'purchase_price', 'sale_price', 'stock_count')
    list_filter = ('status', 'acquisition_type', 'condition', 'make', 'year')
    search_fields = ('vin', 'name', 'make', 'model')
    ordering = ('-sale_price', '-created_at')
    filter_horizontal = ('options',)
    fieldsets = (
        ('Автомобиль', {'fields': ('name', ('make', 'model'), ('year', 'model_year'), 'vin', 'engine_number')}),
        ('Цена и наличие', {'fields': (('purchase_price', 'purchase_currency'), ('sale_price', 'sale_currency'), 'stock_count', 'status')}),
        ('Характеристики', {'fields': (('condition', 'mileage'), ('color', 'body_type'), ('engine_type', 'engine_volume', 'horsepower'), ('transmission', 'fuel_consumption', 'range_km'), ('seat_count', 'country', 'trim_level', 'gross_weight'))}),
        ('Закупка', {'fields': ('acquisition_type', 'counterparty_name', 'arrived_at', 'location')}),
        ('Описание и комплектация', {'fields': ('description', 'options', 'notes')}),
    )


@admin.register(models.VehicleOption)
class VehicleOptionAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(models.VehicleMedia)
class VehicleMediaAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'media_type', 'created_at')


@admin.register(models.VehicleDefect)
class VehicleDefectAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'severity', 'detected_at')


@admin.register(models.TradeInRecord)
class TradeInRecordAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'appraised_value', 'previous_owners_count', 'evaluated_by')


@admin.register(models.Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'customer', 'reserved_by', 'reserved_by_name', 'start_at', 'end_at', 'status')
    list_filter = ('status',)


@admin.register(models.TestDrive)
class TestDriveAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'customer', 'manager', 'scheduled_at', 'status')
    list_filter = ('status',)


@admin.register(models.Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'customer',
        'vehicle',
        'manager',
        'status',
        'sale_price',
        'down_payment_amount',
        'bank_transfer_amount_uzs',
    )
    list_filter = ('status', 'financing_type')
    search_fields = ('id', 'customer__full_name', 'customer__phone', 'vehicle__name', 'contract_number')
    list_select_related = ('customer', 'vehicle', 'manager')
    ordering = ('-created_at',)
    fieldsets = (
        ('Участники сделки', {'fields': ('customer', 'vehicle', 'vehicle_unit', 'manager', 'sold_by_name')}),
        ('Статус и оплата', {'fields': ('status', 'financing_type', 'sale_price', 'discount_amount', 'commission_amount', 'certificate_amount', 'down_payment_amount', 'bank_transfer_amount_uzs', 'bank_rate_used', 'trade_in_value')}),
        ('Документы', {'fields': ('contract_number', 'contract_file', 'power_of_attorney_file', 'signed_at')}),
        ('Примечание', {'fields': ('notes',)}),
    )


@admin.register(models.CashEmployee)
class CashEmployeeAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'position', 'phone_primary', 'status', 'start_date')
    list_filter = ('status',)
    search_fields = ('last_name', 'first_name', 'phone_primary')
    ordering = ('last_name', 'first_name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Сотрудник', {'fields': ('external_id', ('last_name', 'first_name'), 'position', 'status', 'start_date')}),
        ('Контакты', {'fields': ('phone_primary', 'phone_secondary')}),
        ('Зарплата', {'fields': ('salary_amount', 'salary_day')}),
        ('Системная информация', {'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(models.DealExtra)
class DealExtraAdmin(admin.ModelAdmin):
    list_display = ('deal', 'name', 'price')


@admin.register(models.DealDocument)
class DealDocumentAdmin(admin.ModelAdmin):
    list_display = ('deal', 'document_type', 'uploaded_by')


@admin.register(models.Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('deal', 'amount', 'method', 'payment_kind', 'status', 'due_date')
    list_filter = ('method', 'payment_kind', 'status')


@admin.register(models.VehicleExpense)
class VehicleExpenseAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'category', 'amount', 'occurred_at')
    list_filter = ('category',)


@admin.register(models.CashAccount)
class CashAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'uzs_balance', 'usd_balance', 'updated_by', 'updated_at')


@admin.register(models.BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'uzs_balance', 'usd_balance', 'updated_by', 'updated_at')


@admin.register(models.CashShift)
class CashShiftAdmin(admin.ModelAdmin):
    list_display = ('id', 'opened_by', 'opened_at', 'closed_at', 'opening_balance', 'closing_balance')


@admin.register(models.CurrencyRate)
class CurrencyRateAdmin(admin.ModelAdmin):
    list_display = ('base_currency', 'quote_currency', 'rate', 'effective_date', 'created_by')
    list_filter = ('base_currency', 'quote_currency')


@admin.register(models.CashConversion)
class CashConversionAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'shift', 'from_currency', 'to_currency', 'amount_from', 'amount_to')
    list_filter = ('from_currency', 'to_currency')


@admin.register(models.CreditApplication)
class CreditApplicationAdmin(admin.ModelAdmin):
    list_display = ('customer', 'bank_name', 'status', 'requested_amount', 'approved_amount')
    list_filter = ('status',)


@admin.register(models.CreditPaymentSchedule)
class CreditPaymentScheduleAdmin(admin.ModelAdmin):
    list_display = ('credit_application', 'due_date', 'amount', 'status')
    list_filter = ('status',)


@admin.register(models.InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = ('customer', 'policy_type', 'start_date', 'end_date', 'premium')
    list_filter = ('policy_type',)


@admin.register(models.Warranty)
class WarrantyAdmin(admin.ModelAdmin):
    list_display = ('deal', 'provider', 'start_date', 'end_date')


@admin.register(models.AddonSale)
class AddonSaleAdmin(admin.ModelAdmin):
    list_display = ('deal', 'name', 'price')


@admin.register(models.ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'status', 'opened_at', 'closed_at', 'total_cost')
    list_filter = ('status',)


@admin.register(models.ServiceItem)
class ServiceItemAdmin(admin.ModelAdmin):
    list_display = ('service_order', 'cost', 'labor_hours')

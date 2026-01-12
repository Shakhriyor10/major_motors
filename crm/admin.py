from django.contrib import admin

from . import models


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


@admin.register(models.Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vin', 'name', 'make', 'model', 'status', 'purchase_price', 'sale_price', 'stock_count')
    list_filter = ('status', 'acquisition_type')
    search_fields = ('vin', 'name', 'make', 'model')


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
    list_display = ('vehicle', 'customer', 'start_at', 'end_at', 'status')
    list_filter = ('status',)


@admin.register(models.TestDrive)
class TestDriveAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'customer', 'manager', 'scheduled_at', 'status')
    list_filter = ('status',)


@admin.register(models.Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'vehicle', 'manager', 'status', 'sale_price')
    list_filter = ('status', 'financing_type')


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

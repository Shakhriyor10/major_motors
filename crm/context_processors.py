from .access import get_autosalon_access_flags
from .models import BankAccount, CashAccount, CurrencyRate


def cash_account(request):
    account = CashAccount.get_current()
    bank_account = BankAccount.get_current()
    rate = CurrencyRate.objects.order_by('-effective_date', '-created_at').first()
    access_flags = get_autosalon_access_flags(request.user)
    return {
        'cash_account': account,
        'bank_account': bank_account,
        'cash_rate': rate.rate if rate else 0,
        **access_flags,
    }

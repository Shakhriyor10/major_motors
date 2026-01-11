from .models import CashAccount, CurrencyRate


def cash_account(request):
    account = CashAccount.get_current()
    rate = CurrencyRate.objects.order_by('-effective_date', '-created_at').first()
    return {
        'cash_account': account,
        'cash_rate': rate.rate if rate else 0,
    }

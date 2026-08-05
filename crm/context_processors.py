from django.db import OperationalError, ProgrammingError

from .models import BankAccount, CashAccount, CurrencyRate, SiteTheme


def cash_account(request):
    account = CashAccount.get_current()
    bank_account = BankAccount.get_current()
    rate = CurrencyRate.objects.order_by('-effective_date', '-created_at').first()
    return {
        'cash_account': account,
        'bank_account': bank_account,
        'cash_rate': rate.rate if rate else 0,
    }


def site_theme(request):
    try:
        theme = SiteTheme.get_current()
    except (OperationalError, ProgrammingError):
        theme = None
    return {
        'site_theme': theme,
        'site_primary_color': theme.primary_color if theme else '#b4232f',
    }

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
    palettes = {
        'classic': {'background': '#f5f6f8', 'surface': '#ffffff', 'text': '#20242a', 'muted': '#6c757d', 'nav': '#66141d'},
        'ocean': {'background': '#eef6fb', 'surface': '#ffffff', 'text': '#123047', 'muted': '#60798b', 'nav': '#073b5c'},
        'emerald': {'background': '#eff8f3', 'surface': '#ffffff', 'text': '#173b2b', 'muted': '#60766b', 'nav': '#064e3b'},
        'violet': {'background': '#f5f1fb', 'surface': '#ffffff', 'text': '#2e2340', 'muted': '#756a82', 'nav': '#3b1763'},
        'midnight': {'background': '#0b1220', 'surface': '#141e2f', 'text': '#e8eef8', 'muted': '#9aa9bd', 'nav': '#070c15'},
        'graphite': {'background': '#17191d', 'surface': '#24272d', 'text': '#f0f1f3', 'muted': '#a5a8ae', 'nav': '#101114'},
    }
    palette = palettes.get(theme.preset if theme else 'classic', palettes['classic'])
    return {
        'site_theme': theme,
        'site_primary_color': theme.primary_color if theme else '#b4232f',
        'site_palette': palette,
    }

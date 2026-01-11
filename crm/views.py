from django.shortcuts import render

from .models import CashConversion, CurrencyRate


def home(request):
    exchange_rate = CurrencyRate.objects.order_by('-effective_date', '-created_at').first()
    return render(request, 'crm/home.html', {'exchange_rate': exchange_rate})


def cash_dashboard(request):
    exchange_rate = CurrencyRate.objects.order_by('-effective_date', '-created_at').first()
    conversions = CashConversion.objects.select_related('shift').order_by('-created_at')[:10]
    return render(
        request,
        'crm/cash.html',
        {
            'exchange_rate': exchange_rate,
            'conversions': conversions,
        },
    )

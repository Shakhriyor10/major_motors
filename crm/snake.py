import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import SnakeScore


def score_payload(record):
    leaders = SnakeScore.objects.select_related('user').order_by('-best_score', 'updated_at')[:5]
    return {
        'best_score': record.best_score,
        'games_played': record.games_played,
        'leaderboard': [
            {'username': item.user.get_username(), 'score': item.best_score}
            for item in leaders
        ],
    }


@login_required
def page(request):
    record, _ = SnakeScore.objects.get_or_create(user=request.user)
    return render(request, 'crm/snake.html', {'snake_record': record})


@login_required
def state(request):
    record, _ = SnakeScore.objects.get_or_create(user=request.user)
    return JsonResponse(score_payload(record))


@login_required
@require_POST
def submit(request):
    try:
        score = int(json.loads(request.body or '{}').get('score'))
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Некорректный результат.'}, status=400)
    if score < 0 or score > 100000:
        return JsonResponse({'error': 'Результат выходит за границы игрового поля.'}, status=400)
    with transaction.atomic():
        record, _ = SnakeScore.objects.select_for_update().get_or_create(user=request.user)
        record.games_played += 1
        if score > record.best_score:
            record.best_score = score
        record.save()
    return JsonResponse(score_payload(record))

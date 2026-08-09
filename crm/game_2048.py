import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import Game2048Score


def score_payload(record):
    leaders = Game2048Score.objects.select_related('user').order_by('-best_score', '-best_tile', 'updated_at')[:5]
    return {
        'best_score': record.best_score,
        'best_tile': record.best_tile,
        'games_played': record.games_played,
        'leaderboard': [
            {'username': item.user.get_username(), 'score': item.best_score, 'tile': item.best_tile}
            for item in leaders
        ],
    }


@login_required
def page(request):
    record, _ = Game2048Score.objects.get_or_create(user=request.user)
    return render(request, 'crm/game_2048.html', {'game_record': record})


@login_required
def state(request):
    record, _ = Game2048Score.objects.get_or_create(user=request.user)
    return JsonResponse(score_payload(record))


@login_required
@require_POST
def submit(request):
    try:
        data = json.loads(request.body or '{}')
        score = int(data.get('score'))
        best_tile = int(data.get('best_tile'))
        finished = bool(data.get('finished', False))
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Некорректный результат.'}, status=400)
    if score < 0 or score > 4_000_000_000 or best_tile < 2 or best_tile > 131072 or best_tile & (best_tile - 1):
        return JsonResponse({'error': 'Результат выходит за допустимые границы игры.'}, status=400)
    with transaction.atomic():
        record, _ = Game2048Score.objects.select_for_update().get_or_create(user=request.user)
        record.best_score = max(record.best_score, score)
        record.best_tile = max(record.best_tile, best_tile)
        if finished:
            record.games_played += 1
        record.save()
    return JsonResponse(score_payload(record))

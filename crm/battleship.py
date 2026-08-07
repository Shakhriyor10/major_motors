import json
import random

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import BattleshipGame


FLEET = [4, 3, 3, 2, 2, 2, 1, 1, 1, 1]


def side_for(game, user):
    if game.player_one_id == user.id:
        return 1
    if game.player_two_id == user.id:
        return 2
    return 0


def neighbours(index):
    row, col = divmod(index, 10)
    return [r * 10 + c for r in range(max(0, row - 1), min(10, row + 2))
            for c in range(max(0, col - 1), min(10, col + 2)) if r * 10 + c != index]


def validate_ships(ships):
    if not isinstance(ships, list) or sorted(len(ship) for ship in ships) != sorted(FLEET):
        return None
    occupied = set()
    for ship in ships:
        if not isinstance(ship, list) or len(set(ship)) != len(ship):
            return None
        try:
            cells = sorted(int(cell) for cell in ship)
        except (TypeError, ValueError):
            return None
        if any(cell < 0 or cell >= 100 for cell in cells) or occupied.intersection(cells):
            return None
        rows, cols = {cell // 10 for cell in cells}, {cell % 10 for cell in cells}
        if len(rows) != 1 and len(cols) != 1:
            return None
        if len(rows) == 1 and cells != list(range(cells[0], cells[0] + len(cells))):
            return None
        if len(cols) == 1 and [cell // 10 for cell in cells] != list(range(cells[0] // 10, cells[0] // 10 + len(cells))):
            return None
        if any(set(neighbours(cell)).intersection(occupied) for cell in cells):
            return None
        occupied.update(cells)
    return ships


def random_fleet():
    for _ in range(250):
        ships, blocked = [], set()
        for length in FLEET:
            choices = []
            for vertical in (False, True):
                for row in range(10 - (length - 1 if vertical else 0)):
                    for col in range(10 - (length - 1 if not vertical else 0)):
                        cells = [((row + i) * 10 + col) if vertical else (row * 10 + col + i) for i in range(length)]
                        if not blocked.intersection(cells):
                            choices.append(cells)
            if not choices:
                break
            ship = random.choice(choices)
            ships.append(ship)
            blocked.update(ship)
            blocked.update(n for cell in ship for n in neighbours(cell))
        if len(ships) == len(FLEET):
            return ships
    raise RuntimeError('Не удалось расставить корабли.')


def all_cells(ships):
    return {cell for ship in ships for cell in ship}


def public_shots(shots, enemy_board):
    result = []
    for cell in shots:
        ship = next((ship for ship in enemy_board if cell in ship), None)
        result.append({'cell': cell, 'hit': bool(ship), 'sunk': bool(ship and set(ship).issubset(shots))})
    return result


def payload(game, user):
    side = side_for(game, user)
    own_board = game.board_one if side == 1 else game.board_two
    enemy_board = game.board_two if side == 1 else game.board_one
    my_shots = game.shots_one if side == 1 else game.shots_two
    enemy_shots = game.shots_two if side == 1 else game.shots_one
    own_ready = game.ready_one if side == 1 else game.ready_two
    return {
        'id': game.id, 'side': side, 'status': game.status, 'turn': game.current_turn,
        'winner': game.winner, 'finish_reason': game.finish_reason, 'version': game.version,
        'player_one': game.player_one.get_username(),
        'player_two': game.player_two.get_username() if game.player_two else None,
        'ready': own_ready, 'opponent_ready': game.ready_two if side == 1 else game.ready_one,
        'own_ships': own_board if own_ready else [],
        'incoming': public_shots(enemy_shots, own_board),
        'outgoing': public_shots(my_shots, enemy_board),
    }


def participant(game_id, user, lock=False):
    queryset = BattleshipGame.objects.select_related('player_one', 'player_two')
    if lock:
        queryset = queryset.select_for_update()
    game = get_object_or_404(queryset, pk=game_id)
    return game if side_for(game, user) else None


@login_required
def page(request):
    return render(request, 'crm/battleship.html')


@login_required
def lobby(request):
    waiting = BattleshipGame.objects.filter(status='waiting', player_two__isnull=True).exclude(player_one=request.user).select_related('player_one')[:20]
    mine = BattleshipGame.objects.filter(Q(player_one=request.user) | Q(player_two=request.user), status__in=['waiting', 'placing', 'active']).select_related('player_one', 'player_two').first()
    return JsonResponse({'waiting': [{'id': game.id, 'username': game.player_one.get_username()} for game in waiting],
                         'current_game': payload(mine, request.user) if mine else None})


@login_required
@require_POST
def create(request):
    game = BattleshipGame.objects.filter(Q(player_one=request.user) | Q(player_two=request.user), status__in=['waiting', 'placing', 'active']).select_related('player_one', 'player_two').first()
    game = game or BattleshipGame.objects.create(player_one=request.user)
    return JsonResponse(payload(game, request.user))


@login_required
@require_POST
def join(request, game_id):
    with transaction.atomic():
        game = get_object_or_404(BattleshipGame.objects.select_for_update(), pk=game_id)
        if game.player_one_id == request.user.id:
            return JsonResponse({'error': 'Нельзя играть против себя.'}, status=400)
        if game.status != 'waiting' or game.player_two_id:
            return JsonResponse({'error': 'Комната уже занята.'}, status=409)
        if BattleshipGame.objects.filter(Q(player_one=request.user) | Q(player_two=request.user), status__in=['waiting', 'placing', 'active']).exclude(pk=game.pk).exists():
            return JsonResponse({'error': 'Сначала завершите текущую игру.'}, status=409)
        game.player_two, game.status, game.version = request.user, 'placing', game.version + 1
        game.save(update_fields=['player_two', 'status', 'version', 'updated_at'])
    return JsonResponse(payload(game, request.user))


@login_required
def state(request, game_id):
    game = participant(game_id, request.user)
    if not game:
        return JsonResponse({'error': 'Нет доступа к игре.'}, status=403)
    return JsonResponse(payload(game, request.user))


@login_required
@require_POST
def setup(request, game_id):
    try:
        data = json.loads(request.body or '{}')
        ships = random_fleet() if data.get('random') else validate_ships(data.get('ships'))
    except (json.JSONDecodeError, RuntimeError):
        ships = None
    if not ships:
        return JsonResponse({'error': 'Неверная расстановка флота.'}, status=400)
    with transaction.atomic():
        game = participant(game_id, request.user, lock=True)
        if not game:
            return JsonResponse({'error': 'Нет доступа к игре.'}, status=403)
        side = side_for(game, request.user)
        if game.status != 'placing' or (game.ready_one if side == 1 else game.ready_two):
            return JsonResponse({'error': 'Расстановку уже нельзя изменить.'}, status=409)
        if side == 1:
            game.board_one, game.ready_one = ships, True
        else:
            game.board_two, game.ready_two = ships, True
        if game.ready_one and game.ready_two:
            game.status = 'active'
        game.version += 1
        game.save()
    return JsonResponse(payload(game, request.user))


@login_required
@require_POST
def shoot(request, game_id):
    try:
        cell = int(json.loads(request.body or '{}')['cell'])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Некорректная клетка.'}, status=400)
    if not 0 <= cell < 100:
        return JsonResponse({'error': 'Некорректная клетка.'}, status=400)
    with transaction.atomic():
        game = participant(game_id, request.user, lock=True)
        if not game:
            return JsonResponse({'error': 'Нет доступа к игре.'}, status=403)
        side = side_for(game, request.user)
        if game.status != 'active' or game.current_turn != side:
            return JsonResponse({'error': 'Сейчас ход соперника.'}, status=409)
        shots = list(game.shots_one if side == 1 else game.shots_two)
        if cell in shots:
            return JsonResponse({'error': 'По этой клетке уже стреляли.'}, status=409)
        shots.append(cell)
        target_board = game.board_two if side == 1 else game.board_one
        hit = cell in all_cells(target_board)
        if side == 1:
            game.shots_one = shots
        else:
            game.shots_two = shots
        if all_cells(target_board).issubset(shots):
            game.status, game.winner, game.finish_reason = 'finished', side, 'fleet_destroyed'
        elif not hit:
            game.current_turn = 2 if side == 1 else 1
        game.version += 1
        game.save()
    response = payload(game, request.user)
    response['last_shot'] = {'cell': cell, 'hit': hit}
    return JsonResponse(response)


@login_required
@require_POST
def resign(request, game_id):
    with transaction.atomic():
        game = participant(game_id, request.user, lock=True)
        if not game:
            return JsonResponse({'error': 'Нет доступа к игре.'}, status=403)
        if game.status not in ('waiting', 'placing', 'active'):
            return JsonResponse({'error': 'Игра уже завершена.'}, status=409)
        side = side_for(game, request.user)
        game.status, game.winner = 'finished', (2 if side == 1 and game.player_two_id else 1)
        game.finish_reason, game.version = 'resigned', game.version + 1
        game.save()
    return JsonResponse(payload(game, request.user))


@login_required
@require_POST
def rematch(request, game_id):
    with transaction.atomic():
        game = participant(game_id, request.user, lock=True)
        if not game:
            return JsonResponse({'error': 'Нет доступа к игре.'}, status=403)
        if game.status != 'finished' or not game.player_two_id:
            return JsonResponse({'error': 'Повторная игра сейчас недоступна.'}, status=409)
        game.board_one = game.board_two = game.shots_one = game.shots_two = []
        game.ready_one = game.ready_two = False
        game.status, game.winner, game.finish_reason = 'placing', None, ''
        game.current_turn, game.version = (2 if game.current_turn == 1 else 1), game.version + 1
        game.save()
    return JsonResponse(payload(game, request.user))

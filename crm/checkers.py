import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import CheckersGame


DIAGONALS = ((-1, -1), (-1, 1), (1, -1), (1, 1))


def initial_board():
    board = [''] * 64
    for row in range(3):
        for col in range(8):
            if (row + col) % 2:
                board[row * 8 + col] = 'b'
    for row in range(5, 8):
        for col in range(8):
            if (row + col) % 2:
                board[row * 8 + col] = 'w'
    return board


def color(piece):
    return piece.lower() if piece else ''


def inside(row, col):
    return 0 <= row < 8 and 0 <= col < 8


def captures_from(board, start):
    piece = board[start]
    if not piece:
        return []
    row, col = divmod(start, 8)
    moves = []
    if piece.isupper():
        for dr, dc in DIAGONALS:
            enemy = None
            r, c = row + dr, col + dc
            while inside(r, c):
                target = board[r * 8 + c]
                if not target:
                    if enemy is not None:
                        moves.append({'from': start, 'to': r * 8 + c, 'capture': enemy})
                elif color(target) == color(piece):
                    break
                elif enemy is not None:
                    break
                else:
                    enemy = r * 8 + c
                r, c = r + dr, c + dc
    else:
        for dr, dc in DIAGONALS:
            middle_r, middle_c = row + dr, col + dc
            end_r, end_c = row + dr * 2, col + dc * 2
            if inside(end_r, end_c):
                middle = middle_r * 8 + middle_c
                end = end_r * 8 + end_c
                if board[middle] and color(board[middle]) != color(piece) and not board[end]:
                    moves.append({'from': start, 'to': end, 'capture': middle})
    return moves


def quiet_moves_from(board, start):
    piece = board[start]
    if not piece:
        return []
    row, col = divmod(start, 8)
    moves = []
    directions = DIAGONALS if piece.isupper() else ((-1, -1), (-1, 1)) if piece == 'w' else ((1, -1), (1, 1))
    for dr, dc in directions:
        r, c = row + dr, col + dc
        while inside(r, c) and not board[r * 8 + c]:
            moves.append({'from': start, 'to': r * 8 + c, 'capture': None})
            if not piece.isupper():
                break
            r, c = r + dr, c + dc
    return moves


def legal_moves(board, side, forced_piece=None):
    pieces = [forced_piece] if forced_piece is not None else [i for i, p in enumerate(board) if color(p) == side]
    captures = [move for index in pieces for move in captures_from(board, index)]
    if captures:
        return captures
    if forced_piece is not None:
        return []
    return [move for index in pieces for move in quiet_moves_from(board, index)]


def user_side(game, user):
    if game.player_white_id == user.id:
        return 'w'
    if game.player_black_id == user.id:
        return 'b'
    return ''


def payload(game, user):
    side = user_side(game, user)
    moves = legal_moves(game.board, game.current_turn, game.forced_piece) if game.status == 'active' else []
    return {
        'id': game.id, 'board': game.board, 'status': game.status, 'turn': game.current_turn,
        'side': side, 'winner': game.winner, 'finish_reason': game.finish_reason,
        'forced_piece': game.forced_piece, 'version': game.version,
        'player_white': game.player_white.get_username(),
        'player_black': game.player_black.get_username() if game.player_black else None,
        'legal_moves': moves if side == game.current_turn else [],
        'draw_offered_by': game.draw_offered_by.get_username() if game.draw_offered_by else None,
        'draw_offered_by_me': game.draw_offered_by_id == user.id,
        'history': game.history[-20:],
    }


def participant_game(game_id, user, lock=False):
    queryset = CheckersGame.objects.select_related('player_white', 'player_black', 'draw_offered_by')
    if lock:
        queryset = queryset.select_for_update()
    game = get_object_or_404(queryset, pk=game_id)
    return game if user_side(game, user) else None


@login_required
def page(request):
    return render(request, 'crm/checkers.html')


@login_required
def lobby(request):
    waiting = CheckersGame.objects.filter(status='waiting', player_black__isnull=True).exclude(player_white=request.user).select_related('player_white')[:20]
    mine = CheckersGame.objects.filter(Q(player_white=request.user) | Q(player_black=request.user), status__in=['waiting', 'active']).select_related('player_white', 'player_black', 'draw_offered_by').first()
    return JsonResponse({'waiting': [{'id': g.id, 'username': g.player_white.get_username()} for g in waiting], 'current_game': payload(mine, request.user) if mine else None})


@login_required
@require_POST
def create(request):
    game = CheckersGame.objects.filter(Q(player_white=request.user) | Q(player_black=request.user), status__in=['waiting', 'active']).select_related('player_white', 'player_black').first()
    game = game or CheckersGame.objects.create(player_white=request.user, board=initial_board())
    return JsonResponse(payload(game, request.user))


@login_required
@require_POST
def join(request, game_id):
    with transaction.atomic():
        game = get_object_or_404(CheckersGame.objects.select_for_update(), pk=game_id)
        if game.player_white_id == request.user.id:
            return JsonResponse({'error': 'Нельзя играть против себя.'}, status=400)
        if game.status != 'waiting' or game.player_black_id:
            return JsonResponse({'error': 'Игра уже занята.'}, status=409)
        if CheckersGame.objects.filter(Q(player_white=request.user) | Q(player_black=request.user), status__in=['waiting', 'active']).exclude(pk=game.pk).exists():
            return JsonResponse({'error': 'Сначала завершите текущую партию.'}, status=409)
        game.player_black, game.status, game.version = request.user, 'active', game.version + 1
        game.save(update_fields=['player_black', 'status', 'version', 'updated_at'])
    return JsonResponse(payload(game, request.user))


@login_required
def state(request, game_id):
    game = participant_game(game_id, request.user)
    if not game:
        return JsonResponse({'error': 'Нет доступа к партии.'}, status=403)
    return JsonResponse(payload(game, request.user))


@login_required
@require_POST
def move(request, game_id):
    try:
        data = json.loads(request.body or '{}')
        start, end = int(data['from']), int(data['to'])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Некорректный ход.'}, status=400)
    with transaction.atomic():
        game = participant_game(game_id, request.user, lock=True)
        if not game:
            return JsonResponse({'error': 'Нет доступа к партии.'}, status=403)
        side = user_side(game, request.user)
        if game.status != 'active' or side != game.current_turn:
            return JsonResponse({'error': 'Сейчас ход соперника.'}, status=409)
        chosen = next((m for m in legal_moves(game.board, side, game.forced_piece) if m['from'] == start and m['to'] == end), None)
        if not chosen:
            return JsonResponse({'error': 'Этот ход запрещён правилами.'}, status=409)
        board = list(game.board)
        piece = board[start]
        board[start], board[end] = '', piece
        if chosen['capture'] is not None:
            board[chosen['capture']] = ''
        end_row = end // 8
        if piece == 'w' and end_row == 0:
            board[end] = 'W'
        elif piece == 'b' and end_row == 7:
            board[end] = 'B'
        game.board = board
        entry = {'side': side, 'from': start, 'to': end, 'capture': chosen['capture']}
        game.history = [*game.history, entry]
        more = captures_from(board, end) if chosen['capture'] is not None else []
        if more:
            game.forced_piece = end
        else:
            game.forced_piece = None
            game.current_turn = 'b' if side == 'w' else 'w'
            if not legal_moves(board, game.current_turn):
                game.status, game.winner, game.finish_reason = 'finished', side, 'no_moves'
        game.draw_offered_by = None
        game.version += 1
        game.save()
    return JsonResponse(payload(game, request.user))


@login_required
@require_POST
def resign(request, game_id):
    with transaction.atomic():
        game = participant_game(game_id, request.user, lock=True)
        if not game or game.status != 'active':
            return JsonResponse({'error': 'Партия недоступна.'}, status=409)
        side = user_side(game, request.user)
        game.status, game.winner, game.finish_reason = 'finished', ('b' if side == 'w' else 'w'), 'resigned'
        game.version += 1
        game.save()
    return JsonResponse(payload(game, request.user))


@login_required
@require_POST
def draw(request, game_id):
    action = json.loads(request.body or '{}').get('action')
    with transaction.atomic():
        game = participant_game(game_id, request.user, lock=True)
        if not game or game.status != 'active':
            return JsonResponse({'error': 'Партия недоступна.'}, status=409)
        if action == 'offer':
            game.draw_offered_by = request.user
        elif action == 'accept' and game.draw_offered_by_id and game.draw_offered_by_id != request.user.id:
            game.status, game.winner, game.finish_reason, game.draw_offered_by = 'finished', 'd', 'draw', None
        elif action == 'decline' and game.draw_offered_by_id != request.user.id:
            game.draw_offered_by = None
        else:
            return JsonResponse({'error': 'Некорректное действие.'}, status=400)
        game.version += 1
        game.save()
    return JsonResponse(payload(game, request.user))


@login_required
@require_POST
def rematch(request, game_id):
    old = participant_game(game_id, request.user)
    if not old or old.status != 'finished' or not old.player_black:
        return JsonResponse({'error': 'Повторная партия пока недоступна.'}, status=409)
    game = CheckersGame.objects.create(
        player_white=old.player_black,
        player_black=old.player_white,
        board=initial_board(),
        status='active',
    )
    return JsonResponse(payload(game, request.user))

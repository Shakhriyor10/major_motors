import json
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from .checkers import captures_from, initial_board, legal_moves
from .battleship import random_fleet, validate_ships
from .models import BattleshipGame, CheckersGame, ClassicSnakeScore, SiteTheme, SnakeScore, TicTacToeGame

class TicTacToeGameTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.x = users.objects.create_user('player-x', password='test')
        self.o = users.objects.create_user('player-o', password='test')
        self.x_client, self.o_client = Client(), Client()
        self.x_client.force_login(self.x); self.o_client.force_login(self.o)

    def move(self, client, game, position):
        return client.post(reverse('tic-tac-toe-move', args=[game.id]), json.dumps({'position': position}), content_type='application/json')

    def test_two_users_join_sync_and_finish(self):
        created = self.x_client.post(reverse('tic-tac-toe-create')).json()
        self.assertEqual(self.o_client.post(reverse('tic-tac-toe-join', args=[created['id']])).status_code, 200)
        game = TicTacToeGame.objects.get(pk=created['id'])
        for client, cell in [(self.x_client,0),(self.o_client,3),(self.x_client,1),(self.o_client,4),(self.x_client,2)]:
            self.assertEqual(self.move(client, game, cell).status_code, 200)
        state = self.o_client.get(reverse('tic-tac-toe-state', args=[game.id])).json()
        self.assertEqual((state['status'], state['winner'], ''.join(state['board'])), ('finished','X','XXXOO----'))

    def test_turn_and_access_are_protected(self):
        game = TicTacToeGame.objects.create(player_x=self.x, player_o=self.o, status='active')
        self.assertEqual(self.move(self.o_client, game, 0).status_code, 409)
        outsider = get_user_model().objects.create_user('outsider', password='test')
        client = Client(); client.force_login(outsider)
        self.assertEqual(client.get(reverse('tic-tac-toe-state', args=[game.id])).status_code, 403)


class CheckersRulesTests(TestCase):
    def empty(self):
        return [''] * 64

    def test_initial_position_has_24_pieces_and_seven_moves(self):
        board = initial_board()
        self.assertEqual(sum(bool(p) for p in board), 24)
        self.assertEqual(len(legal_moves(board, 'w')), 7)

    def test_capture_is_mandatory_and_man_captures_backwards(self):
        board = self.empty()
        board[26], board[35] = 'w', 'b'
        self.assertEqual(legal_moves(board, 'w'), [{'from': 26, 'to': 44, 'capture': 35}])

    def test_flying_king_can_land_beyond_captured_piece(self):
        board = self.empty()
        board[49], board[35] = 'W', 'b'
        destinations = {m['to'] for m in captures_from(board, 49)}
        self.assertEqual(destinations, {28, 21, 14, 7})


class CheckersApiTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.white = users.objects.create_user('white', password='test')
        self.black = users.objects.create_user('black', password='test')
        self.wc, self.bc = Client(), Client()
        self.wc.force_login(self.white); self.bc.force_login(self.black)

    def move(self, client, game, start, end):
        return client.post(reverse('checkers-move', args=[game.id]), json.dumps({'from': start, 'to': end}), content_type='application/json')

    def test_join_move_and_live_state(self):
        created = self.wc.post(reverse('checkers-create')).json()
        self.assertEqual(self.bc.post(reverse('checkers-join', args=[created['id']])).status_code, 200)
        game = CheckersGame.objects.get(pk=created['id'])
        self.assertEqual(self.move(self.wc, game, 40, 33).status_code, 200)
        state = self.bc.get(reverse('checkers-state', args=[game.id])).json()
        self.assertEqual((state['board'][40], state['board'][33], state['turn']), ('', 'w', 'b'))

    def test_multiple_capture_forces_same_piece_and_promotes(self):
        board = [''] * 64
        board[49], board[42], board[28], board[14] = 'w', 'b', 'b', 'b'
        game = CheckersGame.objects.create(player_white=self.white, player_black=self.black, board=board, status='active')
        first = self.move(self.wc, game, 49, 35).json()
        self.assertEqual((first['forced_piece'], first['turn']), (35, 'w'))
        second = self.move(self.wc, game, 35, 21).json()
        self.assertEqual((second['forced_piece'], second['turn']), (21, 'w'))
        third = self.move(self.wc, game, 21, 7).json()
        self.assertEqual(third['board'][7], 'W')

    def test_resign_draw_and_rematch(self):
        game = CheckersGame.objects.create(player_white=self.white, player_black=self.black, board=initial_board(), status='active')
        offer = self.wc.post(reverse('checkers-draw', args=[game.id]), json.dumps({'action': 'offer'}), content_type='application/json')
        self.assertEqual(offer.status_code, 200)
        accepted = self.bc.post(reverse('checkers-draw', args=[game.id]), json.dumps({'action': 'accept'}), content_type='application/json').json()
        self.assertEqual((accepted['status'], accepted['winner']), ('finished', 'd'))
        rematch = self.wc.post(reverse('checkers-rematch', args=[game.id])).json()
        self.assertEqual((rematch['status'], rematch['player_white'], rematch['player_black']), ('active', 'black', 'white'))


class ThemeSettingsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('designer', password='test')
        self.client.force_login(self.user)

    def test_settings_page_renders_all_presets(self):
        response = self.client.get(reverse('theme-settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Midnight')
        self.assertContains(response, 'Меню слева')

    def test_design_is_saved_and_applied_to_base_template(self):
        response = self.client.post(reverse('theme-settings'), {
            'primary_color': '#2563eb', 'preset': 'midnight', 'navigation': 'sidebar',
            'card_style': 'glass', 'vehicle_card_style': 'square', 'radius': '24', 'compact': '1',
        })
        self.assertEqual(response.status_code, 302)
        theme = SiteTheme.get_current()
        self.assertEqual((theme.preset, theme.navigation, theme.card_style, theme.vehicle_card_style, theme.radius, theme.compact),
                         ('midnight', 'sidebar', 'glass', 'square', 24, True))
        page = self.client.get(reverse('theme-settings'))
        self.assertContains(page, 'theme-midnight nav-sidebar cards-glass vehicle-cards-square compact-ui')

class GamesHubTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.user = users.objects.create_user('regular-player', password='test')
        self.admin = users.objects.create_superuser('game-admin', 'admin@example.com', 'test')

    def test_hub_contains_separate_game_cards(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('lounge'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Крестики-нолики')
        self.assertContains(response, 'Русские шашки')
        self.assertContains(response, 'Змейка')
        self.assertContains(response, 'Морской бой')
        self.assertContains(response, 'Классическая змейка')
        self.assertNotContains(response, 'Полный сброс игр')

    def test_only_admin_can_fully_reset_all_games(self):
        TicTacToeGame.objects.create(player_x=self.user)
        CheckersGame.objects.create(player_white=self.user, board=initial_board())
        SnakeScore.objects.create(user=self.user, best_score=12, games_played=1)
        BattleshipGame.objects.create(player_one=self.user)
        self.client.force_login(self.user)
        denied = self.client.post(reverse('games-reset'))
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(TicTacToeGame.objects.count() + CheckersGame.objects.count() + SnakeScore.objects.count() + BattleshipGame.objects.count(), 4)

        self.client.force_login(self.admin)
        response = self.client.post(reverse('games-reset'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['deleted'], 4)
        self.assertFalse(TicTacToeGame.objects.exists())
        self.assertFalse(CheckersGame.objects.exists())
        self.assertFalse(SnakeScore.objects.exists())
        self.assertFalse(BattleshipGame.objects.exists())


class SnakeApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('snake-player', password='test')
        self.client.force_login(self.user)

    def test_page_and_score_persistence(self):
        self.assertEqual(self.client.get(reverse('snake')).status_code, 200)
        first = self.client.post(reverse('snake-submit'), json.dumps({'score': 5}), content_type='application/json')
        second = self.client.post(reverse('snake-submit'), json.dumps({'score': 3}), content_type='application/json')
        self.assertEqual((first.status_code, second.status_code), (200, 200))
        score = SnakeScore.objects.get(user=self.user)
        self.assertEqual((score.best_score, score.games_played), (5, 2))
        state = self.client.get(reverse('snake-state')).json()
        self.assertEqual((state['best_score'], state['games_played']), (5, 2))

    def test_impossible_score_is_rejected(self):
        response = self.client.post(reverse('snake-submit'), json.dumps({'score': 100001}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SnakeScore.objects.filter(user=self.user).exists())


class ClassicSnakeApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('classic-snake-player', password='test')
        self.client.force_login(self.user)

    def test_classic_records_are_saved_separately(self):
        self.assertEqual(self.client.get(reverse('classic-snake')).status_code, 200)
        response = self.client.post(reverse('classic-snake-submit'), json.dumps({'score': 7}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        record = ClassicSnakeScore.objects.get(user=self.user)
        self.assertEqual((record.best_score, record.games_played), (7, 1))
        self.assertFalse(SnakeScore.objects.filter(user=self.user).exists())

    def test_classic_impossible_score_is_rejected(self):
        response = self.client.post(reverse('classic-snake-submit'), json.dumps({'score': 398}), content_type='application/json')
        self.assertEqual(response.status_code, 400)


class BattleshipTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.one = users.objects.create_user('captain-one', password='test')
        self.two = users.objects.create_user('captain-two', password='test')
        self.c1, self.c2 = Client(), Client()
        self.c1.force_login(self.one); self.c2.force_login(self.two)

    def post_json(self, client, name, game=None, data=None):
        args = [game.id] if game else []
        return client.post(reverse(name, args=args), json.dumps(data or {}), content_type='application/json')

    def test_random_fleet_is_always_valid(self):
        for _ in range(15):
            fleet = random_fleet()
            self.assertEqual(validate_ships(fleet), fleet)
            self.assertEqual(sum(map(len, fleet)), 20)

    def test_two_players_setup_shoot_and_hidden_board(self):
        created = self.post_json(self.c1, 'battleship-create').json()
        game = BattleshipGame.objects.get(pk=created['id'])
        self.assertEqual(self.post_json(self.c2, 'battleship-join', game).status_code, 200)
        fleet_one, fleet_two = random_fleet(), random_fleet()
        self.assertEqual(self.post_json(self.c1, 'battleship-setup', game, {'ships': fleet_one}).status_code, 200)
        ready = self.post_json(self.c2, 'battleship-setup', game, {'ships': fleet_two}).json()
        self.assertEqual(ready['status'], 'active')
        self.assertNotIn(fleet_one[0][0], set(ready['own_ships'][0]) if ready['own_ships'] else set())
        miss = next(cell for cell in range(100) if cell not in {c for ship in fleet_two for c in ship})
        result = self.post_json(self.c1, 'battleship-shoot', game, {'cell': miss}).json()
        self.assertEqual((result['last_shot']['hit'], result['turn']), (False, 2))
        hit = fleet_one[0][0]
        result = self.post_json(self.c2, 'battleship-shoot', game, {'cell': hit}).json()
        self.assertEqual((result['last_shot']['hit'], result['turn']), (True, 2))
        self.assertEqual(self.post_json(self.c2, 'battleship-shoot', game, {'cell': hit}).status_code, 409)

    def test_invalid_touching_fleet_rejected(self):
        game = BattleshipGame.objects.create(player_one=self.one, player_two=self.two, status='placing')
        invalid = [[0, 1, 2, 3], [10, 11, 12], [20, 21, 22], [30, 31], [40, 41], [50, 51], [60], [70], [80], [90]]
        self.assertEqual(self.post_json(self.c1, 'battleship-setup', game, {'ships': invalid}).status_code, 400)

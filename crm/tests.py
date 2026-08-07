import json
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from .checkers import captures_from, initial_board, legal_moves
from .models import CheckersGame, SiteTheme, TicTacToeGame

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
        self.assertNotContains(response, 'Полный сброс игр')

    def test_only_admin_can_fully_reset_all_games(self):
        TicTacToeGame.objects.create(player_x=self.user)
        CheckersGame.objects.create(player_white=self.user, board=initial_board())
        self.client.force_login(self.user)
        denied = self.client.post(reverse('games-reset'))
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(TicTacToeGame.objects.count() + CheckersGame.objects.count(), 2)

        self.client.force_login(self.admin)
        response = self.client.post(reverse('games-reset'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['deleted'], 2)
        self.assertFalse(TicTacToeGame.objects.exists())
        self.assertFalse(CheckersGame.objects.exists())

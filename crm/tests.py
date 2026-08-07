import json
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from .models import TicTacToeGame

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

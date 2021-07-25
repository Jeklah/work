"""Game class to represent the current game taking place.
   This is also where the game variables will be set up, such as the
   Ship list and players that are taking part in the game.

   Having a class for the game also allows the possibility of having
   more than one game going on at the same time if we wanted to."""

import player
import gameBoard
import ship

class Game:
    """Class to represent the current game."""
    def __init__(self, player1, player2, gameBoard):
        self.player1 = player1
        self.player2 = player2
        self.gameBoard = gameBoard





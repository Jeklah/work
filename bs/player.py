"""Player class for battleships."""
import Ship
class Player:
    """Player class to represent the player in the current game."""

    def __init__(self, playerID, name, shipsDestroyed, opponentID, winner = False, shipCount = 5):
        self.name = name
        self.ships = []
        self.shipsDestroyed = 0
        self.winner = winner
        self.playerID = playerID
        self.shipCount = shipCount
        self.opponentID = opponentID

    def shipList(self):
        for ship in range(self.shipCount):
            Ship(Ship.shipHitpoints()[ship],Ship.shipID, Ship.alive)
            self.ships.append(Ship.shipID)

    def shoot(self, shot_posX, shot_posY, gameBoardID):
        if shot_posX == gameBoardID.shipPlaced and shot_posY == gameBoardID.shipPlaced:
            print(f'{self.name} has hit a ship!')
        else:
            print(f'{self.name} misses!')

    def placeShips(self):
        ...

    def destroyedShip(self, oppnonentID):
        self.shipsDestroyed += 1

        if self.shipsDestroyed == 1:
            print(f'{self.name} has destroyed their first ship!')
        elif self.shipsDestroyed >= 3:
            print(f'{self.name} has destroyed {self.shipsDestroyed}! They have nearly won!!')
            print(f'{oppnonentID.name} hurry up and destroy some of their ships!')

    def win(self, opponentID):
        print(f'{self.name} wins the game!!')
        print(f'{self.name} has beaten {opponentID.name}!')

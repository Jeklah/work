from random import randint


class Ship:
    """Battleship class for the ships in the game."""

    def __init__(self, hitpoints, shipID=randint(), alive=True):
        self.hitpoints = hitpoints
        self.posX = 0
        self.posY = 0
        self.alive = alive
        self.name = ''
        self.shipID = shipID

    def shipHit(self):
        self.hitpoints = self.hitpoints - 1

        if self.hitpoints <= 0:
            print(f'{self.name} has been destroyed!')
            self.alive = False
        else:
            print(f'{self.name} has been hit! {self.name} has {self.hitpoints} left')

    def shipDestroyed(self, playerID):
        print(f'{self.name} sinks into the ocean slowly...')

        if playerID.shipsDestroyed >= 1:
            print(f'{playerID.name} has destroyed another ship!')
        else:
            print(f'{playerID.name} has destroyed a ship!')

    def shipHitpoints():
        return [5, 4, 3, 3, 2]

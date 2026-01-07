import json, os

class Currency:
    def __init__(self):
        self.amount = 0
        self.load()

    def add(self, value):
        self.amount += value
        self.save()

    def spend(self, value):
        if self.amount >= value:
            self.amount -= value
            self.save()
            return True
        return False

    def save(self):
        if not os.path.exists('saves'):
            os.makedirs('saves')
        with open('saves/currency.json', 'w') as f:
            json.dump({'amount': self.amount}, f)

    def load(self):
        try:
            with open('saves/currency.json', 'r') as f:
                self.amount = json.load(f).get('amount', 0)
        except FileNotFoundError:
            self.amount = 0

currency = Currency()

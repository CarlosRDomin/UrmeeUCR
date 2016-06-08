import random
from main import NUMBER_OF_USERS


class ExperimentUser:
	COMPUTER = "COMPUTER"
	NOBODY = ""

	def __init__(self, ip="127.0.0.1"):
		self.ip = ip
		self.waiting = True
		self.matched_with = self.NOBODY
		self.starts_first = False
		self.is_seller = False
		self.valuation = 0
		self.opponent_offer = 0
		self.profit = 0
		self.deal_accepted = False

	def __repr__(self):
		return "<User {} ({}, {}) -> {}>".format(self.ip, "1st" if self.starts_first else "2nd", "Seller" if self.is_seller else "Buyer", self.matched_with)

	def __hash__(self):
		return hash(self.ip)

	def __eq__(self, other):
		if isinstance(other, self.__class__):
			return self.ip == other.ip
		elif isinstance(other, str):
			return self.ip == other
		else:
			return False


class ExperimentUserSet(set):
	def __init__(self):
		super(ExperimentUserSet, self).__init__()
		self.cnt_waiting = 0

	def add(self, *args, **kwargs):
		super(ExperimentUserSet, self).add(args[0] if isinstance(args[0], ExperimentUser) else ExperimentUser(args[0]))

	def get_user(self, u):
		# Note: self & set([u]) returns u (with its properties). In order to retrieve the object in self with matching ip as u,
		# we first compute (self-u)=(all elements in self except for u) and then do (self-that)=(u)
		try:
			user = (self - (self - {u})).pop()
			return user
		except KeyError:  # If not found, pop() will try to remove an item on an empty set -> Return None
			return None

	def random_combination(self):  # From http://docs.python.org/2/library/itertools.html#recipes
		l = list(self)
		random.shuffle(l)
		for i in range(0, len(l), 2):
			l[i].matched_with = l[i+1].ip
			l[i+1].matched_with = l[i].ip
			l[i].starts_first = (random.random() > 0.5)
			l[i+1].starts_first = not l[i].starts_first
			l[i].is_seller = (random.random() > 0.5)
			l[i+1].is_seller = not l[i].is_seller
			l[i].valuation = 50
			l[i+1].valuation = 60
			l[i].opponent_offer = l[i+1].opponent_offer = 0
			l[i].profit = l[i+1].profit = 0
			l[i].deal_accepted = l[i+1].deal_accepted = False
		return self

	def refresh_cnt(self):
		cnt_waiting = 0
		for i in self:
			if i.waiting:
				cnt_waiting += 1
		self.cnt_waiting = cnt_waiting

		if self.cnt_waiting >= NUMBER_OF_USERS:  # Make random matches
			self.random_combination()


if __name__ == '__main__':
	random.seed(100)
	a = ExperimentUserSet()
	a.add(("192.168.0.1"))
	b = ExperimentUser("hola")
	b.valuation = 10
	a.add(b)
	c = ExperimentUser("ey")
	c.valuation = 20
	a.add(c)
	d = ExperimentUser("tio")
	d.valuation = 30
	a.add(d)
	print a
	print a.get_user("ey")
	print a.random_combination()
	print a.random_combination()
	print a.random_combination()
	a.refresh_cnt()

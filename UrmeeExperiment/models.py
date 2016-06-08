from UrmeeExperiment.core import db
from UrmeeExperiment.experiment_settings import *
import random
from enum import Enum
from sqlalchemy_enum34 import EnumType


class States(Enum):
	login = "login"
	wait = "wait"
	match = "match"
	match_complete = "match_complete"


class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	login_date = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
	experiment_day = db.Column(db.Integer, nullable=False)
	ip = db.Column(db.String(15), nullable=False)
	state = db.Column(EnumType(States), nullable=False, default=States.login)
	roles = db.relationship("Role", backref=db.backref("user", uselist=False), lazy='dynamic', order_by="Role.role_date.desc()", uselist=True)
	db.Index("unique_user_id", experiment_day, ip, unique=True)

	COMPUTER_IP = "Computer"
	TODAYS_EXPERIMENT_DAY = 0

	def __init__(self, ip=COMPUTER_IP, experiment_day=0, waiting=False, login_date=None):
		self.ip = ip
		self.experiment_day = experiment_day if experiment_day > 0 else User.TODAYS_EXPERIMENT_DAY
		self.waiting = waiting
		if login_date is not None:
			self.login_date = login_date

	def __repr__(self):
		return "<User {}-{}>".format(self.ip, self.experiment_day)


class Role(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	role_date = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
	user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	starts_first = db.Column(db.Boolean, nullable=False)
	is_seller = db.Column(db.Boolean, nullable=False)
	valuation = db.Column(db.Float, nullable=False)
	offers = db.relationship("Offer", backref=db.backref("role", uselist=False), order_by="Offer.offer_date.desc()", uselist=True)
	db.Index("user_idx", user_id)

	def __init__(self, user_id, starts_first=None, is_seller=None, valuation=0, role_date=None):
		self.user_id = user_id
		self.starts_first = starts_first if starts_first is not None else (random.random() > 0.5)
		self.is_seller = is_seller if is_seller is not None else (random.random() > 0.5)
		self.valuation = valuation if valuation > 0 else (50 if self.is_seller else 60)
		if role_date is not None:
			self.role_date = role_date

	def __repr__(self):
		return "<Role by user {}: {}, {}, ${}>".format(self.user_id, "1st" if self.starts_first else "2nd", "Seller" if self.is_seller else "Buyer", self.valuation)


class Match(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	match_date = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
	role_1_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False, unique=True, index=True)
	role_2_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False, unique=True, index=True)
	roles = db.relationship("Role", backref=db.backref("match", uselist=False), primaryjoin=db.or_(Role.id==role_1_id, Role.id==role_2_id), uselist=True)
	offers = db.relationship("Offer", backref=db.backref("match", uselist=False), order_by="Offer.offer_date.desc()", uselist=True)
	# db.Index("role_match_ids", role_1_id, role_2_id)
	# db.Index("role_1_idx", role_1_id)
	# db.Index("role_2_idx", role_2_id)

	def __init__(self, role_1_id, role_2_id, match_date=None):
		self.role_1_id = role_1_id
		self.role_2_id = role_2_id
		if match_date is not None:
			self.match_date = match_date

	def __repr__(self):
		return "<Match {} - {}>".format(self.role_1_id, self.role_2_id)


class Offer(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	offer_date = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
	match_id = db.Column(db.Integer, db.ForeignKey("match.id"), nullable=False)
	offer_by = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False)
	offer_value = db.Column(db.Float, nullable=False)

	def __init__(self, match_id, offer_by, offer_value, offer_date=None):
		self.match_id = match_id
		self.offer_by = offer_by
		self.offer_value = offer_value
		if offer_date is not None:
			self.offer_date = offer_date

	def __repr__(self):
		return "<Offer in match {} by {}: ${}>".format(self.match_id, self.offer_by, self.offer_value)


class ExperimentUser:
	computer_user = None
	COMPUTER_IP = "Computer"

	def __init__(self, ip=COMPUTER_IP):
		self.user_info = User.query.filter_by(ip=ip, experiment_day=ExperimentUser.computer_user.experiment_day).first()
		if self.user_info is None:
			self.user_info = User(ip, self.computer_user.experiment_day)
			db.session.add(self.user_info)
			db.session.commit()
		self.role_info = Role(self.user_info.id)  # Default role values
		self.match_info = None  # Not matched yet
		self.waiting = True
		self.opponent_offer = 0
		self.profit = 0
		self.deal_accepted = False

	def __repr__(self):
		return "[{}, {}, {}]".format(self.user_info, self.role_info, self.match_info)

	def __hash__(self):
		return hash(self.user_info.ip)

	def __eq__(self, other):
		if isinstance(other, self.__class__):
			return self.user_info.ip == other.user_info.ip
		elif isinstance(other, str):
			return self.user_info.ip == other
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
			l[i].role_info = Role(l[i].user_info.id, (random.random() > 0.5), (random.random() > 0.5), 50)
			l[i+1].role_info = Role(l[i+1].user_info.id, not l[i].role_info.starts_first, not l[i].role_info.is_seller, 60)
			db.session.add(l[i].role_info)
			db.session.add(l[i+1].role_info)
			db.session.commit()

			match = Match(l[i].role_info.id, l[i+1].role_info.id)
			l[i].match_info = match
			l[i+1].match_info = match
			db.session.add(match)
			db.session.commit()

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


def new_experiment_day():
	last_experiment_day = User.query.order_by(User.experiment_day.desc()).first()
	if last_experiment_day is None:  # db was empty, start by 1
		experiment_day = 1
	else:
		# To avoid creating multiple experiment_day's in a row when Debug=True (this function gets executed a couple times),
		# we count the number of users created in this experiment_day. If only one (Computer), we delete it and call recursively
		if db.session.query(db.func.count(User.id).label("cnt")).filter_by(experiment_day=last_experiment_day.experiment_day).first().cnt == 1:
			db.session.delete(last_experiment_day)  # Delete this "Computer" user, as this was an "empty" experiment
			db.session.commit()  # Make sure user gets deleted from db
			new_experiment_day()  # Call recursively in case there are more "empty" experiments
			return  # Recursive call already added "Computer" user, exit
		experiment_day = last_experiment_day.experiment_day + 1

	db.session.add(User(experiment_day=experiment_day, waiting=False))
	db.session.commit()
	User.TODAYS_EXPERIMENT_DAY = experiment_day

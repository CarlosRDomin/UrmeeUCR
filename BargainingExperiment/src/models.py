import random
from enum import Enum
from sqlalchemy_enum34 import EnumType
from BargainingExperiment.src.core import db


class States(Enum):
	login = "login"
	wait = "wait"
	match = "match"
	match_complete = "match_complete"
	experiment_complete = "experiment_complete"


class UserType(Enum):
	computer = 0
	users = 1

COMPUTER = UserType.computer
USERS = UserType.users


class StartingRole(Enum):
	buyer = 0
	seller = 1
	random = 2

BUYER_FIRST = StartingRole.buyer
SELLER_FIRST = StartingRole.seller
RANDOM_FIRST = StartingRole.random

SELLER_LOW	= 0
BUYER_LOW	= 1
SELLER_HIGH	= 2
BUYER_HIGH	= 3

import BargainingExperiment.config.experiment_settings as EXPERIMENT_SETTS  # Need to import experiment_settings after the enums above have been defined (so they can be used in the settings file)


class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	login_date = db.Column(db.DateTime, nullable=False, default=db.func.now())
	quit_date = db.Column(db.DateTime, nullable=True, default=None)
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
		return "<User {} (day {}) | Role: {} | State: {}>".format(self.ip, self.experiment_day,
				"No roles yet" if self.roles.count()==0 else "Seller" if self.roles.first().is_seller else "Buyer",
				self.state.name if self.quit_date is None else "quit at {}".format(self.quit_date))

	@staticmethod
	def get_computer_user():
		return User.query.filter(User.experiment_day==User.TODAYS_EXPERIMENT_DAY, User.ip==User.COMPUTER_IP).first()


class Role(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	role_date = db.Column(db.DateTime, nullable=False, default=db.func.now())
	user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	starts_first = db.Column(db.Boolean, nullable=False)
	is_seller = db.Column(db.Boolean, nullable=False)
	valuation = db.Column(db.Float, nullable=False)
	offers = db.relationship("Offer", backref=db.backref("role", uselist=False), order_by="Offer.offer_date.desc()", uselist=True)
	db.Index("user_idx", user_id)

	def __init__(self, user_id, starts_first=None, is_seller=None, valuation=0, role_date=None):
		self.user_id = user_id
		self.is_seller = is_seller if is_seller is not None else (random.random() > 0.5)
		self.starts_first = starts_first if starts_first is not None else self.is_seller if EXPERIMENT_SETTS.MATCH_STARTED_BY==SELLER_FIRST else not self.is_seller if EXPERIMENT_SETTS.MATCH_STARTED_BY==BUYER_FIRST else (random.random() > 0.5)
		self.valuation = valuation if valuation > 0 else EXPERIMENT_SETTS.VALUATION_SET[int(not self.is_seller) + 2*(random.random() > (EXPERIMENT_SETTS.PROB_SELLER_LOW if self.is_seller else EXPERIMENT_SETTS.PROB_BUYER_LOW))]
		if role_date is not None:
			self.role_date = role_date

	def __repr__(self):
		return "<Role by user {}: {}, {}, ${}>".format(self.user_id, "1st" if self.starts_first else "2nd", "Seller" if self.is_seller else "Buyer", self.valuation)


class Match(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	match_date = db.Column(db.DateTime, nullable=False, default=db.func.now())
	role_1_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False, unique=True, index=True)
	role_2_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False, unique=True, index=True)
	roles = db.relationship("Role", backref=db.backref("match", uselist=False), primaryjoin=db.or_(Role.id==role_1_id, Role.id==role_2_id), uselist=True)
	offers = db.relationship("Offer", backref=db.backref("match", uselist=False), order_by="Offer.offer_date.desc()", uselist=True)
	completed = db.Column(db.Boolean, nullable=False)
	db.Index("match_date_idx", match_date)
	db.Index("completed_idx", completed)
	# db.Index("role_match_ids", role_1_id, role_2_id)
	# db.Index("role_1_idx", role_1_id)
	# db.Index("role_2_idx", role_2_id)

	def __init__(self, role_1_id, role_2_id, match_date=None, completed=False):
		self.role_1_id = role_1_id
		self.role_2_id = role_2_id
		self.completed = completed
		if match_date is not None:
			self.match_date = match_date

	def __repr__(self):
		return "<Match {} - {}; Completed: {}>".format(self.role_1_id, self.role_2_id, self.completed)


class Offer(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	offer_date = db.Column(db.DateTime, nullable=False, default=db.func.now())
	match_id = db.Column(db.Integer, db.ForeignKey("match.id"), nullable=False)
	offer_by = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False)
	offer_value = db.Column(db.Float, nullable=False)
	db.Index("offer_value_idx", offer_value)

	def __init__(self, match_id, offer_by, offer_value, offer_date=None):
		self.match_id = match_id
		self.offer_by = offer_by
		self.offer_value = offer_value
		if offer_date is not None:
			self.offer_date = offer_date

	def __repr__(self):
		return "<Offer in match {} by {}: ${}>".format(self.match_id, self.offer_by, self.offer_value)


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


# API
# from BargainingExperiment.src.core import api_manager
# api_manager.create_api(User, methods=['GET'])
# api_manager.create_api(Role, methods=['GET'])
# api_manager.create_api(Match, methods=['GET'])
# api_manager.create_api(Offer, methods=['GET', 'POST'])

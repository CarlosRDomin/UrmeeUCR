import time
from datetime import datetime, timedelta
from threading import Thread, Lock
from flask import request, render_template, url_for, redirect, jsonify
from BargainingExperiment.src import app, template_functions
from BargainingExperiment.src.app_settings import POLL_REFRESH_RATE, STATE_MACHINE_REFRESH_RATE
from BargainingExperiment.src.models import *
from BargainingExperiment.src.scheduler import schedule_even_avoid_same_class_matching


# Initialize variables and globals
# For every function in template_functions, add a jinja global variable named after the function that points to the function.
# That way, any function defined in template_functions will be available from any template as {{ function_name() }}
for f in dir(template_functions):
	if f[0] != '_':  # Ignore default functions, only interested in the ones defined by me :P
		app.jinja_env.globals.update({f: getattr(template_functions, f)})
app.jinja_env.globals.update(EXPERIMENT_SETTS=EXPERIMENT_SETTS, BUYER_LOW=BUYER_LOW, SELLER_HIGH=SELLER_HIGH, POLL_REFRESH_RATE=POLL_REFRESH_RATE, States=States)
app.jinja_env.trim_blocks = True  # For aesthetic purposes, prevent Jinja from adding '\n' before and after a {{ }} or {% %} block
app.jinja_env.lstrip_blocks = True


class StateMachine(Thread):
	def __init__(self):
		self.b_stop = False
		self.round_start_datetime = datetime.now()
		self.session_counter_match_type = self.session_counter_rounds = 0
		self.match_schedule_user_vs_user = []
		super(StateMachine, self).__init__()

	def generate_match_schedule(self):
		l = User.query.filter(User.experiment_day==User.TODAYS_EXPERIMENT_DAY, User.ip!=User.COMPUTER_IP).all()
		self.match_schedule_user_vs_user = list(schedule_even_avoid_same_class_matching(l, EXPERIMENT_SETTS.SESSION_ORDER[self.session_counter_match_type][1]))

	def generate_match_round(self):
		have_set_start_datetime = False

		if EXPERIMENT_SETTS.SESSION_ORDER[self.session_counter_match_type][0] == USERS:
			if self.session_counter_rounds == 0:
				self.generate_match_schedule()

			for m in self.match_schedule_user_vs_user[self.session_counter_rounds]:
				role1 = Role(m[0].id, is_seller=True)
				role2 = Role(m[1].id, not role1.starts_first, not role1.is_seller)
				with db_lock:
					db.session.add_all([role1, role2])
					db.session.commit()
				match = Match(role1.id, role2.id)
				m[0].state = m[1].state = States.match
				with db_lock:
					db.session.add(match)
					db.session.commit()
				if not have_set_start_datetime:
					have_set_start_datetime = True
					self.round_start_datetime = match.match_date  # Save the start datetime of this round, so we can filter which matches to look at (and determine if computer needs to play)
		else:
			l = User.query.filter(User.experiment_day==User.TODAYS_EXPERIMENT_DAY, User.ip!=User.COMPUTER_IP).all()
			for i, u in enumerate(l):
				role1 = Role(u.id, is_seller=i<len(l)/2)
				role2 = Role(User.get_computer_user().id, not role1.starts_first, not role1.is_seller)
				with db_lock:
					db.session.add_all([role1, role2])
					db.session.commit()
				match = Match(role1.id, role2.id)
				u.state = States.match
				with db_lock:
					db.session.add(match)
					db.session.commit()
				if not have_set_start_datetime:
					have_set_start_datetime = True
					self.round_start_datetime = match.match_date  # Save the start datetime of this round, so we can filter which matches to look at (and determine if computer needs to play)

		self.session_counter_rounds += 1
		if self.session_counter_rounds >= EXPERIMENT_SETTS.SESSION_ORDER[self.session_counter_match_type][1]:
			self.session_counter_rounds = 0
			self.session_counter_match_type += 1
			if self.session_counter_match_type > len(EXPERIMENT_SETTS.SESSION_ORDER):
				print "Last round!!!"

	# def generate_random_combination_old(self):  # From http://docs.python.org/2/library/itertools.html#recipes
	# 	l = User.query.filter(User.experiment_day==User.TODAYS_EXPERIMENT_DAY, User.ip!=User.COMPUTER_IP).all()
	# 	random.shuffle(l)
	# 	for i in range(0, len(l), 2):
	# 		role1 = Role(l[i].id)
	# 		role2 = Role(l[i + 1].id, not role1.starts_first, not role1.is_seller)
	# 		db.session.add_all([role1, role2])
	# 		db.session.commit()
	# 		match = Match(role1.id, role2.id)
	# 		l[i].state = l[i+1].state = States.match
	# 		db.session.add(match)
	# 		db.session.commit()

	def stop(self):
		self.b_stop = True
		print("Stopping StateMachine background thread...")

	def run(self):
		while not self.b_stop:
			with db_lock:
				db.session.commit()
			if int(get_cnt_waiting()) >= EXPERIMENT_SETTS.NUMBER_OF_USERS:
				self.generate_match_round()
			else:
				unfinished_matches = Match.query.filter(Match.match_date>=self.round_start_datetime, Match.completed==False).all()
				for m in unfinished_matches:
					for r in m.roles:
						if r.user.ip==User.COMPUTER_IP or r.user.quit_date is not None:  # Play for the computer or users who quit
							offers = m.offers
							if (len(offers)==0 and r.starts_first) or (len(offers)>0 and offers[0].offer_by!=r.id):  # My turn if I didn't do last offer
								if r.is_seller:
									if r.valuation == EXPERIMENT_SETTS.VALUATION_SET[SELLER_HIGH]:
										offer_val_index = SELLER_HIGH
									else:  # r.valuation == EXPERIMENT_SETTS.VALUATION_SET[SELLER_LOW]:
										offer_val_index = SELLER_HIGH if len(offers)<2 else BUYER_LOW  # SELLER_HIGH on 1st round, otherwise BUYER_LOW; 1st round means len(offers)<2, regardless of who started the round
								else:  # not r.is_seller:
									if r.valuation == EXPERIMENT_SETTS.VALUATION_SET[BUYER_HIGH]:
										offer_val_index = SELLER_HIGH
									else:  # r.valuation == EXPERIMENT_SETTS.VALUATION_SET[BUYER_LOW]:
										offer_val_index = BUYER_LOW
								offer_value = EXPERIMENT_SETTS.VALUATION_SET[offer_val_index]
								if process_new_offer(offer_value, r):  # Determine whether match is completed, and change user states accordingly if necessary
									continue  # If match is completed, no need to check for the other role in the match

			sleep_until = datetime.now() + timedelta(seconds=STATE_MACHINE_REFRESH_RATE)
			while datetime.now() < sleep_until:
				time.sleep(0.1)  # Sleep in 0.1s intervals until desired interval (STATE_MACHINE_REFRESH_RATE) has elapsed

		print("Successfully exited StateMachine background thread!")


background_thread = StateMachine()
db_lock = Lock()


def process_new_offer(offer_value, role):
	# Let's determine if this new offer ends the game
	if len(role.match.offers) >= EXPERIMENT_SETTS.MAX_ROUNDS-1:  # Check if we exceeded the maximum number of offer rounds allowed per match
		match_completed = True
	elif len(role.match.offers) == 0:  # This is the 1st offer, match can't finish until there are at least 2 offers
		match_completed = False
	else:  # The only way a match DOESN'T END is if buyer offered lower than seller (regardless of order)
		last_offer = role.match.offers[0].offer_value
		match_completed = not((role.is_seller and offer_value > last_offer) or (not role.is_seller and offer_value < last_offer))

	with db_lock:
		db.session.add(Offer(role.match.id, role.id, offer_value))
		role.match.completed = match_completed
		if match_completed:
			for r in role.match.roles:
				if r.user.ip != User.COMPUTER_IP:  # Don't change the state of Computer
					r.user.state = States.match_complete if background_thread.session_counter_match_type < len(EXPERIMENT_SETTS.SESSION_ORDER) else States.experiment_complete
		db.session.commit()

	return match_completed


def get_user_from_ip(ip):
	return User.query.filter_by(experiment_day=User.TODAYS_EXPERIMENT_DAY, ip=ip).first()


# Serve requests
@app.route('/user_state', methods=['GET'])
def get_user_state():
	u = get_user_from_ip(request.remote_addr)
	if u is None:
		return redirect(url_for('main'))
	return str(u.state.value)


@app.route('/wait_cnt', methods=['GET'])
def get_cnt_waiting():
	with db_lock:
		cnt = db.session.query(db.func.count(1).label("cnt")).filter(User.experiment_day==User.TODAYS_EXPERIMENT_DAY, db.or_(User.state==States.wait, User.quit_date != None)).first().cnt
	return str(cnt)


@app.route('/last_offer_info', methods=['GET'])
def get_last_offer_info():
	u = get_user_from_ip(request.remote_addr)
	if u is None or u.roles.count() == 0:
		return redirect(url_for('main'))

	match = u.roles.first().match
	offers = match.offers
	offer = offers[0].offer_value if len(offers) > 0 else None

	return jsonify({"count": len(offers), "offer": offer, "completed": match.completed})

@app.route('/quit', methods=['POST'])
def user_quit():
	u = get_user_from_ip(request.remote_addr)
	if u is not None:
		u.quit_date = db.func.now()
		u.state = States.experiment_complete
		with db_lock:
			db.session.add(u)
			db.session.commit()

	return redirect(url_for('main'))


@app.route('/', methods=['GET', 'POST'])
def main():
	u = get_user_from_ip(request.remote_addr)
	if u is None:
		u = User(request.remote_addr)
		with db_lock:
			db.session.add(u)
			db.session.commit()
	elif request.method == 'POST':  # If info was sent, process it (might transition to another state)
		globals()["process_{}".format(u.state.name)](u)
	return globals()["serve_{}".format(u.state.name)](u)


def process_login(u):
	u.state = States.wait
	with db_lock:
		db.session.commit()

def serve_login(u):
	return render_template("login.html")


def process_wait(u):
	pass

def serve_wait(u):
	return render_template("wait.html")


def process_match(u):
	offer_value = EXPERIMENT_SETTS.VALUATION_SET[BUYER_LOW if "low" in request.form["offer_option"] else SELLER_HIGH]
	process_new_offer(offer_value, u.roles.first())

def serve_match(u):
	return render_template("match.html", role=u.roles.first())


def process_match_complete(u):
	u.state = States.wait
	with db_lock:
		db.session.commit()

def serve_match_complete(u):
	return render_template("match_complete.html", role=u.roles.first())


def process_experiment_complete(u):
	pass

def serve_experiment_complete(u):
	return render_template("experiment_complete.html", user_quit=(u.quit_date is not None))

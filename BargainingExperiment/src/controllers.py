import requests
import time
from datetime import datetime, timedelta
from threading import Thread, Lock
from flask import request, render_template, url_for, redirect, jsonify
from BargainingExperiment.src import app, template_functions
from BargainingExperiment.src.app_settings import POLL_REFRESH_RATE, STATE_MACHINE_REFRESH_RATE, PORT
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

	def commit_new_roles_and_match(self, role1, role2, users, save_start_datetime):
		with db_lock:  # First, add roles and commit, so we get their id
			db.session.add_all([role1, role2])
			db.session.commit()

		match = Match(role1.id, role2.id)  # Then create match, update user(s) state and commit again
		for u in users:
			if u.quit_date is None:	u.state = States.match  # Don't change state of users who quit (they should remain in experiment_complete)
		with db_lock:
			db.session.add(match)
			db.session.commit()

		if save_start_datetime:  # If not done yet, save the start datetime of this round, so we can filter which matches to look at (and determine if computer needs to play)
			self.round_start_datetime = match.match_date

	def play_matches_as_computer(self):
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
							break  # If match is completed, no need to check for the other role in the match

	def generate_match_schedule(self):
		l = User.query.filter(User.experiment_day==User.TODAYS_EXPERIMENT_DAY, User.ip!=User.COMPUTER_IP).all()
		self.match_schedule_user_vs_user = list(schedule_even_avoid_same_class_matching(l, EXPERIMENT_SETTS.SESSION_ORDER[self.session_counter_match_type][1]))

	def generate_match_round(self):
		if self.session_counter_match_type >= len(EXPERIMENT_SETTS.SESSION_ORDER):  # Sanity check (shouldn't happen, unless all users quit before the end -> State machine never attempts to play for them, just generates new matches, so this would prevent crashing and would end the experiment)
			print "Experiment completed! :)"
			self.stop()
			return

		if EXPERIMENT_SETTS.SESSION_ORDER[self.session_counter_match_type][0] == USERS:  # Current match type is users vs users
			if self.session_counter_rounds == 0:  # Only need to generate a schedule before the first match
				self.generate_match_schedule()

			for i, m in enumerate(self.match_schedule_user_vs_user[self.session_counter_rounds]):  # Then, generate the roles for current match based on schedule
				role1 = Role(m[0].id, is_seller=True)  # For now, roles remain constant throughout the session -> First half of users (m[0]'s) always sellers, second half (m[1]'s) always buyers
				role2 = Role(m[1].id, not role1.starts_first, not role1.is_seller)
				self.commit_new_roles_and_match(role1, role2, m, i == 0)
		else:  # Current match type is users vs computer
			l = User.query.filter(User.experiment_day==User.TODAYS_EXPERIMENT_DAY, User.ip!=User.COMPUTER_IP).all()
			for i, u in enumerate(l):
				role1 = Role(u.id, is_seller=i<len(l)/2)  # For now, roles remain constant throughout the session -> First half of users are always sellers, second half are always buyers
				role2 = Role(User.get_computer_user().id, not role1.starts_first, not role1.is_seller)
				self.commit_new_roles_and_match(role1, role2, [u], i == 0)

		self.session_counter_rounds += 1
		if self.session_counter_rounds >= EXPERIMENT_SETTS.SESSION_ORDER[self.session_counter_match_type][1]:
			self.session_counter_rounds = 0
			self.session_counter_match_type += 1
			if self.session_counter_match_type >= len(EXPERIMENT_SETTS.SESSION_ORDER):
				print "Last round!!!"

	@staticmethod
	def shutdown_server():
		requests.post('http://localhost:{}/shutdown'.format(PORT))

	def stop(self):
		self.b_stop = True
		print("Stopping StateMachine background thread...")

	def run(self):
		while not self.b_stop:
			with db_lock:
				db.session.commit()  # For some reason, if we don't commit, some changes won't be reflected, and we'd get a wrong count for #users waiting

			if int(get_cnt_done()) >= EXPERIMENT_SETTS.NUMBER_OF_USERS:  # If all users are done, finish experiment
				self.stop()
			elif int(get_cnt_waiting()) >= EXPERIMENT_SETTS.NUMBER_OF_USERS:  # If all users are waiting (and some still haven't quit/finished the experiment), generate new matches
				self.generate_match_round()
			else:  # Otherwise, some users are still playing. Play for the computer (or users who quit) if necessary
				self.play_matches_as_computer()

			sleep_until = datetime.now() + timedelta(seconds=STATE_MACHINE_REFRESH_RATE)
			while datetime.now() < sleep_until:
				time.sleep(0.1)  # Sleep in 0.1s intervals until desired interval (STATE_MACHINE_REFRESH_RATE) has elapsed

		print("Successfully exited StateMachine background thread!")
		self.shutdown_server()


background_thread = StateMachine()
db_lock = Lock()


def process_new_offer(offer_value, role):
	match_completed = False  # Let's determine if this new offer ends the game
	if len(role.match.offers) >= 2*EXPERIMENT_SETTS.MAX_ROUNDS-1:  # Check if we exceeded the maximum number of offer rounds allowed per match
		match_completed = True
	elif len(role.match.offers) % 2 == 1:  # Offers are made in pairs! We can't close a deal on an offer from the role who started, it can only be after a counter-offer (meaning there has to be an odd number of offers registered so far)
		last_offer = role.match.offers[0].offer_value
		match_completed = not((role.is_seller and offer_value > last_offer) or (not role.is_seller and offer_value < last_offer))  # The only way a match DOESN'T END is if buyer offered lower than seller (regardless of order)

	with db_lock:
		db.session.add(Offer(role.match.id, role.id, offer_value))
		role.match.completed = match_completed
		if match_completed:
			for r in role.match.roles:
				if r.user.ip != User.COMPUTER_IP and r.user.quit_date is None:  # Don't change the state of Computer or of users who quit
					r.user.state = States.match_complete
		db.session.commit()

	return match_completed


def compute_match_profit(role):
	if role.match is not None and len(role.match.offers) >= 2 and (role.user.quit_date is None or role.user.quit_date > role.match.offers[0].offer_date):  # Prevent crashing if less than 2 offers were submitted (maybe user quit before end of 1st round?), and only count games until user quit
		deal_price = min(role.match.offers[0].offer_value, role.match.offers[1].offer_value)
		num_rounds = int((len(role.match.offers)+1)/2.)  # int()=floor(), so we want 1-2 offers -> 1 round; 3-4 offers -> 2 rounds; 5-6 offers -> 3 rounds; and so on...
		discount = (1 - EXPERIMENT_SETTS.INTEREST_PER_ROUND)**(num_rounds - 1)
	else:  # Should never happen that there are less than 2 offers submitted, but just in case, assign default values
		deal_price = role.valuation  # Force profit=0
		num_rounds = 0
		discount = 1.00
	profit = max(0, (deal_price - role.valuation)*discount*(-1 if not role.is_seller else 1))

	return profit, deal_price, num_rounds, discount


def get_user_from_ip(ip):
	return User.query.filter_by(experiment_day=User.TODAYS_EXPERIMENT_DAY, ip=ip).first()


# Serve requests
@app.route('/user_state', methods=['GET'])
def get_user_state():
	u = get_user_from_ip(request.remote_addr)
	if u is None:
		return redirect(url_for('main'))
	return str(u.state.value)


@app.route('/done_cnt', methods=['GET'])
def get_cnt_done():
	with db_lock:
		cnt = db.session.query(db.func.count(1).label("cnt")).filter(User.experiment_day==User.TODAYS_EXPERIMENT_DAY, User.state==States.experiment_complete).first().cnt
	return str(cnt)


@app.route('/wait_cnt', methods=['GET'])
def get_cnt_waiting():
	with db_lock:
		cnt = db.session.query(db.func.count(1).label("cnt")).filter(User.experiment_day==User.TODAYS_EXPERIMENT_DAY, db.or_(User.state==States.wait, User.quit_date!=None)).first().cnt
	return str(cnt)


@app.route('/last_offer_info', methods=['GET'])
def get_last_offer_info():
	u = get_user_from_ip(request.remote_addr)
	if u is None or u.roles.count() == 0:
		return jsonify({"count": 0, "offer": 0, "completed": True})  # Completed=True will force a redirect to main, so no need to return redirect(url_for('main'))

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


@app.route('/shutdown', methods=['POST'])
def server_shutdown():
	func = request.environ.get('werkzeug.server.shutdown')
	if func is None:  # Sanity check
		raise RuntimeError('Not running with the Werkzeug Server!')

	print "Shutting down server... ",
	func()  # Shutdown server
	print "Success!"

	return "Server shutdown successful!"  # Return something so server doesn't raise an Exception


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
	u.state = States.wait if background_thread.session_counter_match_type < len(EXPERIMENT_SETTS.SESSION_ORDER) and u.quit_date is None else States.experiment_complete  # Switch to wait only if there's more games to play and user hasn't quit
	with db_lock:
		db.session.commit()

def serve_match_complete(u):
	role = u.roles.first()
	profit, deal_price, num_rounds, discount = compute_match_profit(role)

	return render_template("match_complete.html", profit=profit, num_rounds=num_rounds, discount=discount, deal_price=deal_price, role=role)


def process_experiment_complete(u):
	pass

def serve_experiment_complete(u):
	profit = 0  # Initialize cumulative profit
	for r in u.roles:  # For every role played by the user
		profit += compute_match_profit(r)[0]  # Accumulate winnings

	return render_template("experiment_complete.html", user_quit=(u.quit_date is not None), profit=profit)

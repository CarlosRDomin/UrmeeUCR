from flask import request, render_template, url_for, redirect, jsonify
from BargainingExperiment.src import app
from BargainingExperiment.src import template_functions
from BargainingExperiment.src.app_settings import POLL_REFRESH_RATE
from BargainingExperiment.src.models import *
from BargainingExperiment.config.experiment_settings import *

# API
# from BargainingExperiment.src.core import api_manager
# api_manager.create_api(User, methods=['GET'])
# api_manager.create_api(Role, methods=['GET'])
# api_manager.create_api(Match, methods=['GET'])
# api_manager.create_api(Offer, methods=['GET', 'POST'])


# Initialize variables and globals
# For every function in template_functions, add a jinja global variable named after the function that points to the function.
# That way, any function defined in template_functions will be available from any template as {{ function_name() }}
for f in dir(template_functions):
	if f[0] != '_':  # Ignore default functions, only interested in the ones defined by me :P
		app.jinja_env.globals.update({f: getattr(template_functions, f)})
app.jinja_env.globals.update(NUMBER_OF_USERS=NUMBER_OF_USERS)
app.jinja_env.globals.update(INTEREST_PER_ROUND=INTEREST_PER_ROUND)
app.jinja_env.globals.update(POLL_REFRESH_RATE=POLL_REFRESH_RATE)
app.jinja_env.globals.update(States=States)
app.jinja_env.trim_blocks = True  # For aesthetic purposes, prevent Jinja from adding '\n' before and after a {{ }} or {% %} block
app.jinja_env.lstrip_blocks = True


def get_user_from_ip(ip):
	return User.query.filter_by(experiment_day=User.TODAYS_EXPERIMENT_DAY, ip=ip).first()


def generate_random_combination():  # From http://docs.python.org/2/library/itertools.html#recipes
	l = User.query.filter(User.experiment_day==User.TODAYS_EXPERIMENT_DAY, User.ip!=User.COMPUTER_IP).all()
	random.shuffle(l)
	for i in range(0, len(l), 2):
		role1 = Role(l[i].id)
		role2 = Role(l[i + 1].id, not role1.starts_first, not role1.is_seller)
		db.session.add_all([role1, role2])
		db.session.commit()
		match = Match(role1.id, role2.id)
		l[i].state = l[i+1].state = States.match
		db.session.add(match)
		db.session.commit()


# Serve requests
@app.route('/user_state', methods=['GET'])
def get_user_state():
	u = get_user_from_ip(request.remote_addr)
	if u is None:
		return redirect(url_for('main'))
	return str(u.state.value)


@app.route('/wait_cnt', methods=['GET'])
def get_cnt_waiting():
	cnt = db.session.query(db.func.count(User.id).label("cnt")).filter_by(experiment_day=User.TODAYS_EXPERIMENT_DAY, state=States.wait).first().cnt
	if cnt >= NUMBER_OF_USERS:
		generate_random_combination()
	return str(cnt)


@app.route('/last_offer_info', methods=['GET'])
def get_last_offer_info():
	u = get_user_from_ip(request.remote_addr)
	if u is None:
		return redirect(url_for('main'))

	offers = u.roles.first().match.offers
	offer = offers[0].offer_value if len(offers) > 0 else None

	return jsonify({"count": len(offers), "offer": offer})


@app.route('/', methods=['GET', 'POST'])
def main():
	u = get_user_from_ip(request.remote_addr)
	if u is None:
		u = User(request.remote_addr)
		db.session.add(u)
		db.session.commit()
	elif request.method == 'POST':  # If info was sent, process it (might transition to another state)
		globals()["process_{}".format(u.state.name)](u)
	return globals()["serve_{}".format(u.state.name)](u)


def process_login(u):
	u.state = States.wait
	db.session.commit()

def serve_login(u):
	return render_template("login.html")


def process_wait(u):
	pass

def serve_wait(u):
	return render_template("wait.html")


def process_match(u):
	offer_accept = (request.form["offer_option"] == "accept")
	offer_value = 0 if offer_accept else float(request.form["offer_value"])

	role = u.roles.first()
	if offer_accept:
		for r in role.match.roles:
			r.user.state = States.match_complete
	db.session.add(Offer(role.match.id, role.id, offer_value))
	db.session.commit()

def serve_match(u):
	return render_template("match.html", role=u.roles.first())


def process_match_complete(u):
	u.state = States.wait
	db.session.commit()

def serve_match_complete(u):
	return render_template("match_complete.html", role=u.roles.first())

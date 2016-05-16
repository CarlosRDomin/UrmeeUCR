import random
# import sqlite3
from flask import Flask, send_from_directory, request, session, g, redirect, url_for, abort, render_template, flash
from flask_settings import PORT
import template_functions


class User:

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

    def __contains__(self, item):
        return (self.ip == item.ip) if isinstance(item, self.__class__) else False

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.ip == other.ip
        elif isinstance(other, str):
            return self.ip == other
        else:
            return False


class UserList(list):
    def __init__(self):
        self.cnt_waiting = 0

    def __contains__(self, item):
        for i in self:
            if i == item:
                return True
        return False

    def get_user(self, u):
        try:
            user = self[self.index(u)]
            return user if isinstance(user, User) else User(user)
        except:
            return None

    def random_combination(self):  # From http://docs.python.org/2/library/itertools.html#recipes
        random.shuffle(self)
        sorted(self, reverse=False)
        for i in range(0, len(self), 2):
            self[i].matched_with = self[i+1].ip
            self[i+1].matched_with = self[i].ip
            self[i].starts_first = (random.random() > 0.5)
            self[i+1].starts_first = not self[i].starts_first
            self[i].is_seller = True
            self[i+1].is_seller = False
            self[i].valuation = 50
            self[i+1].valuation = 60
            self[i].opponent_offer = 0
            self[i+1].opponent_offer = 0
            self[i].profit = 0
            self[i+1].profit = 0
            self[i].deal_accepted = False
            self[i+1].deal_accepted = False


    def refresh_cnt(self):
        cnt_waiting = 0
        for i in self:
            if i.waiting == True:
                cnt_waiting += 1
        self.cnt_waiting = cnt_waiting
        if self.cnt_waiting >= NUMBER_OF_USERS:  # Make random matches
            self.random_combination()


userList = UserList()
NUMBER_OF_USERS = 2
INTEREST_PER_ROUND = 5  # (in %)

app = Flask(__name__, static_url_path='')
app.config.from_object("flask_settings")  # Looks at the given object (if it's a string it will import it) and then look for all uppercase variables defined there
app.config.from_envvar('FLASKR_SETTINGS', silent=True)  # Environment variable FLASKR_SETTINGS can be set to specify a config file to be loaded, which would override the default values (silent switch just tells Flask to not complain if no such environment key is set)

# For every function in template_functions, add a jinja global variable named after the function that points to the function.
# That way, any function defined in template_functions will be available from any template as {{ function_name() }}
for f in dir(template_functions):
    if f[0] != '_':  # Ignore default functions, only interested in the ones defined by me :P
        app.jinja_env.globals.update({f: getattr(template_functions, f)})
app.jinja_env.globals.update(NUMBER_OF_USERS=NUMBER_OF_USERS)
app.jinja_env.globals.update(INTEREST_PER_ROUND=INTEREST_PER_ROUND)
app.jinja_env.trim_blocks = True  # For aesthetic purposes, prevent Jinja from adding '\n' before and after a {{ }} or {% %} block
app.jinja_env.lstrip_blocks = True


# @app.route('/css/<path:path>')
# def send_css(path):
#     return send_from_directory(os.path.join(app.static_folder, 'css'), path)


# @app.route('/js/<path:path>')
# def send_js(path):
#     return send_from_directory(os.path.join(app.static_folder, 'js'), path)

@app.route('/', methods=['GET'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.remote_addr not in userList:
            userList.append(User(request.remote_addr))
            return redirect(url_for('wait'))
        else:
            flash("You already have a tab/window open on this computer,<br>please close this tab and return to the other one.")
    # if request.method == 'GET' or error logging in
    return render_template("login.html")

@app.route('/wait', methods=['GET'])
def wait():
    u = userList.get_user(request.remote_addr)
    if u is None:  # If user is not found, take him back to the start
        flash("An error occurred when trying to access the page 'wait'.<br>The system doesn't recognize your login credentials,<br>please login again to return to the experiment.")
        return redirect(url_for('login'))

    u.waiting = True
    userList.refresh_cnt()
    return render_template("wait.html")

@app.route('/wait_progress', methods=['GET'])
def wait_progress():
    u = userList.get_user(request.remote_addr)
    if u is None:  # If user is not found, take him back to the start
        flash("An error occurred when trying to access the page 'wait_progress'.<br>The system doesn't recognize your login credentials,<br>please login again to return to the experiment.")
        return redirect(url_for('login'))

    return render_template("progress.html", on_load=u'parent.updateProg({}, {:d})'.format(userList.cnt_waiting, u.matched_with!=u.NOBODY), refresh_period=3)

@app.route('/match', methods=['GET'])
def match():
    # if request.method == 'POST':
        # offer_out_accept = (request.args.get('offer_out_option', 'decline') == 'accept')
        # offer_out = float(request.args.get('offer_out_value', 20))
        #
        # if offer_out_accept:
        #     return redirect(url_for('match_complete', profit=(offer_out-20)))


        # if offer_in_accept:
        #     return redirect(url_for('match_complete', is_seller=request.form["is_seller"], profit=profit, offer_in_value=offer_in_value, valuation=request.form["valuation"]))
        # else:
        #     return render_template("match.html", is_seller=request.form["is_seller"], valuation=request.form["valuation"], offer_in="")
    # else:  # request.method == 'GET'
        u = userList.get_user(request.remote_addr)
        if u is None:  # If user is not found, take him back to the start
            flash("An error occurred when trying to access the page 'match'.<br>The system doesn't recognize your login credentials,<br>please login again to return to the experiment.")
            return redirect(url_for('login'))

        u.waiting = False
        userList.refresh_cnt()
        return render_template("match.html", is_seller=u.is_seller, valuation=u.valuation, starts_first=u.starts_first)

@app.route('/offer', methods=['POST'])
def offer():
    u = userList.get_user(request.remote_addr)
    if u is None:  # If user is not found, take him back to the start
        flash("An error occurred when trying to access the page 'offer'.<br>The system doesn't recognize your login credentials,<br>please login again to return to the experiment.")
        return redirect(url_for('login'))

    offer_in_accept = (request.form["offer_out_option"] == "accept")
    offer_in_value = float(request.form["offer_in"]) if offer_in_accept else float(request.form["offer_out_value"])

    profit = (((100 - INTEREST_PER_ROUND) / 100.0) ** (int(request.form["negotiation_round"]) - 1))
    if u.is_seller:
        profit *= max(offer_in_value - u.valuation, 0)
    else:
        profit *= max(u.valuation - offer_in_value, 0)

    u.profit = profit  # Projected profit if offer gets accepted
    userList.get_user(u.matched_with).opponent_offer = offer_in_value
    if offer_in_accept:
        u.deal_accepted = True
        userList.get_user(u.matched_with).deal_accepted = True
    else:
        u.opponent_offer = 0

    return redirect(url_for('offer_progress'))

@app.route('/offer_progress', methods=['GET'])
def offer_progress():
    u = userList.get_user(request.remote_addr)
    if u is None:  # If user is not found, take him back to the start
        flash("An error occurred when trying to access the page 'offer_progress'.<br>The system doesn't recognize your login credentials,<br>please login again to return to the experiment.")
        return redirect(url_for('login'))

    return render_template("progress.html", on_load=u'parent.updateOffer({:f}, {:d})'.format(u.opponent_offer, u.deal_accepted), refresh_period=3)

@app.route('/match_complete', methods=['GET'])
def match_complete():
    u = userList.get_user(request.remote_addr)
    if u is None:  # If user is not found, take him back to the start
        flash("An error occurred when trying to access the page 'match_complete'.<br>The system doesn't recognize your login credentials,<br>please login again to return to the experiment.")
        return redirect(url_for('login'))

    u.matched_with = u.NOBODY
    return render_template("match_complete.html", final_offer=u.opponent_offer, profit=u.profit)

@app.route('/new_match', methods=['GET'])
def new_match():
    return redirect(url_for('wait'))


# def connect_db():
#     return sqlite3.connect(app.config['DATABASE'])


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=PORT)

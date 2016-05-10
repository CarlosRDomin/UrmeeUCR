import os
import sqlite3
from flask import Flask, send_from_directory, request, session, g, redirect, url_for, abort, render_template, flash

# configuration
DATABASE = '/tmp/experiment.db'
DEBUG = True
SECRET_KEY = os.urandom(24)  # 'developmentKey'
USERNAME = 'Carlos'
PASSWORD = 'adminPass'

app = Flask(__name__, static_url_path='')
app.config.from_object(__name__)  # Looks at the given object (if it's a string it will import it) and then look for all uppercase variables defined there
app.config.from_envvar('FLASKR_SETTINGS', silent=True)  # Environment variable FLASKR_SETTINGS can be set to specify a config file to be loaded, which would override the default values (silent switch just tells Flask to not complain if no such environment key is set)


@app.route('/')
def hello_world():
    return 'Hello World! Your IP seems to be {}'.format(request.remote_addr)


# @app.route('/css/<path:path>')
# def send_css(path):
#     return send_from_directory(os.path.join(app.static_folder, 'css'), path)


# @app.route('/js/<path:path>')
# def send_js(path):
#     return send_from_directory(os.path.join(app.static_folder, 'js'), path)


@app.route('/template', methods=['GET'])
def projects():
    return render_template("template.html", msg=request.args.get('msg', 'Default message :P'))


def connect_db():
    return sqlite3.connect(app.config['DATABASE'])


if __name__ == '__main__':
    app.run(port=5000, debug=DEBUG)

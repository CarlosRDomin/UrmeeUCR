from UrmeeExperiment import app
from UrmeeExperiment.settings import PORT
from UrmeeExperiment.models import new_experiment_day
from manage_db import create_db, drop_db


def run_server():
	# drop_db()
	create_db()
	new_experiment_day()
	app.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
	run_server()

from BargainingExperiment.src import app
from BargainingExperiment.src.app_settings import PORT
from BargainingExperiment.src.models import new_experiment_day
from BargainingExperiment.manage_db import create_db


def run_server():
	# drop_db()
	create_db()
	new_experiment_day()
	app.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
	run_server()

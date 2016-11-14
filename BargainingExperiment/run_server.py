import update_sys_path
from BargainingExperiment.src import app
from BargainingExperiment.src.app_settings import PORT
from BargainingExperiment.src.models import new_experiment_day
from BargainingExperiment.src.controllers import background_thread
from BargainingExperiment.manage_db import create_db, drop_db


def run_server(delete_db=False):
	if delete_db:
		drop_db()
	create_db()
	new_experiment_day()
	background_thread.start()
	try:
		app.run(host='0.0.0.0', port=PORT)
	finally:
		background_thread.stop()

if __name__ == '__main__':
	run_server()

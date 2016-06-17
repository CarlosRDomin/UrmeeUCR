import argparse
import warnings
from BargainingExperiment.config.db_settings import SQLALCHEMY_DATABASE_URI
from BargainingExperiment.src.core import db


def create_db():
	db_uri = SQLALCHEMY_DATABASE_URI.rsplit("/", 1)  # Split database_uri (protocol, username, pass) and database_name (db name)
	engine = db.create_engine(db_uri[0])  # connect to server
	with warnings.catch_warnings():
		warnings.simplefilter("ignore")  # Ignore the warning thrown by MySQL saying that the db already exists
		engine.execute("CREATE DATABASE IF NOT EXISTS {}".format(db_uri[1]))  # create db
	db.create_all()


def drop_db():
	db.drop_all()


def main():
	parser = argparse.ArgumentParser(description='Manage the database for our application.')
	parser.add_argument('command', help='the name of the command you want to run')
	args = parser.parse_args()

	if args.command == 'create_db':
		create_db()
	elif args.command == 'delete_db':
		drop_db()
	else:
		raise Exception('Invalid command')

if __name__ == '__main__':
	main()

from flask import Flask


app = Flask(__name__, static_url_path='')
app.config.from_object('BargainingExperiment.src.app_settings')
app.config.from_object('BargainingExperiment.config.db_settings')

import BargainingExperiment.src.core
import BargainingExperiment.src.models
import BargainingExperiment.src.controllers

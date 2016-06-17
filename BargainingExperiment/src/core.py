from enum import Enum
from flask_sqlalchemy import SQLAlchemy
from flask_restless import APIManager
from flask.json import JSONEncoder
from BargainingExperiment.src import app


class CustomEnumJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, Enum):
                return obj.value
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)


db = SQLAlchemy(app)
app.json_encoder = CustomEnumJSONEncoder
api_manager = APIManager(app, flask_sqlalchemy_db=db)

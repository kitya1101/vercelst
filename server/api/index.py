from flask import Flask, request
from flask_cors import CORS
from app import app as flask_app

app = Flask(__name__)
CORS(app)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return flask_app(request.environ, lambda x, y: None)

def handler(event, context):
    return app(event, context)
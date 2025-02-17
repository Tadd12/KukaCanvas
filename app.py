import os

from flask import Flask

from website.kuka_app import kuka_app
from flask_session import Session

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'your_secret_key'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure server-side session storage
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

app.register_blueprint(kuka_app, url_prefix='/kuka')

if __name__ == '__main__':
    app.run(debug=True)
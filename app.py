from functools import wraps
from uuid import uuid4, UUID

from flask import Flask, request, Response, session, redirect, url_for, jsonify,render_template
from jinja2 import Template


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

app = Flask(__name__)
app.secret_key = bytes.fromhex(
    'dfba670ebc21410076bb5941140e789ac6342e09c18da920'
)
app.fishes = {}


def get_fish_from_json():
    fish_data = request.get_json()
    if not fish_data:
        raise InvalidUsage('Please provide json data')
    return fish_data


def set_fish(fish_id=None, data=None, update=False):
    if fish_id is None:
        fish_id = str(uuid4())

    if data is None:
        data = get_fish_from_json()
        if data is None:
            raise InvalidUsage('Please provide json data')

    if update:
        app.fishes[fish_id].update(data)
    else:
        app.fishes[fish_id] = data

    return fish_id


@app.route('/')
def root():
    return 'Hello, World!'


def check_auth(username, password):
    """This function is called to check if a username password combination is
    valid."""
    return username == 'TRAIN' and password == 'TuN3L'


def please_authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response('Could not verify your access level for that URL.\n'
                    'You have to login with proper credentials', 401,
                    {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_basic_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return please_authenticate()
        return func(*args, **kwargs)

    return wrapper


@app.route('/login/', methods=['GET', 'POST'])
@requires_basic_auth
def login():
    session['username'] = request.authorization.username
    return redirect('/hello')


def requires_user_session(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('username'):
            return redirect('/login/')
        return func(*args, **kwargs)

    return wrapper
template = Template('<p id="greeting"> Hello, {{user}}!</p>')

@app.route('/hello')
@requires_user_session
def hello():
    x=session['username']
    render = template.render(user=str(x))
    return render



@app.route('/logout/', methods=['GET', 'POST'])
@requires_user_session
def logout():
    if request.method == 'GET':
        return redirect('/')
    del session['username']
    return redirect('/')


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

# @app.route('/trains', methods=['GET','POST'])
# @requires_user_session
# def trains():



@app.route('/trains', methods=['GET', 'POST'])
@requires_user_session
def fishes():
    if request.method == 'GET':
        return jsonify(app.fishes)
    elif request.method == 'POST':
        fish_id = set_fish()
        return redirect(url_for('fish', fish_id=fish_id, format='json'))


@app.route('/trains/<fish_id>',
           methods=['GET', 'PUT', 'PATCH', 'DELETE'])
def fish(fish_id):
    if fish_id not in app.fishes:
        return 'No such fish', 204

    if request.method == 'DELETE':
        del app.fishes[fish_id]
        return '', 204

    if request.method == 'PUT':
        set_fish(fish_id)
    elif request.method == 'PATCH':
        set_fish(fish_id, update=True)

    if request.method == 'GET' and request.args.get('format') != 'json':
        raise InvalidUsage("Missing 'format=json' in query string.",
                           status_code=415)
    return jsonify(app.fishes[fish_id])


if __name__ == '__main__':
    app.run(debug=True, use_debugger=False)

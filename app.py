
import sqlite3
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, g)
from jinja2 import DictLoader
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'change-this-secret-key'
DB = 'app.db'

BASE = '''<!doctype html>
<html><head><meta charset='utf-8'><title>Task Manager</title>
<style>
body{font-family:Arial;max-width:500px;margin:40px auto;padding:0 15px}
.flash{background:#ffe9e9;padding:8px;margin:8px 0;border-radius:4px}
.done{text-decoration:line-through;color:gray}
form.inline{display:inline}
</style></head>
<body>
<h2>Task Manager</h2>
{% if session.username %}<p>Hi, {{ session.username }} | <a href='{{
url_for('logout') }}'>Logout</a></p>{% endif %}
{% for m in get_flashed_messages() %}<div class='flash'>{{ m }}</div>{% endfor %}
{% block content %}{% endblock %}
</body></html>'''

REGISTER = '''{% extends 'base.html' %}
{% block content %}
<h3>Register</h3>
<form method='post'>
<input name='username' placeholder='Username' required><br>
<input name='password' type='password' placeholder='Password' required><br>
<button>Register</button></form>
<p>Have an account? <a href='{{ url_for('login') }}'>Login</a></p>
{% endblock %}'''

LOGIN = '''{% extends 'base.html' %}
{% block content %}
<h3>Login</h3>
<form method='post'>
<input name='username' placeholder='Username' required><br>
<input name='password' type='password' placeholder='Password' required><br>
<button>Login</button></form>
<p>New user? <a href='{{ url_for('register') }}'>Register</a></p>
{% endblock %}'''

TASKS = '''{% extends 'base.html' %}
{% block content %}
<form method='post'><input name='title' placeholder='New task' required>
<button>Add</button></form>
<ul>
{% for t in tasks %}
<li><span class='{{ 'done' if t.done else '' }}'>{{ t.title }}</span>
<form class='inline' method='post' action='{{ url_for('toggle', task_id=t.id)
}}'><button>{{ 'Undo' if t.done else 'Done' }}</button></form>
<form class='inline' method='post' action='{{ url_for('delete', task_id=t.id)
}}'><button>Delete</button></form></li>
{% else %}<li>No tasks yet.</li>
{% endfor %}
</ul>
{% endblock %}'''

app.jinja_loader = DictLoader({'base.html': BASE, 'register.html': REGISTER,
                               'login.html': LOGIN, 'tasks.html': TASKS})


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db:
        db.close()


def init_db():
    db = sqlite3.connect(DB)
    db.executescript('''
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        done INTEGER DEFAULT 0);
    ''')
    db.commit()
    db.close()


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


@app.route('/')
def home():
    return redirect(url_for('tasks'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if len(username) < 3:
            flash('Username must be at least 3 characters.')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.')
        else:
            try:
                db = get_db()
                db.execute('INSERT INTO users(username, password) VALUES(?, ?)',
                           (username, generate_password_hash(password)))
                db.commit()
                flash('Registered! Please log in.')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('That username is already taken.')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = get_db().execute('SELECT * FROM users WHERE username = ?',
                                (username,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('tasks'))
        flash('Wrong username or password.')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/tasks', methods=['GET', 'POST'])
@login_required
def tasks():
    db = get_db()
    if request.method == 'POST':
        title = request.form['title'].strip()
        if title:
            db.execute('INSERT INTO tasks(user_id, title) VALUES(?, ?)',
                       (session['user_id'], title))
            db.commit()
        else:
            flash('Task cannot be empty.')
        return redirect(url_for('tasks'))
    rows = db.execute('SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC',
                      (session['user_id'],)).fetchall()
    return render_template('tasks.html', tasks=rows)


@app.route('/toggle/<int:task_id>', methods=['POST'])
@login_required
def toggle(task_id):
    db = get_db()
    db.execute('UPDATE tasks SET done = 1 - done WHERE id = ? AND user_id = ?',
               (task_id, session['user_id']))
    db.commit()
    return redirect(url_for('tasks'))


@app.route('/delete/<int:task_id>', methods=['POST'])
@login_required
def delete(task_id):
    db = get_db()
    db.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?',
               (task_id, session['user_id']))
    db.commit()
    return redirect(url_for('tasks'))


init_db()

if __name__ == '__main__':
    app.run(debug=True)


from flask import Flask, render_template, send_from_directory, request, redirect, url_for, session
from pathlib import Path
import os
import sqlite3

app = Flask(__name__)
BASE_DIR = Path(__file__).parent
PLOTS_DIR = BASE_DIR / "plots"
USER_DB = BASE_DIR / "user.db"
app.secret_key = 'your_secret_key'  # Change for production

# --- User helpers ---
def init_user_db():
    conn = sqlite3.connect(USER_DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def add_user(username, password):
    try:
        conn = sqlite3.connect(USER_DB)
        c = conn.cursor()
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def check_user(username, password):
    conn = sqlite3.connect(USER_DB)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
    user = c.fetchone()
    conn.close()
    return user is not None

def get_available_stocks():
    # Dynamically list all *_analysis_summary.txt files as stocks
    stock_files = list(BASE_DIR.glob("*_analysis_summary.txt"))
    stocks = []
    for f in stock_files:
        stock_name = f.stem.replace('_analysis_summary', '')
        # Clean up stock name for display (e.g., 'amazon_clean' -> 'Amazon')
        display_name = stock_name.replace('_clean', '').capitalize()
        stocks.append({'name': display_name, 'key': stock_name})
    # Add pairwise comparison option if 2 or more stocks
    if len(stocks) >= 2:
        stocks.append({'name': 'Comparison', 'key': 'all'})
    return stocks

# Helper to get summary and plot filenames
def get_summary_and_plots(stock=None):
    if not stock or stock == '':
        return '', []
    summary_path = BASE_DIR / f"{stock}_analysis_summary.txt"
    plots_dir = BASE_DIR / "plots"
    all_plots = [f for f in os.listdir(plots_dir) if f.endswith('.png')]
    plots = [p for p in all_plots if p.startswith(stock)]
    summary = summary_path.read_text() if summary_path.exists() else ''
    return summary, plots

@app.route('/')
def landing():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            error = "Please provide both username and password."
        elif add_user(username, password):
            return redirect(url_for('login'))
        else:
            error = "Username already exists."
    return render_template('signup.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if check_user(username, password):
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials.'
    return render_template('login.html', error=error)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    available_stocks = get_available_stocks()
    if request.method == 'GET':
        return render_template('dashboard.html', available_stocks=available_stocks, selected_stock=None)
    selected_stock = request.form.get('stock')
    if not selected_stock:
        return render_template('dashboard.html', available_stocks=available_stocks, selected_stock=None)
    if selected_stock == 'all':
        # For comparison, show a generic comparison plot and stats
        comparison_stats_path = BASE_DIR / "comparison_stats.txt"
        comparison_stats = comparison_stats_path.read_text() if comparison_stats_path.exists() else ''
        return render_template('dashboard.html', available_stocks=available_stocks, selected_stock='all', comparison_stats=comparison_stats)
    summary, plots = get_summary_and_plots(selected_stock)
    return render_template('dashboard.html', available_stocks=available_stocks, selected_stock=selected_stock, summary=summary, plots=plots)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('landing'))

@app.route("/plots/<path:filename>")
def plot_file(filename):
    return send_from_directory(PLOTS_DIR, filename)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Flask app")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5001, help="Port to bind (default: 5001)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    init_user_db()  # Initialize user DB on startup

    app.run(debug=args.debug, host=args.host, port=args.port)

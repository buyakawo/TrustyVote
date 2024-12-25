import datetime
from blockchain import Blockchain  # Assuming you meant Blockchain instead of Ledger
import hashlib
import json
from flask import Flask, jsonify, request, redirect, url_for, render_template, flash, session
import requests
from uuid import uuid4
from urllib.parse import urlparse
from flask_sqlalchemy import SQLAlchemy
import sys
from werkzeug.security import generate_password_hash, check_password_hash  # For secure password handling

# Initialize the Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "super_secret_key"  # Consider loading this from environment variables for better security

node_identifier = str(uuid4()).replace('-', '')  # Unique identifier for the node
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

# Initialize the Blockchain ledger (assuming Blockchain is the class you're using)
ledger = Blockchain()

# Initialize a variable for clearing data
reset_flag = 0

# Function to mine a block in the blockchain
def generate_block():
    previous_block = ledger.get_last_block()
    previous_proof = previous_block['proof']
    proof = ledger.calculate_proof_of_work(previous_proof)
    previous_hash = ledger.compute_hash(previous_block)
    ledger.add_vote(voter_id=-1, candidate_id=-1)  # Assuming this adds a placeholder vote
    block = ledger.create_new_block(proof, previous_hash)
    response = {
        'message': 'Block successfully mined!',
        'index': block['index'],
        'timestamp': block['timestamp'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
        'votes': block['votes']
    }
    return jsonify(response), 200

# Function to validate the blockchain
def validate_chain():
    is_chain_valid = ledger.validate_ledger()
    return 1 if is_chain_valid else 0

# Database model for storing user information
class Account(db.Model):
    """ Define the database schema for user accounts """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(80))  # Will store hashed passwords
    role = db.Column(db.Integer)  # 0 for regular user, 1 for admin

    def __init__(self, username, password, role=0):
        self.username = username
        self.password = generate_password_hash(password)  # Store hashed password
        self.role = role

# Home route
@app.route('/', methods=['GET', 'POST'])
def main_page():
    if request.method == 'GET':
        if 'logged_in' not in session:
            return redirect(url_for('login_page'))
        else:
            return render_template('home.html', user=request.args.get('user'))
    else:
        voter_id = int(request.form['userId'])
        candidate_id = int(request.form['optradio'])
        if not voter_id or not candidate_id:
            return render_template('result.html', success_flag=0, user=voter_id)

        previous_block = ledger.get_last_block()
        proof = ledger.calculate_proof_of_work(previous_block.get("proof", "")) if previous_block else 1

        index = ledger.create_new_block(proof, ledger.compute_hash(previous_block), voter_id, candidate_id)
        if index is None:
            return render_template('result.html', success_flag=0, user=voter_id)
        else:
            if len(ledger.votes) == 10:
                generate_block()
            return render_template('result.html', success_flag=1, candidate=candidate_id, user=voter_id), 200

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    """ Render the login page and handle login logic """
    if request.method == 'GET':
        return render_template('login.html')
    else:
        username = request.form['username']
        password = request.form['password']
        user = Account.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):  # Secure password check
            session['logged_in'] = True
            if user.role == 0:  # Regular user
                return redirect(url_for('main_page', user=user.id))
            else:  # Admin user
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            return render_template('login.html')

# Logout route
@app.route('/logout')
def logout_page():
    """ Handle user logout """
    session.pop('logged_in', None)
    return redirect(url_for('main_page'))

# Admin dashboard route
@app.route('/admin', methods=['GET'])
def admin_dashboard():
    chain_valid = validate_chain()
    results = ledger.calculate_results()  # Ensure calculate_results() is implemented in the Blockchain class
    return render_template('admin_dashboard.html', data=results, validity_flag=chain_valid)

# Route to get the blockchain
@app.route('/get_ledger', methods=['GET'])
def fetch_ledger():
    response = {
        'chain': ledger.get_full_ledger(),
        'length': len(ledger.get_full_ledger())
    }
    return jsonify(response), 200

# Route to connect new nodes
@app.route('/connect_node', methods=['POST'])
def add_new_node():
    json_data = request.get_json()
    nodes = json_data.get('nodes')
    if nodes is None:
        return "No nodes provided", 400
    for node in nodes:
        ledger.register_node(node)
    response = {
        'message': 'Nodes successfully connected.',
        'total_nodes': list(ledger.nodes)
    }
    return jsonify(response), 201

# Route to replace the chain with the longest chain if necessary
@app.route('/replace_chain', methods=['GET'])
def sync_chain():
    chain_replaced = ledger.sync_with_longest_chain()
    if chain_replaced:
        response = {
            'message': 'The chain was replaced with the longest one.',
            'new_chain': ledger.chain
        }
    else:
        response = {
            'message': 'Current chain is already the longest.',
            'chain': ledger.chain
        }
    return jsonify(response), 200

if __name__ == '__main__':
    app.debug = True
    db.create_all()  # Create the tables
    app.run(host='127.0.0.1', port=5000)



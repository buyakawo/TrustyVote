import datetime
from blockchain import Ledger
import hashlib
import json
from flask import Flask, jsonify, request, redirect, url_for, render_template, flash, session
import requests
from uuid import uuid4
from urllib.parse import urlparse
from flask_sqlalchemy import SQLAlchemy
import sys

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = "super_secret_key"
node_identifier = str(uuid4()).replace('-', '')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

# Initialize the Blockchain ledger
ledger = Ledger()

# Initialize a variable for clearing data
reset_flag = 0

# Function to mine a block in the blockchain
def generate_block():
    previous_block = ledger.get_last_block()
    previous_proof = previous_block['proof']
    proof = ledger.calculate_proof_of_work(previous_proof)
    previous_hash = ledger.compute_hash(previous_block)
    ledger.add_vote(voter_id=-1, candidate_id=-1)
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
    password = db.Column(db.String(80))
    role = db.Column(db.Integer)

    def __init__(self, username, password):
        self.username = username
        self.password = password

# Home route
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
        if previous_block:
            proof = ledger.calculate_proof_of_work(previous_block.get("proof", ""))    
        else:
            proof = 1    
        
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
        user = Account.query.filter_by(username=username, password=password).first()
        if user:
            if user.role == 0:  # Regular user
                session['logged_in'] = True
                return redirect(url_for('main_page', user=user.id))
            else:  # Admin user
                session['logged_in'] = True
                return redirect(url_for('admin_dashboard'))
        else:
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
    results = ledger.calculate_results()
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
    db.create_all()
    app.secret_key = "another_secret_key"
    app.run(host='127.0.0.1', port=5000)

import datetime
import hashlib
import json
from urllib.parse import urlparse
import requests


class Blockchain:
    def __init__(self):
        self.blockchain_ledger = []  # List to store blockchain blocks
        self.voter_ids = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17)
        self.voters_casted = []  # List of voters who have already cast their votes
        self.candidate_ids = (100, 101, 102, 103)  # Candidate IDs
        self.vote_counts = {candidate: 0 for candidate in self.candidate_ids}  # Vote tally
        self.transactions = []  # Store transactions temporarily
        self.nodes = set()  # Store the nodes in the network

    def add_new_block(self, proof, previous_hash, voter, candidate):
        # Check if voter and candidate IDs are valid
        if voter in self.voter_ids and candidate in self.candidate_ids:
            # Check if the voter has already voted
            if voter not in self.voters_casted:
                # Create a new block with voter and candidate information
                block = {
                    'index': len(self.blockchain_ledger) + 1,
                    'timestamp': str(datetime.datetime.now()),
                    'proof': proof if len(self.blockchain_ledger) > 0 else 1,
                    'previous_hash': previous_hash if len(self.blockchain_ledger) > 0 else 0,
                    'voter': voter,
                    'candidate': candidate
                }
                # Append the block to the blockchain
                self.blockchain_ledger.append(block)
                # Mark voter as having voted
                self.voters_casted.append(voter)
                # Increment the candidate's vote count
                self.vote_counts[candidate] += 1
                return block
            else:
                return None  # Voter has already cast a vote
        else:
            return None  # Invalid voter or candidate

    def fetch_last_block(self):
        if len(self.blockchain_ledger) > 0:
            return self.blockchain_ledger[-1]
        return None  # Return None if there are no blocks

    def get_full_chain(self):
        return self.blockchain_ledger

    def calculate_proof_of_work(self, previous_proof):
        new_proof = 1
        check_proof = False
        while not check_proof:
            # Hashing the new proof and previous proof
            hash_operation = hashlib.sha256(str(new_proof**2 - previous_proof**2).encode()).hexdigest()
            # Looking for a hash that starts with four leading zeroes
            if hash_operation[:4] == '0000':
                check_proof = True
            else:
                new_proof += 1
        return new_proof

    def compute_block_hash(self, block):
        # Convert the block into a JSON string and hash it
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def validate_blockchain(self):
        previous_block = self.blockchain_ledger[0]
        block_index = 1
        while block_index < len(self.blockchain_ledger):
            current_block = self.blockchain_ledger[block_index]
            # Validate if the hash of the previous block is correct
            if current_block['previous_hash'] != self.compute_block_hash(previous_block):
                return False
            # Check if the proof of work is correct
            previous_proof = previous_block['proof']
            current_proof = current_block['proof']
            hash_operation = hashlib.sha256(str(current_proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] != '0000':
                return False
            previous_block = current_block
            block_index += 1
        return True

    def record_transaction(self, voter, candidate):
        # Add a new transaction to the list
        if voter in self.voter_ids and candidate in self.candidate_ids:
            if voter not in self.voters_casted:
                self.transactions.append({'voter': voter, 'candidate': candidate})
                self.voters_casted.append(voter)
                self.vote_counts[candidate] += 1
                previous_block = self.fetch_last_block()
                return previous_block['index'] + 1 if previous_block else None
            else:
                return None  # Voter has already cast their vote
        else:
            return None  # Invalid voter or candidate

    def register_node(self, address):
        # Add a new node to the set of nodes
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def sync_blockchain(self):
        # Synchronize blockchain with the network
        network = self.nodes
        longest_chain = None
        max_length = len(self.blockchain_ledger)

        for node in network:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > max_length and self.validate_blockchain():
                    max_length = length
                    longest_chain = chain

        if longest_chain:
            self.blockchain_ledger = longest_chain
            return True

        return False

    def get_election_results(self):
        # Return the current vote counts for each candidate
        return self.vote_counts

    def check_blockchain_status(self):
        # Check the status of the blockchain
        if len(self.blockchain_ledger) == 0:
            return "Blockchain is empty"
        elif len(self.blockchain_ledger) == 1:
            return "Blockchain contains only the genesis block"
        else:
            return "Blockchain has multiple blocks"

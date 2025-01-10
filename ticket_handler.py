import json
from datetime import datetime

class TicketSystem:
    def __init__(self, db_file='tickets.json'):
        self.db_file = db_file
        self._load_db()

    def _load_db(self):
        try:
            with open(self.db_file, 'r') as f:
                self.db = json.load(f)
        except FileNotFoundError:
            self.db = {
                'tickets': [],
                'last_ticket_id': 0
            }
            self._save_db()

    def _save_db(self):
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, indent=2)

    def create_ticket(self, user_id, subject, message):
        self.db['last_ticket_id'] += 1
        ticket = {
            'ticket_id': self.db['last_ticket_id'],
            'user_id': user_id,
            'subject': subject,
            'status': 'open',
            'messages': [{
                'user_id': user_id,
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'is_admin': False
            }],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        self.db['tickets'].append(ticket)
        self._save_db()
        return ticket

    def add_message(self, ticket_id, user_id, message, is_admin=False):
        for ticket in self.db['tickets']:
            if ticket['ticket_id'] == ticket_id:
                ticket['messages'].append({
                    'user_id': user_id,
                    'message': message,
                    'timestamp': datetime.now().isoformat(),
                    'is_admin': is_admin
                })
                ticket['updated_at'] = datetime.now().isoformat()
                self._save_db()
                return ticket
        return None

    def close_ticket(self, ticket_id):
        for ticket in self.db['tickets']:
            if ticket['ticket_id'] == ticket_id:
                ticket['status'] = 'closed'
                ticket['updated_at'] = datetime.now().isoformat()
                self._save_db()
                return ticket
        return None

    def reopen_ticket(self, ticket_id):
        for ticket in self.db['tickets']:
            if ticket['ticket_id'] == ticket_id:
                ticket['status'] = 'open'
                ticket['updated_at'] = datetime.now().isoformat()
                self._save_db()
                return ticket
        return None

    def get_user_tickets(self, user_id):
        return [ticket for ticket in self.db['tickets'] if ticket['user_id'] == user_id]

    def get_ticket(self, ticket_id):
        for ticket in self.db['tickets']:
            if ticket['ticket_id'] == ticket_id:
                return ticket
        return None

    def get_open_tickets(self):
        return [ticket for ticket in self.db['tickets'] if ticket['status'] == 'open']

    def get_closed_tickets(self):
        return [ticket for ticket in self.db['tickets'] if ticket['status'] == 'closed']

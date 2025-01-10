import json
from datetime import datetime

class AdminPanel:
    def __init__(self, db_file='admin.json'):
        self.db_file = db_file
        self._load_db()

    def _load_db(self):
        try:
            with open(self.db_file, 'r') as f:
                self.db = json.load(f)
        except FileNotFoundError:
            self.db = {
                'admins': [],
                'plans': {},
                'settings': {
                    'allow_registration': True,
                    'maintenance_mode': False,
                    'backup_enabled': True,
                    'backup_frequency': 'daily'
                }
            }
            self._save_db()

    def _save_db(self):
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, indent=2)

    def is_admin(self, user_id):
        return str(user_id) in self.db['admins']

    def add_admin(self, user_id):
        if str(user_id) not in self.db['admins']:
            self.db['admins'].append(str(user_id))
            self._save_db()
            return True
        return False

    def remove_admin(self, user_id):
        if str(user_id) in self.db['admins']:
            self.db['admins'].remove(str(user_id))
            self._save_db()
            return True
        return False

    def update_plan(self, plan_id, details):
        self.db['plans'][plan_id] = details
        self._save_db()

    def remove_plan(self, plan_id):
        if plan_id in self.db['plans']:
            del self.db['plans'][plan_id]
            self._save_db()
            return True
        return False

    def get_plans(self):
        return self.db['plans']

    def update_settings(self, settings):
        self.db['settings'].update(settings)
        self._save_db()

    def get_settings(self):
        return self.db['settings']

class UserManager:
    def __init__(self, db_file='users.json'):
        self.db_file = db_file
        self._load_db()

    def _load_db(self):
        try:
            with open(self.db_file, 'r') as f:
                self.db = json.load(f)
        except FileNotFoundError:
            self.db = {'users': {}}
            self._save_db()

    def _save_db(self):
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, indent=2)

    def register_user(self, user_id, username, first_name, last_name=None):
        user_data = {
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'registered_at': datetime.now().isoformat(),
            'hosting_accounts': [],
            'active': True
        }
        self.db['users'][str(user_id)] = user_data
        self._save_db()
        return user_data

    def get_user(self, user_id):
        return self.db['users'].get(str(user_id))

    def update_user(self, user_id, data):
        if str(user_id) in self.db['users']:
            self.db['users'][str(user_id)].update(data)
            self._save_db()
            return self.db['users'][str(user_id)]
        return None

    def add_hosting_account(self, user_id, account_data):
        if str(user_id) in self.db['users']:
            self.db['users'][str(user_id)]['hosting_accounts'].append(account_data)
            self._save_db()
            return True
        return False

    def get_all_users(self):
        return self.db['users']

    def get_active_users(self):
        return {k: v for k, v in self.db['users'].items() if v.get('active', True)}

    def deactivate_user(self, user_id):
        if str(user_id) in self.db['users']:
            self.db['users'][str(user_id)]['active'] = False
            self._save_db()
            return True
        return False

    def activate_user(self, user_id):
        if str(user_id) in self.db['users']:
            self.db['users'][str(user_id)]['active'] = True
            self._save_db()
            return True
        return False

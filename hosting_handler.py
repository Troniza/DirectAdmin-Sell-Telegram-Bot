import os
import json
from datetime import datetime
import requests
from directadmin_handler import DirectAdminHandler

class HostingManager:
    def __init__(self, da_handler, db_file='hosting.json'):
        self.da_handler = da_handler
        self.db_file = db_file
        self._load_db()

    def _load_db(self):
        try:
            with open(self.db_file, 'r') as f:
                self.db = json.load(f)
        except FileNotFoundError:
            self.db = {
                'accounts': [],
                'backups': [],
                'databases': []
            }
            self._save_db()

    def _save_db(self):
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, indent=2)

    def create_hosting_account(self, user_id, package, domain, email):
        try:
            username = self._generate_username(domain)
            password = self._generate_password()
            
            # Create account in DirectAdmin
            result = self.da_handler.create_user(
                username=username,
                password=password,
                email=email,
                package=package,
                domain=domain
            )
            
            # Store account info
            account_data = {
                'user_id': user_id,
                'username': username,
                'domain': domain,
                'email': email,
                'package': package,
                'created_at': datetime.now().isoformat(),
                'status': 'active',
                'expiry_date': self._calculate_expiry_date()
            }
            self.db['accounts'].append(account_data)
            self._save_db()
            
            return {
                'status': 'success',
                'username': username,
                'password': password,
                'account_data': account_data
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def add_domain(self, username, domain):
        try:
            result = self.da_handler._make_request(
                'CMD_API_DOMAIN',
                data={
                    'action': 'create',
                    'domain': domain,
                    'username': username,
                    'php': 'ON',
                    'cgi': 'ON'
                }
            )
            return {'status': 'success', 'message': 'Domain added successfully'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def create_database(self, username, db_name, db_user, db_pass):
        try:
            # Create database
            result = self.da_handler._make_request(
                'CMD_API_DATABASES',
                data={
                    'action': 'create',
                    'name': db_name,
                    'user': db_user,
                    'passwd': db_pass,
                    'passwd2': db_pass
                }
            )
            
            # Store database info
            db_data = {
                'username': username,
                'db_name': db_name,
                'db_user': db_user,
                'created_at': datetime.now().isoformat()
            }
            self.db['databases'].append(db_data)
            self._save_db()
            
            return {'status': 'success', 'database': db_data}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def create_backup(self, username):
        try:
            # Request backup through DirectAdmin
            result = self.da_handler._make_request(
                'CMD_API_USER_BACKUP',
                data={
                    'action': 'backup',
                    'user': username,
                    'type': 'full'
                }
            )
            
            # Store backup info
            backup_data = {
                'username': username,
                'created_at': datetime.now().isoformat(),
                'type': 'full',
                'status': 'completed'
            }
            self.db['backups'].append(backup_data)
            self._save_db()
            
            return {'status': 'success', 'backup': backup_data}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_resource_usage(self, username):
        try:
            result = self.da_handler._make_request(
                f'CMD_API_SHOW_USER_USAGE?user={username}',
                method='GET'
            )
            return {'status': 'success', 'usage': result}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def suspend_account(self, username):
        try:
            result = self.da_handler.suspend_user(username)
            self._update_account_status(username, 'suspended')
            return {'status': 'success', 'message': 'Account suspended'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def unsuspend_account(self, username):
        try:
            result = self.da_handler.unsuspend_user(username)
            self._update_account_status(username, 'active')
            return {'status': 'success', 'message': 'Account unsuspended'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def delete_account(self, username):
        try:
            result = self.da_handler.delete_user(username)
            self._update_account_status(username, 'deleted')
            return {'status': 'success', 'message': 'Account deleted'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_account_info(self, username):
        try:
            result = self.da_handler.get_user_info(username)
            return {'status': 'success', 'info': result}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _update_account_status(self, username, status):
        for account in self.db['accounts']:
            if account['username'] == username:
                account['status'] = status
                account['updated_at'] = datetime.now().isoformat()
                self._save_db()
                break

    def get_user_accounts(self, user_id):
        return [acc for acc in self.db['accounts'] if acc['user_id'] == user_id]

    def get_account_backups(self, username):
        return [backup for backup in self.db['backups'] if backup['username'] == username]

    def get_account_databases(self, username):
        return [db for db in self.db['databases'] if db['username'] == username]

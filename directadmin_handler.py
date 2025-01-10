import os
import requests
from urllib.parse import urlencode

class DirectAdminHandler:
    def __init__(self, url, username, password):
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()

    def _make_request(self, command, method='POST', data=None):
        """Make a request to DirectAdmin API"""
        url = f"{self.url}/{command}"
        try:
            response = self.session.request(
                method,
                url,
                auth=(self.username, self.password),
                data=data,
                verify=False  # Note: In production, should be set to True
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            raise Exception(f"DirectAdmin API Error: {str(e)}")

    def create_reseller_package(self, name, quota, bandwidth, domains=1):
        """Create a new hosting package"""
        data = {
            'action': 'create',
            'add': 'Submit',
            'name': name,
            'quota': quota,  # in MB
            'bandwidth': bandwidth,  # in MB
            'domainlimit': domains,
            'ips': 0,  # Shared IP
            'cgi': 'ON',
            'php': 'ON',
            'spam': 'ON',
            'ssl': 'ON',
            'ssh': 'OFF',
        }
        return self._make_request('CMD_API_PACKAGES', data=data)

    def create_user(self, username, password, email, package, domain):
        """Create a new hosting account"""
        data = {
            'action': 'create',
            'add': 'Submit',
            'username': username,
            'passwd': password,
            'passwd2': password,
            'email': email,
            'domain': domain,
            'package': package,
            'ip': 'shared',
            'notify': 'yes'
        }
        return self._make_request('CMD_API_ACCOUNT_USER', data=data)

    def suspend_user(self, username):
        """Suspend a user account"""
        data = {
            'action': 'suspend',
            'select0': username
        }
        return self._make_request('CMD_API_SELECT_USERS', data=data)

    def unsuspend_user(self, username):
        """Unsuspend a user account"""
        data = {
            'action': 'unsuspend',
            'select0': username
        }
        return self._make_request('CMD_API_SELECT_USERS', data=data)

    def delete_user(self, username):
        """Delete a user account"""
        data = {
            'confirmed': 'Confirm',
            'delete': 'yes',
            'select0': username
        }
        return self._make_request('CMD_API_SELECT_USERS', data=data)

    def get_user_info(self, username):
        """Get information about a user account"""
        return self._make_request(f'CMD_API_SHOW_USER_CONFIG?user={username}', method='GET')

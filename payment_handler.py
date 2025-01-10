import json
import requests
from datetime import datetime

class ZarinpalPayment:
    def __init__(self, merchant_id, sandbox=False):
        self.merchant_id = merchant_id
        self.sandbox = sandbox
        self.payment_url = 'https://sandbox.zarinpal.com/pg/StartPay/' if sandbox else 'https://zarinpal.com/pg/StartPay/'
        self.api_url = 'https://sandbox.zarinpal.com/pg/rest/WebGate/' if sandbox else 'https://api.zarinpal.com/pg/v4/payment/'

    def request_payment(self, amount, description, callback_url, email=None, mobile=None):
        data = {
            'merchant_id': self.merchant_id,
            'amount': amount,
            'description': description,
            'callback_url': callback_url,
            'metadata': {
                'email': email,
                'mobile': mobile
            }
        }
        
        try:
            response = requests.post(f"{self.api_url}request", json=data)
            if response.status_code == 200:
                result = response.json()['data']
                if result['code'] == 100:
                    return {
                        'status': 'success',
                        'authority': result['authority'],
                        'payment_url': f"{self.payment_url}{result['authority']}"
                    }
            return {
                'status': 'error',
                'message': 'Payment request failed'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def verify_payment(self, authority, amount):
        data = {
            'merchant_id': self.merchant_id,
            'authority': authority,
            'amount': amount
        }
        
        try:
            response = requests.post(f"{self.api_url}verify", json=data)
            if response.status_code == 200:
                result = response.json()['data']
                if result['code'] == 100:
                    return {
                        'status': 'success',
                        'ref_id': result['ref_id']
                    }
            return {
                'status': 'error',
                'message': 'Payment verification failed'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

class PaymentDatabase:
    def __init__(self, db_file='payments.json'):
        self.db_file = db_file
        self._load_db()

    def _load_db(self):
        try:
            with open(self.db_file, 'r') as f:
                self.db = json.load(f)
        except FileNotFoundError:
            self.db = {'payments': []}
            self._save_db()

    def _save_db(self):
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, indent=2)

    def create_payment(self, user_id, amount, description, authority):
        payment = {
            'user_id': user_id,
            'amount': amount,
            'description': description,
            'authority': authority,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        self.db['payments'].append(payment)
        self._save_db()
        return payment

    def update_payment(self, authority, status, ref_id=None):
        for payment in self.db['payments']:
            if payment['authority'] == authority:
                payment['status'] = status
                payment['ref_id'] = ref_id
                payment['updated_at'] = datetime.now().isoformat()
                self._save_db()
                return payment
        return None

    def get_payment(self, authority):
        for payment in self.db['payments']:
            if payment['authority'] == authority:
                return payment
        return None

import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.hmac import HMAC
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class OpayPayment:
    """Handle Opay payment processing"""

    def __init__(self):
        self.api_key = current_app.config.get('OPAY_API_KEY')
        self.secret_key = current_app.config.get('OPAY_SECRET_KEY')
        self.base_url = 'https://merchant.opaycheckout.com/api/v1'

    def initiate_payment(self, payment_data):
        """Initiate a payment with Opay"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            response = requests.post(
                f'{self.base_url}/checkout/initiate',
                json=payment_data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Payment initiation error: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': str(e)}

    def verify_webhook(self, webhook_data):
        """Verify Opay webhook signature"""
        try:
            received_signature = webhook_data.get('signature')
            if not received_signature:
                return False

            # Generate HMAC signature
            hmac = HMAC(self.secret_key.encode('utf-8'), hashes.SHA256())
            hmac.update(str(webhook_data.get('transaction_id')).encode('utf-8'))
            expected_signature = hmac.finalize().hex()

            return received_signature == expected_signature
        except Exception as e:
            logger.error(f"Webhook verification error: {str(e)}", exc_info=True)
            return False
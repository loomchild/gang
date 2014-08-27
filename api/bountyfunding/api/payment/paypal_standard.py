import requests

import urllib

from bountyfunding.api.config import config
from bountyfunding.api.models import db, Payment
from bountyfunding.api.const import PaymentGateway
from bountyfunding.api.errors import APIException
from bountyfunding.api.payment.util import retrieve_admin, get_paypal_url


class PayPalStandardGateway:

	def create_payment(self, project_id, sponsorship, return_url):
		"""
		Returns authorization URL
		"""
		if not return_url:
			raise APIException('return_url cannot be blank', 400)

		admin = retrieve_admin(project_id)

		args = {
			"cmd": "_donations",
			"business": admin.paypal_email,
			"item_name": "Bounty",
			"amount": sponsorship.amount,
			"currency_code": "EUR",
			"no_note": 1,
			"no_shipping": 1,
			"return": return_url,
			"cancel_return": return_url
		}
		redirect_url = get_paypal_url(project_id) + "?" + urllib.urlencode(args)

		payment = Payment(sponsorship.project_id, sponsorship.sponsorship_id, PaymentGateway.PAYPAL_STANDARD, admin.user_id)
		payment.url = redirect_url
		return payment

	def process_payment(self, project_id, sponsorship, payment, details):
		"""
		Validates payment
		"""
		transaction_id = details["tx"]

		payload = {
			"cmd": "_notify-synch",
			"at": config[project_id].PAYPAL_PDT_ACCESS_TOKEN,
			"tx": transaction_id
		}

		# Check for reused transaction ID
		if db.session.query(db.exists().where(Payment.gateway_id==transaction_id)).scalar():
			return False

		r = requests.post(get_paypal_url(project_id), data=payload)
		
		lines = r.text.strip().splitlines()
		
		if len(lines) == 0:
			return False

		# Check for SUCCESS word
		if not lines.pop(0).strip() == "SUCCESS":
			return False

		# Payment validation
		retrieved_payment = {}			
		for line in lines:
			key, value = line.strip().split('=')
			retrieved_payment[key] = urllib.unquote_plus(value)

		admin = retrieve_admin(project_id)
		# Check recipient email
		if retrieved_payment['business'] != admin.paypal_email:
			return False

		# Check currency
		if retrieved_payment['mc_currency'] != "EUR":
			return False

		# Check amount
		if float(retrieved_payment['mc_gross']) != sponsorship.amount:
			return False

		# Store transaction ID
		payment.gateway_id = transaction_id

		return True

from __future__ import unicode_literals

import braintree
import braintree.exceptions.not_found_error

from django import forms
from ..forms import PaymentForm


class BraintreePaymentForm(PaymentForm):
    nonce = forms.CharField()
    token = forms.CharField()

    transaction_id = None

    def clean_nonce(self):
        nonce = self.cleaned_data['nonce']
        result = braintree.PaymentMethod.create({
            "customer_id": self.customer_id,
            "payment_method_nonce": nonce,
            "options": {
                "verify_card": True,
            }
        })
        if not result.is_success:
            raise forms.ValidationError(result.message)
        self.cleaned_data['payment_method'] = result.payment_method
        return nonce

    def clean_token(self):
        token = self.cleaned_data['token']
        try:
            self.cleaned_data['payment_method'] = braintree.PaymentMethod.find(
                token)
        except braintree.exceptions.not_found_error.NotFoundError, e:
            raise forms.ValidationError(unicode(e))
        return token

    def clean(self):
        data = self.cleaned_data

        if not self.errors and not self.payment.transaction_id:
            result = braintree.Transaction.sale({
                'amount': str(self.payment.total),
                'payment_method_token':
                self.cleaned_data['payment_method'].token,
                'billing': self.get_billing_data(),
                'options': {
                    'submit_for_settlement': True
                },
                'order_id': self.payment.description
            })

            if result.is_success:
                self.transaction_id = result.transaction.id
            else:
                self._errors['__all__'] = self.error_class([result.message])
                self.payment.change_status('error')

        return data

    def get_billing_data(self):
        return {
            'first_name': self.payment.billing_first_name,
            'last_name': self.payment.billing_last_name,
            'country_code_alpha2': self.payment.billing_country_code}

    def save(self):
        braintree.Transaction.submit_for_settlement(self.transaction_id)
        self.payment.transaction_id = self.transaction_id
        self.payment.change_status('confirmed')

from __future__ import unicode_literals

import braintree
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import redirect

from .forms import BraintreePaymentForm
from .. import BasicProvider, RedirectNeeded


class BraintreeProvider(BasicProvider):
    def __init__(self, *args, **kwargs):
        self.merchant_id = kwargs.pop('merchant_id')
        self.public_key = kwargs.pop('public_key')
        self.private_key = kwargs.pop('private_key')
        self.environment = kwargs.pop('environment')

        braintree.Configuration.configure(self.environment,
                                          merchant_id=self.merchant_id,
                                          public_key=self.public_key,
                                          private_key=self.private_key)

        super(BraintreeProvider, self).__init__(*args, **kwargs)
        if not self._capture:
            raise ImproperlyConfigured(
                'Braintreet does not support pre-authorization.')

    def get_form(self, data=None, **kwargs):
        kwargs.update({
            'data': data,
            'payment': self.payment,
            'provider': self,
            'action': '',
            'hidden_inputs': False
        })
        form = BraintreePaymentForm(**kwargs)
        if form.is_valid():
            form.save()
            raise RedirectNeeded(self.payment.get_success_url())
        else:
            self.payment.change_status('input')
        return form

    def process_data(self, request):
        if self.payment.status == 'confirmed':
            return redirect(self.payment.get_success_url())
        return redirect(self.payment.get_failure_url())

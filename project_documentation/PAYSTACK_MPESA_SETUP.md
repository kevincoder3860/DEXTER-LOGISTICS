# Paystack M-Pesa quote payments

## Configuration

Set `PAYSTACK_SECRET_KEY` in the backend environment. For local development, add it to `backend/.env`; in Render, add the Paystack secret key to the `dextere-backend` service environment. Do not commit the key. Use a Paystack test key until the integration has been tested with the merchant account.

Configure the Paystack webhook URL as:

```text
https://<backend-host>/api/payments/paystack-webhook/
```

The webhook uses the same secret key to validate Paystack's `x-paystack-signature` and marks a quote paid only when a successful KES charge matches its stored quote amount.

## Quote-to-payment flow

1. A customer submits a transport enquiry with an email address and receives its reference number.
2. A dispatcher enters the agreed KES amount and changes the enquiry status to `QUOTE_CONFIRMED` or `APPROVED`.
3. The customer looks up the reference in the public tracking portal. Payment is enabled only for a confirmed quote that is not already paid.
4. The frontend posts the enquiry ID and M-Pesa phone number to `/api/payments/paystack-stk/`. The backend uses the stored amount and email; a supplied amount is only checked against the confirmed quote.
5. Paystack sends an STK Push. The customer enters their M-Pesa PIN, and the verified webhook updates the payment status.

The phone input accepts Kenyan mobile numbers in `07XXXXXXXX`, `01XXXXXXXX`, `2547XXXXXXXX`, `2541XXXXXXXX`, or `+254...` form.

# Real-Money Payment Gateway Setup

This project now integrates **Razorpay Standard Checkout** for real payments. UPI and Online payment choices both create a server-side Razorpay Order and open Razorpay Checkout. Cash remains a manual hospital-counter workflow.

## Payment flow

1. Patient opens an unpaid bill.
2. Patient selects **UPI** or **Online**.
3. Flask creates a Razorpay Order using the bill amount in paise.
4. The browser opens Razorpay Standard Checkout.
5. Patient completes UPI, card, net banking, or another payment method enabled on the Razorpay account.
6. Razorpay returns `razorpay_payment_id`, `razorpay_order_id`, and `razorpay_signature`.
7. Flask verifies the signature using the server-side Key Secret and the Order ID stored in the database.
8. The bill is marked paid only after successful verification.
9. Razorpay webhook events are also verified using the webhook secret and update the transaction idempotently.

## Install

```powershell
pip install -r requirements.txt
```

The project pins the current Razorpay Python client used for this integration (`2.0.1`).

## Configure Test Mode first

Copy `.env.example` to `.env` and fill:

```env
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxx
RAZORPAY_WEBHOOK_SECRET=your-webhook-secret
RAZORPAY_CURRENCY=INR
RAZORPAY_AUTO_CAPTURE=1
```

Never put the Key Secret or Webhook Secret in JavaScript, templates, Git, screenshots, or public repositories.

## Razorpay Dashboard setup

1. Create/login to your Razorpay merchant account.
2. Generate **Test Mode** API keys.
3. Configure UPI and other payment methods required by the hospital account.
4. Create a webhook pointing to:

`https://YOUR-DOMAIN/milestone4/razorpay/webhook`

5. Set a dedicated webhook secret and put the same value in `RAZORPAY_WEBHOOK_SECRET`.
6. Enable payment events such as `payment.captured`, `payment.failed`, and `order.paid` as required.
7. Test the complete flow using Razorpay Test Mode.

## Go live

After testing, complete Razorpay merchant/KYC onboarding and generate **Live Mode** API keys. Replace only the environment variables on the server:

```env
RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxx
RAZORPAY_WEBHOOK_SECRET=your-live-webhook-secret
```

Use HTTPS for the deployed application and webhook URL. Configure automatic payment capture in Razorpay or keep `RAZORPAY_AUTO_CAPTURE=1` so captured payments can settle.

## Important production notes

- The application does **not** store card numbers, CVVs, UPI PINs, or banking credentials.
- Payment signatures are verified server-side with HMAC-SHA256.
- The server uses the Razorpay order ID stored in its own database for verification instead of trusting a browser-supplied order ID.
- Webhook signatures are verified against the raw request body.
- Duplicate webhook deliveries are handled without creating duplicate payment transactions.
- A successful browser callback is verified immediately, while webhooks provide asynchronous confirmation if the browser closes unexpectedly.
- Real money is only processed when the Razorpay account is in Live Mode and the Live keys are configured.

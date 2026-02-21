from flask import Flask, request, jsonify
import stripe, os, time, threading, requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

app = Flask(__name__)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID"))
WEBHOOK_URL = os.getenv("RENDER_URL")
active_sessions = {}

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET"))
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            renter_id = int(session['metadata']['renter_id'])
            minutes = int(session['metadata']['minutes'])
            active_sessions[renter_id] = {"expires": time.time() + minutes*60, "chat_id": renter_id}
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={
                "chat_id": renter_id, "text": f"✅ PhantomLink ELITE session ACTIVE for {minutes} mins!\nCodes incoming LIVE. Enjoy brother."
            })
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={
                "chat_id": ADMIN_ID, "text": f"💰 $5–8 STRIPE PAYMENT HIT – session started for {renter_id}"
            })
        return jsonify(success=True)
    except:
        return jsonify(success=False), 400

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to PhantomLink Elite\n/rent10 for $5 (10min)\n/rent20 for $8 (20min)\nPayPal or Venmo? Say so.")

async def rent10(update: Update, context: ContextTypes.DEFAULT_TYPE):
    renter_id = update.message.chat_id
    checkout = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{'price_data': {'currency': 'usd', 'product_data': {'name': 'PhantomLink 10min Elite'}, 'unit_amount': 500}, 'quantity': 1}],
        mode='payment',
        success_url=WEBHOOK_URL + '/success',
        metadata={'renter_id': str(renter_id), 'minutes': '10'}
    )
    await update.message.reply_text(f"Pay here and session starts INSTANTLY: {checkout.url}\n(Or reply 'PayPal' / 'Venmo' for manual)")

async def rent20(update: Update, context: ContextTypes.DEFAULT_TYPE):
    renter_id = update.message.chat_id
    checkout = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{'price_data': {'currency': 'usd', 'product_data': {'name': 'PhantomLink 20min Elite'}, 'unit_amount': 800}, 'quantity': 1}],
        mode='payment',
        success_url=WEBHOOK_URL + '/success',
        metadata={'renter_id': str(renter_id), 'minutes': '20'}
    )
    await update.message.reply_text(f"Pay here and session starts INSTANTLY: {checkout.url}")

async def manual_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("PayPal: paypal.me/YOURPAYPAL\nVenmo: @YOURVENMO (send $5 or $8 with note 'PhantomLink 10/20')\nScreenshot proof → session starts in <60s")

@app.route('/webhook', methods=['POST'])
def sms_webhook():
    data = request.form
    msg = data.get('message', '')
    if any(k in msg.lower() for k in ['code','otp','verify']):
        for rid, sess in list(active_sessions.items()):
            if sess['expires'] > time.time():
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": rid, "text": f"🔥 PhantomLink Code: {msg}"})
                return jsonify(ok=True)
    return jsonify(ok=True)

def run_bot():
    app_bot = Application.builder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("rent10", rent10))
    app_bot.add_handler(CommandHandler("rent20", rent20))
    app_bot.add_handler(CommandHandler("manual", manual_pay))
    app_bot.run_polling()

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

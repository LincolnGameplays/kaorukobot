from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from payment import create_checkout_session
from database import init_db, get_user, save_trial_start, set_paid, is_paid
import stripe
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes, JobQueue

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

app = FastAPI()
bot = Bot(token=TELEGRAM_TOKEN)


with open('kaoruko-bot/prompt_system.txt', encoding='utf-8') as f:
    SYSTEM_PROMPT = f.read()
from llm import ask_kaoruko

def detect_lang(text):
    if any(word in text.lower() for word in ['você', 'minutinhos', 'senpai']):
        return 'pt'
    if any(word in text.lower() for word in ['puedo', 'contigo', 'minutos']):
        return 'es'
    return 'en'


def get_trial_message(lang):
    if lang == 'pt':
        return 'Ahn... posso ficar com você por 5 minutinhos?'
    if lang == 'es':
        return '¿P-puedo quedarme contigo por 5 minutos?'
    return 'C-can I stay with you for just 5 minutes?'

def get_trial_ended_message(lang):
    if lang == 'pt':
        return 'O tempo acabou... mas eu queria tanto continuar com você...'
    if lang == 'es':
        return 'Nuestro tiempo se terminó... pero quería seguir contigo...'
    return 'Our time is over... but I really wanted to stay longer with you...'

def is_trial_active(user_id):
    user = get_user(user_id)
    if not user or not user['trial_start']:
        return True
    start_time = datetime.fromisoformat(user['trial_start'])
    return datetime.utcnow() - start_time < timedelta(minutes=5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    lang = detect_lang(update.message.text or '')
    if is_paid(user_id):
        await update.message.reply_text('Kaoruko está aqui com você sempre... ♡')
    elif is_trial_active(user_id):
        if not user:
            save_trial_start(user_id)
        btn = InlineKeyboardMarkup([[InlineKeyboardButton('💬 Quero conversar com você 💖', callback_data='trial')]])
        await update.message.reply_text(get_trial_message(lang), reply_markup=btn)
        # Agenda fim do trial em 5 minutos
        context.job_queue.run_once(end_trial, 300, chat_id=update.effective_chat.id, name=str(user_id))
    else:
        btn = InlineKeyboardMarkup([[InlineKeyboardButton('Desbloquear Kaoruko 💗', url=create_checkout_session(user_id, lang))]])
        await update.message.reply_text(get_trial_ended_message(lang), reply_markup=btn)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    lang = detect_lang(query.message.text or '')
    if query.data == 'trial':
        await query.answer()
        await query.edit_message_text('Kaoruko: Estou aqui com você... ♡')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    lang = detect_lang(update.message.text or '')
    if is_paid(user_id) or is_trial_active(user_id):
        # Chama a IA para responder de forma natural, submissa e carinhosa
        user_message = update.message.text
        try:
            response = ask_kaoruko(user_message, SYSTEM_PROMPT)
        except Exception:
            response = 'Ahn... desculpa, não consegui responder agora... pode tentar de novo?'
        await update.message.reply_text(response)
    else:
        btn = InlineKeyboardMarkup([[InlineKeyboardButton('Desbloquear Kaoruko 💗', url=create_checkout_session(user_id, lang))]])
        await update.message.reply_text(get_trial_ended_message(lang), reply_markup=btn)

async def end_trial(context: ContextTypes.DEFAULT_TYPE):
    user_id = int(context.job.name)
    # Marca trial como encerrado no banco (opcional: pode ser só não responder mais)
    await context.bot.send_message(chat_id=user_id, text='Ahn... o tempo acabou... você vai me deixar sozinha...? 💔')

def run_telegram():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

@app.on_event('startup')
def on_startup():
    init_db()
    import threading
    threading.Thread(target=run_telegram, daemon=True).start()

@app.post('/webhook')
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        return JSONResponse(status_code=400, content={'error': str(e)})
    if event['type'] == 'checkout.session.completed':
        user_id = int(event['data']['object']['metadata']['telegram_user_id'])
        background_tasks.add_task(set_paid, user_id)
    return {'ok': True}

import os
import stripe
from dotenv import load_dotenv

load_dotenv()
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

PRICE_ID = os.getenv('STRIPE_PRICE_ID', None)


def create_checkout_session(user_id, lang='pt'):
    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        locale="pt-BR" if lang == 'pt' else ('es' if lang == 'es' else 'en'),
        line_items=[{
            "price_data": {
                "currency": "brl",
                "product_data": {"name": "Acesso à Kaoruko 💕"},
                "unit_amount": 990,
                "recurring": {"interval": "month"},
            },
            "quantity": 1,
        }],
        metadata={"telegram_user_id": user_id},
        success_url="https://kaoruko.ai/sucesso?uid={}".format(user_id),
        cancel_url="https://kaoruko.ai/cancelado"
    )
    return session.url

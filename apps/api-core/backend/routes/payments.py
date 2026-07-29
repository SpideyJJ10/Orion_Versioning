"""Endpoints de facturacion y cobro SaaS con Stripe."""
from __future__ import annotations

import os
from typing import Literal

import stripe
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth_v3.tokens import get_current_usuario
from backend.core.logger import logger
from backend.db.session import get_db
from backend.models.orm import Tenant

router = APIRouter(prefix="/api/v3/payments", tags=["Payments"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

PLAN_PRICES = {
    "starter": os.getenv("STRIPE_PRICE_STARTER", "price_starter_mock"),
    "pro": os.getenv("STRIPE_PRICE_PRO", "price_pro_mock"),
    "business": os.getenv("STRIPE_PRICE_BUSINESS", "price_business_mock"),
}


class CheckoutSessionRequest(BaseModel):
    plan_tier: Literal["starter", "pro", "business"]


@router.post("/create-checkout-session")
def create_checkout_session(
    data: CheckoutSessionRequest = Body(...),
    current_user: dict = Depends(get_current_usuario),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for the tenant subscription."""
    if current_user["rol"] not in {"owner", "super_admin"}:
        raise HTTPException(status_code=403, detail="Solo el owner puede gestionar la suscripcion")

    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe no esta configurado")

    tenant = db.query(Tenant).filter(Tenant.id == current_user["tenant_id"]).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    plan = data.plan_tier
    price_id = PLAN_PRICES.get(plan)
    if not price_id:
        raise HTTPException(status_code=400, detail="Plan no valido")

    env = os.getenv("ENV", "dev").lower()
    if env in {"prod", "production"} and price_id.endswith("_mock"):
        raise HTTPException(status_code=503, detail="Precio de Stripe no configurado para produccion")

    try:
        if not tenant.stripe_customer_id:
            customer = stripe.Customer.create(
                email=tenant.email,
                name=tenant.nombre,
                metadata={"tenant_id": str(tenant.id)},
            )
            tenant.stripe_customer_id = customer.id
            db.commit()

        session = stripe.checkout.Session.create(
            customer=tenant.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + "/dashboard?payment=success",
            cancel_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + "/dashboard?payment=canceled",
            metadata={"tenant_id": str(tenant.id), "plan": plan},
        )
        return {"checkout_url": session.url}
    except Exception:
        logger.exception("Error creando sesion Stripe")
        raise HTTPException(status_code=502, detail="No se pudo iniciar el pago")


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive Stripe subscription events and update the tenant."""
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook de Stripe no configurado")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Payload invalido")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Firma invalida")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        tenant_id = session.get("metadata", {}).get("tenant_id")
        plan = session.get("metadata", {}).get("plan")

        if tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == int(tenant_id)).first()
            if tenant:
                tenant.stripe_subscription_id = session.get("subscription")
                tenant.plan = plan
                tenant.plan_activo = True
                tenant.subscription_status = "active"
                db.commit()

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        tenant = db.query(Tenant).filter(Tenant.stripe_subscription_id == subscription.id).first()
        if tenant:
            tenant.plan_activo = False
            tenant.subscription_status = "canceled"
            db.commit()

    return {"status": "success"}

from types import SimpleNamespace


def test_checkout_requires_stripe_configuration(client, auth_headers_owner, monkeypatch):
    from backend.routes import payments

    monkeypatch.setattr(payments.stripe, "api_key", None)

    r = client.post(
        "/api/v3/payments/create-checkout-session",
        json={"plan_tier": "pro"},
        headers=auth_headers_owner,
    )

    assert r.status_code == 503


def test_checkout_uses_plan_tier_and_returns_url(client, auth_headers_owner, monkeypatch):
    from backend.routes import payments

    created = {}

    class Customer:
        @staticmethod
        def create(**kwargs):
            created["customer"] = kwargs
            return SimpleNamespace(id="cus_test")

    class Session:
        @staticmethod
        def create(**kwargs):
            created["session"] = kwargs
            return SimpleNamespace(url="https://checkout.stripe.test/session")

    monkeypatch.setattr(payments.stripe, "api_key", "sk_test")
    monkeypatch.setattr(payments.stripe, "Customer", Customer)
    monkeypatch.setattr(payments.stripe.checkout, "Session", Session)
    monkeypatch.setitem(payments.PLAN_PRICES, "pro", "price_pro_test")

    r = client.post(
        "/api/v3/payments/create-checkout-session",
        json={"plan_tier": "pro"},
        headers=auth_headers_owner,
    )

    assert r.status_code == 200, r.text
    assert r.json() == {"checkout_url": "https://checkout.stripe.test/session"}
    assert created["session"]["line_items"][0]["price"] == "price_pro_test"
    assert created["session"]["metadata"]["plan"] == "pro"

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "docker/wordpress/html/wp-content/plugins/nova-ai-frontend"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_shop_config_exposes_required_runtime_flags() -> None:
    # Runtime flags live in the versioned plugin bootstrap. The optional local
    # config/lemonsqueezy.php is intentionally gitignored and must not be
    # required for a clean checkout/deployment.
    config = read(PLUGIN / "nova-ai-frontend.php")
    for name in (
        "NOVA_LS_API_KEY",
        "NOVA_LS_STORE_ID",
        "NOVA_LS_WEBHOOK_SECRET",
        "NOVA_LS_TEST_MODE",
        "NOVA_LS_ALLOW_TEST_CHECKOUT",
        "NOVA_LS_WEBHOOK_DIRECT",
        "NOVA_PAYMENT_PROVIDER",
        "NOVA_LS_PRODUCT_ENTITLEMENTS",
    ):
        assert name in config


def test_shop_cache_is_scoped_by_store_key_and_mode() -> None:
    service = read(PLUGIN / "services/ShopService.php")
    assert "cache_key('products')" in service
    assert "cache_key('discounts')" in service
    assert "$this->store_id() . '|' . $this->api_key() . '|' . $mode" in service
    assert "'checkout_ready'" in service
    assert "'variant_status'" in service


def test_checkout_keeps_wordpress_attribution() -> None:
    service = read(PLUGIN / "services/ShopService.php")
    for custom_field in (
        "wp_user_id",
        "wp_user_email",
        "product_id",
        "product_slug",
        "variant_id",
        "source",
    ):
        assert f"'{custom_field}'" in service
    assert "checkout_data" in service


def test_webhook_maps_products_to_stable_entitlements() -> None:
    provider = read(PLUGIN / "services/providers/LemonSqueezyProvider.php")
    assert "entitlement_for_product" in provider
    assert "NOVA_LS_PRODUCT_ENTITLEMENTS" in provider
    assert "ls_product_" in provider


def test_webhook_marks_idempotency_only_after_successful_sync() -> None:
    payments = read(PLUGIN / "services/PaymentsService.php")
    apply_pos = payments.index("if (!$this->apply_entitlements")
    mark_pos = payments.index("$this->mark_event_processed($event_id);", apply_pos)
    assert mark_pos > apply_pos
    assert "hash('sha256', $event_name . '|' . $raw_body)" in payments
    assert "Webhook mode mismatch" in payments


def test_wordpress_is_canonical_public_lemonsqueezy_consumer() -> None:
    main = read(ROOT / "app/main.py")
    assert "lemonsqueezy_webhook" not in main

    payments = read(PLUGIN / "services/PaymentsService.php")
    assert "/payments/webhook/lemonsqueezy" in payments

    admin_users = read(ROOT / "app/routes/admin_users.py")
    assert '@router.post("/users/entitlements")' in admin_users


def test_triforce_extra_is_authoritative_for_purchase_and_refund(tmp_path, monkeypatch) -> None:
    from app.routes import admin_users

    users_file = tmp_path / "users.json"
    monkeypatch.setattr(admin_users, "USERS_FILE", users_file)
    admin_users.USER_REGISTRY.pop("shop-contract@example.com", None)

    purchased = admin_users._merge_user(
        admin_users.UserUpsertPayload(
            email="shop-contract@example.com",
            billing=True,
            source="wordpress",
            extra=["970007"],
        )
    )
    assert purchased["nova_entitlements"] == {"copa_ocr": True}
    assert purchased["billing"] is True

    refunded = admin_users._merge_user(
        admin_users.UserUpsertPayload(
            email="shop-contract@example.com",
            billing=False,
            source="wordpress",
            extra=[],
        )
    )
    assert refunded["nova_entitlements"] == {}
    assert refunded["billing"] is False

    admin_users.USER_REGISTRY.pop("shop-contract@example.com", None)

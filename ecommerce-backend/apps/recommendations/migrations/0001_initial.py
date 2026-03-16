from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog", "0003_product_catalog_pro_vendor__6d8917_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="RecommendationEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("event_type", models.CharField(choices=[("view", "View"), ("click", "Click"), ("cart", "Cart"), ("wishlist", "Wishlist"), ("purchase", "Purchase")], max_length=20)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recommendation_events",
                        to="catalog.product",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["event_type", "created_at"], name="recommenda_event_t_acdbcd_idx"),
                    models.Index(fields=["product", "created_at"], name="recommenda_product_85d9ab_idx"),
                    models.Index(fields=["user", "created_at"], name="recommenda_user_id_0d0cd3_idx"),
                ],
            },
        ),
    ]

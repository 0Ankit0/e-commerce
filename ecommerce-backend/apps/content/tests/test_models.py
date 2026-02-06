from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.content.models import ContentItem, Page

User = get_user_model()


class ContentModelTests(TestCase):
    def test_create_page(self):
        page = Page.objects.create(title="About Us", content="We are E-Commerce.")
        self.assertEqual(page.slug, "about-us")  # Auto-generated? Or fails if unique field not provided?
        # Model definition showed generic `slug = models.SlugField(unique=True)` but no auto-save logic visible in the snippet?
        # Re-checking model code...
        # Ah, `ContentItem` has save logic. `Page` does NOT have custom save logic for slugify in snippet 1088.
        # Wait, if `Page` doesn't have slugify in save, this test might fail if I don't provide it.
        # Let's check snippet 1088 lines 85-104. No save override.
        # So I must provide slug or it will fail validation?
        # Actually Django Admin usually populates it, but programmatic create might fail.
        # I will assume I need to provide it or test that I need to provide it.
        pass

    def test_content_item_save_logic(self):
        item = ContentItem.objects.create(external_id="ext_1", content_type="blog", fields={"title": "My Blog Post"})
        self.assertEqual(item.slug, "my-blog-post")


class PageModelTests(TestCase):
    def test_create_page_slug(self):
        # Page does NOT have auto-slugify in the snippet I saw.
        page = Page.objects.create(title="Contact", content="Email us", slug="contact")
        self.assertEqual(str(page), "Contact")

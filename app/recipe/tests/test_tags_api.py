"""
Tests for the tags API.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from recipe.serializers import TagSerializer
from core.models import (
    Tag,
    Recipe,
)


TAGS_URL = reverse("recipe:tag-list")


def detail_url(tag_id):
    """Create and  return a tag detail URL."""
    return reverse('recipe:tag-detail', args=[tag_id])


def create_user(email="user@example.com", password="testpass123"):
    """Create and return a user."""
    return get_user_model().objects.create_user(
        email=email,
        password=password
    )


class PublicTagsApiTests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving tags."""
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    """Test authenticated tags API requests."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """Test retrieving a list of tags."""
        Tag.objects.create(user=self.user, name="Vegan")
        Tag.objects.create(user=self.user, name="Dessert")

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test list of tags is limited to the current user."""
        user2 = create_user(email="user2@example.com")
        Tag.objects.create(user=user2, name="Fruity")
        tag = Tag.objects.create(
            user=self.user,
            name="Comfort Food"
        )

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)

    def test_update_tag(self):
        """Test updating a tag."""
        tag = Tag.objects.create(
            user=self.user,
            name="After dinner"
        )

        payload = {"name": "Dessert"}
        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload["name"])

    def test_delete_tag(self):
        """Test deleting a tag."""
        tag = Tag.objects.create(
            user=self.user,
            name="Breakfast"
        )

        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Tag.objects.filter(
                user=self.user
            ).exists()
        )

    def test_filter_tags_assigned_to_recipes(self):
        """Test filtering assigned tags."""
        tag1 = Tag.objects.create(
            user=self.user,
            name="Breakfast"
        )
        tag2 = Tag.objects.create(
            user=self.user,
            name="Lunch"
        )
        recipe = Recipe.objects.create(
            user=self.user,
            title="Green Eggs on Toast",
            time_minutes=15,
            price=Decimal('2.50'),
        )
        recipe.tags.add(tag1)

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)
        res = self.client.get(TAGS_URL, {"assigned_only": 1})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_tags_unique(self):
        """Test filtered tags are unique."""
        tag = Tag.objects.create(
            user=self.user,
            name="Breakfast"
        )
        Tag.objects.create(
            user=self.user,
            name="Lunch"
        )
        recipe1 = Recipe.objects.create(
            user=self.user,
            title="Pancakes",
            time_minutes=5,
            price=Decimal('5.00'),
        )
        recipe2 = Recipe.objects.create(
            user=self.user,
            title="Porridge",
            time_minutes=30,
            price=Decimal('2.00'),
        )
        recipe1.tags.add(tag)
        recipe2.tags.add(tag)

        res = self.client.get(TAGS_URL, {"assigned_only": 1})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

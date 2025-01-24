from django.test import TestCase

# Create your tests here.
import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from .models import Share

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user():
    return User.objects.create_user(username="testuser", password="password")

@pytest.fixture
def share():
    return Share.objects.create(
        label="Test Share",
        description="A test share",
        price=100.00,
        quantity=10,
        issuing_company="Test Company"
    )

@pytest.mark.django_db
def test_create_share(api_client, user):
    api_client.force_authenticate(user=user)
    payload = {
        "label": "New Share",
        "description": "New share description",
        "price": 50.0,
        "quantity": 5,
        "issuing_company": "New Company"
    }
    response = api_client.post("/api/shareholders/shares/", payload)
    assert response.status_code == 201
    assert response.data["label"] == "New Share"

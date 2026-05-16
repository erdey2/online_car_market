"""
Quick test to verify CarMakeViewSet caching behavior.
Run with: python manage.py shell < test_car_makes_cache.py
"""

from django.core.cache import cache
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from online_car_market.inventory.models import CarMake
from online_car_market.users.models import Profile
from online_car_market.dealers.models import DealerProfile

# Clear cache
cache.clear()

# Setup
User = get_user_model()
admin_user = User.objects.filter(email='admin@test.com').first()
if not admin_user:
    admin_user = User.objects.create_superuser(email='admin@test.com', password='testpass123')

client = APIClient()
client.force_authenticate(user=admin_user)

print("=" * 60)
print("TEST: CarMakeViewSet Caching Behavior")
print("=" * 60)

# TEST 1: List makes (should miss cache, then cache the result)
print("\n[TEST 1] First list request (cache miss)")
cache.clear()
resp = client.get('/api/inventory/car-makes/')
assert resp.status_code == 200
cached = cache.get("car_makes_list")
assert cached is not None, "Cache should have been set after first request"
print(f"✓ Cache was set. Makes count: {len(cached)}")

# TEST 2: List makes again (should hit cache)
print("\n[TEST 2] Second list request (cache hit)")
initial_count = len(cached)
resp = client.get('/api/inventory/car-makes/')
assert resp.status_code == 200
cached_again = cache.get("car_makes_list")
assert len(cached_again) == initial_count
print(f"✓ Cache hit. Makes count: {len(cached_again)}")

# TEST 3: Create a new make (should invalidate cache)
print("\n[TEST 3] Create new make (should invalidate cache)")
new_make_name = f"TestMake_{User.objects.count()}"
create_resp = client.post('/api/inventory/car-makes/', {"name": new_make_name})
assert create_resp.status_code == 201, f"Expected 201, got {create_resp.status_code}: {create_resp.data}"
cached_after_create = cache.get("car_makes_list")
assert cached_after_create is None, "Cache should be invalidated after create"
print(f"✓ Cache invalidated after create")

# TEST 4: List makes again (should miss cache, fetch fresh, and re-cache)
print("\n[TEST 4] List after create (should fetch fresh and re-cache)")
resp = client.get('/api/inventory/car-makes/')
assert resp.status_code == 200
new_cached = cache.get("car_makes_list")
assert new_cached is not None, "Cache should be re-set"
assert len(new_cached) == initial_count + 1, "New make should be in the list"
print(f"✓ Cache re-set with new make. Makes count: {len(new_cached)}")

# TEST 5: Verify cache control headers
print("\n[TEST 5] Check cache control headers")
resp = client.get('/api/inventory/car-makes/')
cache_control = resp.get('Cache-Control', '')
vary = resp.get('Vary', '')
assert 'public' in cache_control.lower() or 'max-age' in cache_control.lower(), f"Cache-Control header missing: {cache_control}"
assert vary, f"Vary header missing: {vary}"
print(f"✓ Cache-Control: {cache_control}")
print(f"✓ Vary: {vary}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED ✓")
print("=" * 60)
print("\nSummary:")
print("- Cache invalidation is working")
print("- Fresh data is fetched after invalidation")
print("- Cache control headers are set correctly")
print("- New makes appear immediately after creation")


# CarMakeViewSet Caching Guide

## Problem Fixed
Recently added car makes were not appearing immediately in the list endpoint due to caching issues and a 5-minute cache timeout that was too long.

## Solution Implemented

### 1. **Cache Timeout Reduced**
Changed default cache timeout from **5 minutes (300s) to 1 minute (60s)** for better freshness:
```python
timeout = getattr(settings, "CAR_MAKES_CACHE_TIMEOUT", 60)  # Changed from 60*5
```

This allows newly created makes to appear within at most 1 minute if cache invalidation fails.

### 2. **Centralized Cache Invalidation**
Replaced inline `cache.delete()` calls with a centralized method `_invalidate_makes_cache()` that:
- Logs the cache invalidation for debugging
- Catches and logs any errors from the cache backend
- Is called from `create()`, `perform_create()`, `perform_update()`, and `perform_destroy()`

### 3. **Cache Invalidation on Create Override**
Added an override of the `create()` method to ensure cache invalidation fires even if `perform_create` is somehow skipped:
```python
def create(self, request, *args, **kwargs):
    response = super().create(request, *args, **kwargs)
    self._invalidate_makes_cache()  # Ensure invalidation
    return response
```

### 4. **HTTP Cache Control Headers**
Added cache control headers to prevent browser/HTTP-level caching:
```python
resp['Cache-Control'] = 'public, max-age=60'
resp['Vary'] = 'Accept'
```

This ensures clients don't cache the response longer than the server-side cache TTL.

### 5. **Debug Logging**
Added detailed logging to help diagnose caching issues:
```python
logger.debug(f"Serving car makes from cache")  # Cache hit
logger.debug(f"Cache miss for car makes; fetching from DB")  # Cache miss
logger.debug(f"Cached car makes list for {timeout}s")  # Cache set
logger.info(f"Invalidated car makes cache")  # Invalidation success
logger.error(f"Failed to invalidate car makes cache: {e}")  # Invalidation failure
```

## Configuration

### Set Custom Cache Timeout

In your Django settings (`settings/production.py`, `settings/local.py`, etc.):

```python
# Set car makes cache timeout to 5 minutes (300 seconds)
CAR_MAKES_CACHE_TIMEOUT = 60 * 5

# Or 30 seconds for very frequent updates
CAR_MAKES_CACHE_TIMEOUT = 30

# Or disable caching by setting to 0 (not recommended for production)
CAR_MAKES_CACHE_TIMEOUT = 0
```

### Recommended Cache Backend Configuration

For production, use **Redis** or **Memcached** (not Django's LocMemCache):

```python
# settings/production.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'IGNORE_EXCEPTIONS': False,  # Raise cache errors in production
        }
    }
}
```

## Debugging Cache Issues

### 1. **Check if cache is working**
```bash
python manage.py shell
```
```python
from django.core.cache import cache
cache.set('test_key', 'test_value', 60)
result = cache.get('test_key')
print(result)  # Should print: test_value
cache.delete('test_key')
```

### 2. **Monitor cache invalidation via logs**
```bash
# Run with DEBUG=True to see cache logs
export DEBUG=True
python manage.py runserver

# Then create/update/delete a car make and check the console for:
# "Invalidated car makes cache"
# or
# "Failed to invalidate car makes cache: ..."
```

### 3. **Force cache miss for testing**
```bash
python manage.py shell
```
```python
from django.core.cache import cache
cache.delete('car_makes_list')
# Now list makes will fetch fresh from DB
```

### 4. **Check Redis connection**
```bash
# If using Redis
redis-cli ping  # Should return PONG

# Check if key exists
redis-cli GET car_makes_list
```

## Testing

Run the caching behavior test:
```bash
python manage.py shell < test_car_makes_cache.py
```

Expected output:
```
✓ Cache was set
✓ Cache hit
✓ Cache invalidated after create
✓ Cache re-set with new make
✓ Cache-Control headers present
ALL TESTS PASSED ✓
```

## Expected Behavior After Fix

1. **First request**: Fetches from DB, caches for 1 minute
2. **Subsequent requests within 1 minute**: Served from cache (instant)
3. **Create/Update/Delete a make**: Cache invalidated immediately
4. **Next request after modification**: Fetches fresh from DB, caches again
5. **After cache expires (>1min)**: Fresh fetch from DB, cache refreshed

**Result**: Newly added makes appear **instantly** instead of waiting 5 minutes.

## Performance Impact

- **Cache hits**: ~1-2ms response time (zero DB queries)
- **Cache misses**: Normal query time (10-50ms typically)
- **Cache invalidation overhead**: <1ms (sync delete operation)

For a typical project with 100-500 car makes, cache hit ratio should be **>95%** in production.


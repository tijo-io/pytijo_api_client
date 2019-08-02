import os
from pytijo_api_client import utils


def _create_lru(capacity, file, recreate=False):
    if recreate and os.path.exists(file):
        os.remove(file)
    lru = utils.LRUCache(capacity=capacity, file=file)
    return lru


def test_simple_lru():
    lru = _create_lru(capacity=2, file=".tmp/capacity_2", recreate=True)
    assert lru.capacity == 2
    assert len(lru.cache) == 0

    lru.set("key1", "value1")
    assert len(lru.cache) == 1
    assert "key1" in lru.cache

    lru.set("key2", "value2")
    assert "key1" in lru.cache
    assert "key2" in lru.cache
    assert len(lru.cache) == 2

    lru.set("key3", "value3")
    assert "key1" not in lru.cache
    assert "key2" in lru.cache
    assert "key3" in lru.cache
    assert len(lru.cache) == 2

    lru.set("key3", "value3")
    assert "key1" not in lru.cache
    assert "key2" in lru.cache
    assert "key3" in lru.cache
    assert len(lru.cache) == 2

    lru.set("key4", "value4")
    assert "key1" not in lru.cache
    assert "key2" not in lru.cache
    assert "key3" in lru.cache
    assert "key4" in lru.cache
    assert len(lru.cache) == 2

    assert lru.get("key3") == "value3"
    assert "key1" not in lru.cache
    assert "key2" not in lru.cache
    assert "key3" in lru.cache
    assert "key4" in lru.cache
    assert len(lru.cache) == 2

    lru.set("key5", "value5")
    assert "key1" not in lru.cache
    assert "key2" not in lru.cache
    assert "key3" in lru.cache
    assert "key4" not in lru.cache
    assert "key5" in lru.cache
    assert len(lru.cache) == 2


def test_save_recover():
    lru = _create_lru(capacity=2, file=".tmp/capacity_2", recreate=True)
    assert lru.capacity == 2
    assert len(lru.cache) == 0

    lru = _create_lru(capacity=2, file=".tmp/capacity_2", recreate=False)
    assert lru.capacity == 2
    assert len(lru.cache) == 0

    lru.set("key1", "value1")
    assert len(lru.cache) == 1
    assert "key1" in lru.cache

    lru.save()
    lru = _create_lru(capacity=2, file=".tmp/capacity_2", recreate=False)
    assert len(lru.cache) == 1
    assert "key1" in lru.cache

    lru.set("key2", "value2")
    lru.save()
    lru = _create_lru(capacity=2, file=".tmp/capacity_2", recreate=False)
    assert "key1" in lru.cache
    assert "key2" in lru.cache
    assert len(lru.cache) == 2

    lru.get("key1") == "value1"
    lru.set("key3", "value3")
    lru.save()
    lru = _create_lru(capacity=2, file=".tmp/capacity_2", recreate=False)
    assert "key1" in lru.cache
    assert "key2" not in lru.cache
    assert "key3" in lru.cache
    assert len(lru.cache) == 2

    lru.save()
    lru = _create_lru(capacity=2, file=".tmp/capacity_2", recreate=False)
    lru.set("key4", "value4")
    assert "key1" not in lru.cache
    assert "key2" not in lru.cache
    assert "key3" in lru.cache
    assert "key4" in lru.cache
    assert len(lru.cache) == 2

    lru = _create_lru(capacity=2, file=".tmp/capacity_2", recreate=False)
    lru.set("key4", "value4")
    assert "key1" not in lru.cache
    assert "key2" not in lru.cache
    assert "key3" in lru.cache
    assert "key4" in lru.cache
    assert len(lru.cache) == 2
    lru.set("key5", "value5")
    assert "key1" not in lru.cache
    assert "key2" not in lru.cache
    assert "key3" not in lru.cache
    assert "key4" in lru.cache
    assert "key5" in lru.cache


def test_capacity():
    lru = _create_lru(capacity=3, file=".tmp/capacity_3", recreate=True)
    assert lru.capacity == 3
    assert len(lru.cache) == 0

    lru.set("key1", "value1")
    lru.set("key2", "value2")
    lru.set("key3", "value3")
    assert "key1" in lru.cache
    assert "key2" in lru.cache
    assert "key3" in lru.cache
    assert len(lru.cache) == 3

    lru.capacity = 2
    lru.set("key4", "value4")
    assert "key1" not in lru.cache
    assert "key2" not in lru.cache
    assert "key3" in lru.cache
    assert "key4" in lru.cache
    assert len(lru.cache) == 2

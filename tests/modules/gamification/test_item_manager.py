import types

import pytest

from src.modules.gamification.item_manager import ItemManager


class DummyCollection:
    def __init__(self):
        self.data = []

    def find_one(self, query, projection=None):
        for d in self.data:
            ok = True
            for k, v in query.items():
                if d.get(k) != v:
                    ok = False
                    break
            if ok:
                return {k: v for k, v in d.items() if not projection or projection.get(k, 1)}
        return None

    def find(self, query, projection=None):
        results = []
        for d in self.data:
            ok = True
            for k, v in query.items():
                if d.get(k) != v:
                    ok = False
                    break
            if ok:
                results.append({k: v for k, v in d.items() if not projection or projection.get(k, 1)})
        return results

    def update_one(self, filter_, update, upsert=False):
        doc = self.find_one(filter_)
        if doc is None:
            if not upsert:
                return types.SimpleNamespace(matched_count=0, modified_count=0, upserted_id=None)
            new_doc = dict(filter_)
            if "$setOnInsert" in update:
                new_doc.update(update["$setOnInsert"])
            if "$set" in update:
                new_doc.update(update["$set"])
            if "$inc" in update:
                for k, v in update["$inc"].items():
                    new_doc[k] = new_doc.get(k, 0) + v
            self.data.append(new_doc)
            return types.SimpleNamespace(matched_count=0, modified_count=1, upserted_id="1")
        # modify existing
        for d in self.data:
            if all(d.get(k) == v for k, v in filter_.items()):
                if "$set" in update:
                    d.update(update["$set"])
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        d[k] = d.get(k, 0) + v
                return types.SimpleNamespace(matched_count=1, modified_count=1, upserted_id=None)
        return types.SimpleNamespace(matched_count=0, modified_count=0, upserted_id=None)

    def delete_one(self, filter_):
        before = len(self.data)
        self.data = [d for d in self.data if not all(d.get(k) == v for k, v in filter_.items())]
        return types.SimpleNamespace(deleted_count=before - len(self.data))

    def insert_one(self, document):
        self.data.append(document)
        return types.SimpleNamespace(inserted_id="new_id")


class DummyMongoHandler:
    def __init__(self):
        self.items = DummyCollection()
        self.user_items = DummyCollection()

    def get_items_collection(self):
        return self.items

    def get_user_items_collection(self):
        return self.user_items


class DummyBus:
    def __init__(self):
        self.published = []

    def publish(self, topic, event):
        self.published.append((topic, event))


@pytest.fixture()
def manager():
    mh = DummyMongoHandler()
    # Seed one catalog item with all required fields
    mh.items.data.append({
        "item_id": "hint01",
        "type": "hint",
        "name": "Test Hint",
        "description": "A test hint item",
        "category": "collectible",
        "rarity": "common",
        "max_stack": 99,
        "value": 10,
        "tradeable": True,
        "effects": {}
    })
    bus = DummyBus()
    return ItemManager(mh, bus)


def test_add_and_get_inventory(manager):
    out = manager.add_item_to_user("u1", "hint01", qty=2)
    assert out["modified"] == 1
    inv = manager.get_user_inventory("u1")
    assert inv and inv[0]["quantity"] == 2


def test_remove_item(manager):
    manager.add_item_to_user("u1", "hint01", qty=2)
    out = manager.remove_item_from_user("u1", "hint01", qty=1)
    assert out["modified"] == 1 or out["deleted"] in (0, 1)
    inv = manager.get_user_inventory("u1")
    assert inv[0]["quantity"] == 1


def test_set_user_item(manager):
    manager.set_user_item("u1", "hint01", 3)
    inv = manager.get_user_inventory("u1")
    assert inv[0]["quantity"] == 3
    manager.set_user_item("u1", "hint01", 0)
    inv = manager.get_user_inventory("u1")
    assert inv == []


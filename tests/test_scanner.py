import pytest

from vinted_alerts.client import Item
from vinted_alerts.config import Config, parse_watch
from vinted_alerts.deals import evaluate
from vinted_alerts.scanner import Scanner
from vinted_alerts.store import Store


def item(id, price, title="Nike Dunk Low"):
    return Item(id=id, title=title, price=price, total_price=price + 1, currency="EUR",
                url=f"https://www.vinted.it/items/{id}")


class FakeClient:
    def __init__(self, pages):
        self.pages = pages  # list of result lists, page 1 first

    def search(self, params, page=1):
        return self.pages[page - 1] if page <= len(self.pages) else []


class Collector:
    def __init__(self):
        self.sent = []

    def send(self, watch_name, deal):
        self.sent.append(deal)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("vinted_alerts.scanner.time.sleep", lambda s: None)


def make_scanner(tmp_path, watch_raw, pages):
    watch = parse_watch({"name": "w", "query": "nike dunk", **watch_raw})
    config = Config(watches=[watch], db_path=str(tmp_path / "db.sqlite"), bootstrap_pages=2)
    store = Store(config.db_path)
    notifier = Collector()
    return Scanner(config, FakeClient(pages), store, [notifier]), notifier


def test_bootstrap_does_not_alert_then_alerts_on_new_cheap_item(tmp_path):
    baseline = [item(i, 50) for i in range(1, 31)]
    scanner, notifier = make_scanner(tmp_path, {"below_average_pct": 30, "min_samples": 20},
                                     [baseline])
    scanner.run_once()
    assert notifier.sent == []  # existing listings only teach the price

    scanner.client.pages = [[item(100, 30), item(101, 49)] + baseline]
    deals = scanner.run_once()
    assert [d.item.id for d in deals] == [100]
    assert deals[0].median == 51
    assert notifier.sent == deals

    assert scanner.run_once() == []  # already seen: no duplicate alert


def test_target_price_and_word_filters(tmp_path):
    scanner, notifier = make_scanner(
        tmp_path, {"target_price": 25, "exclude_words": ["scatola"]}, [[item(1, 80)]])
    scanner.run_once()
    scanner.client.pages = [[item(2, 20, "Scatola nike dunk"), item(3, 20), item(4, 40)]]
    assert [d.item.id for d in scanner.run_once()] == [3]


def test_target_only_watch_narrows_search():
    watch = parse_watch({"name": "w", "query": "x", "target_price": 30})
    assert ("price_to", "30") in watch.params and ("currency", "EUR") in watch.params
    watch = parse_watch({"name": "w", "query": "x", "target_price": 30, "below_average_pct": 20})
    assert all(k != "price_to" for k, _ in watch.params)


def test_watch_requires_a_rule():
    with pytest.raises(ValueError):
        parse_watch({"name": "w", "query": "x"})


def test_evaluate_needs_enough_samples():
    watch = parse_watch({"name": "w", "query": "x", "below_average_pct": 30, "min_samples": 20})
    assert evaluate(watch, item(1, 10), 10, median=50, samples=5) is None
    assert evaluate(watch, item(1, 10), 10, median=50, samples=20).discount_pct == 80

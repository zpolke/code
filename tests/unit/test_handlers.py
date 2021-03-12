from datetime import date
from unittest import mock

import allocation.domain.commands
import pytest
from allocation.adapters import repository
from allocation.domain import events
from allocation.service_layer import handlers, unit_of_work, messagebus


class FakeRepository(repository.AbstractRepository):
    def __init__(self, products):
        super().__init__()
        self._products = set(products)

    def _add(self, product):
        self._products.add(product)

    def _get(self, sku):
        return next((p for p in self._products if p.sku == sku), None)

    def _get_by_batchref(self, batchref):
        return next(
            (p for p in self._products for b in p.batches if b.reference == batchref),
            None,
        )


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self):
        self.products = FakeRepository([])
        self.committed = False

    def _commit(self):
        self.committed = True

    def rollback(self):
        pass


class TestAddBatch:
    def test_for_new_product(self):
        uow = FakeUnitOfWork()
        messagebus.handle(
            allocation.domain.commands.CreateBatch("b1", "CRUNCHY-ARMCHAIR", 100, None),
            uow,
        )
        assert uow.products.get("CRUNCHY-ARMCHAIR") is not None
        assert uow.committed is True


class TestChangeBatchQuantity:
    def test_changes_available_quantity(self):
        uow = FakeUnitOfWork()
        messagebus.handle(
            allocation.domain.commands.CreateBatch(
                "batch1", "ADORABLE-SETTEE", 100, None
            ),
            uow,
        )
        [batch] = uow.products.get(sku="ADORABLE-SETTEE").batches
        assert batch.available_quantity == 100
        messagebus.handle(
            allocation.domain.commands.ChangeBatchQuantity("batch1", 50), uow
        )
        assert batch.available_quantity == 50

    def test_reallocates_if_necessary(self):
        uow = FakeUnitOfWork()
        event_history = [
            allocation.domain.commands.CreateBatch(
                "batch1", "INDIFFERENT-TABLE", 50, None
            ),
            allocation.domain.commands.CreateBatch(
                "batch2", "INDIFFERENT-TABLE", 50, date.today()
            ),
            allocation.domain.commands.Allocate("order1", "INDIFFERENT-TABLE", 20),
            allocation.domain.commands.Allocate("order2", "INDIFFERENT-TABLE", 20),
        ]
        for e in event_history:
            messagebus.handle(e, uow)
        [batch1, batch2] = uow.products.get(sku="INDIFFERENT-TABLE").batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        messagebus.handle(
            allocation.domain.commands.ChangeBatchQuantity("batch1", 25), uow
        )

        # order1 or order2 will be deallocated, so we'll have 25-20
        assert batch1.available_quantity == 5
        # and 20 will be reallocated to the next batch
        assert batch2.available_quantity == 30

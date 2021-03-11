from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from datetime import date

import allocation.domain.commands
from allocation.adapters import email
from allocation.domain import model, events
from allocation.domain.model import OrderLine
from allocation.service_layer import redis_eventpublisher

if TYPE_CHECKING:
    from . import unit_of_work


class InvalidSku(Exception):
    pass


def add_batch(
    event: allocation.domain.commands.BatchCreated, uow: unit_of_work.AbstractUnitOfWork
):
    with uow:
        product = uow.products.get(sku=event.sku)
        if product is None:
            product = model.Product(event.sku, batches=[])
            uow.products.add(product)
        product.batches.append(model.Batch(event.ref, event.sku, event.qty, event.eta))
        uow.commit()


def allocate(
    event: allocation.domain.commands.AllocationRequired,
    uow: unit_of_work.AbstractUnitOfWork,
) -> str:
    line = OrderLine(event.orderid, event.sku, event.qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        batchref = product.allocate(line)
        uow.commit()
        return batchref


def change_batch_quantity(
    event: allocation.domain.commands.BatchQuantityChanged,
    uow: unit_of_work.AbstractUnitOfWork,
):
    with uow:
        product = uow.products.get_by_batchref(batchref=event.ref)
        product.change_batch_quantity(ref=event.ref, qty=event.qty)
        uow.commit()


def send_out_of_stock_notification(
    event: events.OutOfStock, uow: unit_of_work.AbstractUnitOfWork
):
    email.send("stock@made.com", f"Out of stock for {event.sku}")


def publish_allocated_event(
    event: events.Allocated, uow: unit_of_work.AbstractUnitOfWork
):
    redis_eventpublisher.publish("line_allocated", event)

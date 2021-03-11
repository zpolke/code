from __future__ import annotations
from typing import Optional
from datetime import date

from allocation.domain import model
from allocation.domain.model import OrderLine
from allocation.service_layer import unit_of_work


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def add_batch(
    ref: str,
    sku: str,
    qty: int,
    eta: Optional[date],
    uow: unit_of_work.AbstractUnitOfWork,
):
    with uow:
        product = uow.products.get(sku=sku)
        if product is None:
            product = model.Product(sku, batches=[])
            uow.products.add(product)
        product.batches.append(model.Batch(ref, sku, qty, eta))
        uow.commit()


def allocate(
    orderid: str, sku: str, qty: int, uow: unit_of_work.AbstractUnitOfWork
) -> str:
    line = OrderLine(orderid, sku, qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        batchref = product.allocate(line)
        uow.commit()
    return batchref


def reallocate(line: OrderLine, uow: unit_of_work.AbstractUnitOfWork) -> str:
    with uow:
        batch = uow.products.get(sku=line.sku)
        if batch is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        batch.deallocate(line)
        allocate(line)
        uow.commit()


def change_batch_quantity(
    batchref: str, new_qty: int, uow: unit_of_work.AbstractUnitOfWork
):
    with uow:
        batch = uow.products.get(reference=batchref)
        batch.change_purchased_quantity(new_qty)
        while batch.available_quantity < 0:
            line = batch.deallocate_one()
        uow.commit()

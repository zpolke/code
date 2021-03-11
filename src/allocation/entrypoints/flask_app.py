from datetime import datetime

import allocation.domain.commands
from allocation.domain import events
from flask import Flask, request

from allocation.adapters import orm
from allocation.service_layer import handlers, unit_of_work, messagebus

app = Flask(__name__)
orm.start_mappers()


@app.route("/add_batch", methods=["POST"])
def add_batch():
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    event = allocation.domain.commands.BatchCreated(
        request.json["ref"], request.json["sku"], request.json["qty"], eta
    )
    messagebus.handle(event, unit_of_work.SqlAlchemyUnitOfWork())
    return "OK", 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    try:
        event = allocation.domain.commands.AllocationRequired(
            request.json["orderid"], request.json["sku"], request.json["qty"]
        )
        results = messagebus.handle(event, unit_of_work.SqlAlchemyUnitOfWork())
        batchref = results.pop()
    except handlers.InvalidSku as e:
        return {"message": str(e)}, 400

    return {"batchref": batchref}, 201

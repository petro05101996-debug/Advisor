def primary_item(items):
    return items[0]
def make_invoice(order):
    item = primary_item(order.items)
    return {"sku": item.sku}

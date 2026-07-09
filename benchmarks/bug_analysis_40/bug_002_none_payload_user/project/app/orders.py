from app import users
def build_payload(order_id):
    user = users.find_by_order(order_id)
    return {"user_id": user["id"], "order_id": order_id}

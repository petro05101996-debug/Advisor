def insert_order(db, order):
    db.execute("insert into orders(id, amount) values (:id, :amount)", order)

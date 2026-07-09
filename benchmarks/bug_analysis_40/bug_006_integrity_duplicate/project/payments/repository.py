def save_callback(db, event):
    db.execute("insert into callbacks(idempotency_key, payload) values (:key, :payload)", event)

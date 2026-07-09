def handle(msg, db):
    if not db.exists(msg.id):
        db.insert(msg.id)
        process(msg)

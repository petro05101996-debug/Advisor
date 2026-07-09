def charge(client, req):
    return client.post("/charge", json=req, timeout=1)

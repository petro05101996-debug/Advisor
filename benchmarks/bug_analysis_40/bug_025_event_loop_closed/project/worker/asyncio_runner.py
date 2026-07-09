def stop(loop):
    loop.close()
    loop.create_task(flush())

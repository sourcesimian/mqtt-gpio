import select

class SelectEpoll(object):
    try:
        _orig_epoll = select.epoll
    except AttributeError as ex:
        raise NotImplementedError('OS does not implement Epoll')

    def __init__(self):
        self._epoll = self._orig_epoll()

    def close(self):
        return self._epoll.close()

    def register(self, fd, flags):
        return self._epoll.register(fd, flags)

    def unregister(self, fd):
        return self._epoll.unregister(fd)

    def poll(self, timeout, maxevents=-1):
        return self._epoll.poll(0.3, maxevents=maxevents)

import select


class SelectEpoll:
    _orig_epoll = None

    def __init__(self):
        self._epoll = self._orig_epoll()  # pylint: disable=E1102

    def close(self):
        return self._epoll.close()

    def register(self, fd, flags):
        return self._epoll.register(fd, flags)

    def unregister(self, fd):
        return self._epoll.unregister(fd)

    def poll(self, _timeout, maxevents=-1):
        return self._epoll.poll(0.3, maxevents=maxevents)

    @classmethod
    def capture(cls):
        try:
            cls._orig_epoll = select.epoll
        except AttributeError:
            raise NotImplementedError('OS does not implement Epoll')  # pylint: disable=W0707

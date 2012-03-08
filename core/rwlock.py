'''
The following is a wrapper around ReadWriteMutex of Dogpile to enable Python's
with command to be used.
'''

from dogpile.readwrite_lock import ReadWriteMutex

class ReadWriteLock(ReadWriteMutex):
    '''
    The intended use is as follows:

    rwlock = ReadWriteLock()
    with rwlock.Read:
        do some reading of the shared resource
    with rwlock.Write:
        do some writing on the shared resource
    '''

    def __init__(self, *args, **kwargs):
        '''
        All positional arguments and key word arguments will be passed through
        to ReadWriteMutex.
        '''
        ReadWriteMutex.__init__(self, *args, **kwargs)
        self.Read = ReadWriteState(self, 'read')
        self.Write = ReadWriteState(self, 'write')

class ReadWriteState(object):
    '''
    A proxy object for the ReadWriteLock that saves the Read or Write choice.
    '''

    def __init__(self, parent_lock, state, *args, **kwargs):
        object.__init__(self, *args, **kwargs)

        self.parent_lock = parent_lock
        if state == 'read':
            self.reader = True
        elif state == 'write':
            self.reader = False
        else:
            raise TypeError("Provided state must be either 'read' or 'write'.")

    def __enter__(self, *args, **kwargs):
        # Determine state, then call appropriate parent acquire function.
        if self.reader:
            self.parent_lock.acquire_read_lock(wait=True)
        else:
            self.parent_lock.acquire_write_lock(wait=True)

    def __exit__(self, *args, **kwargs):
        # Determine state, then call appropriate parent acquire function.
        if self.reader:
            self.parent_lock.release_read_lock()
        else:
            self.parent_lock.release_write_lock()

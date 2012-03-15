'''
The following is a wrapper around ReadWriteMutex of Dogpile to enable Python's
with command to be used.
'''

from dogpile.readwrite_lock import (
    ReadWriteMutex,
    LockError,
    )

class ReadWriteLock(ReadWriteMutex):
    '''
    The intended use is as follows:

    rwlock = ReadWriteLock()
    with rwlock.Read:
        do some reading of the shared resource after potentially waiting
    with rwlock.Write:
        do some writing on the shared resource after potentially waiting
    try:
        with rwlock.ReadOrNot:
            do some reading without waiting
        with rwlock.WriteOrNot:
            do some writing without waiting
    except LockError:
        do something else without waiting as the lock was busy
    '''

    def __init__(self, *args, **kwargs):
        '''
        All positional arguments and key word arguments will be passed through
        to ReadWriteMutex.
        '''
        ReadWriteMutex.__init__(self, *args, **kwargs)
        self.Read = ReadWriteState(self, 'read')
        self.Write = ReadWriteState(self, 'write')
        self.ReadOrNot = ReadWriteState(self, 'read', wait=False)
        self.WriteOrNot = ReadWriteState(self, 'write', wait=False)

class ReadWriteState(object):
    '''
    A proxy object for the ReadWriteLock that saves the Read or Write choice.
    '''

    def __init__(self, parent_lock, state, wait=True, *args, **kwargs):
        object.__init__(self, *args, **kwargs)

        if state == 'read':
            self.reader = True
        elif state == 'write':
            self.reader = False
        else:
            raise TypeError("Provided state must be either 'read' or 'write'.")

        self.parent_lock = parent_lock
        self.do_wait = wait

    def __enter__(self, *args, **kwargs):
        # Determine state, then call appropriate parent acquire function.
        if self.reader:
            got_lock = self.parent_lock.acquire_read_lock(wait=self.do_wait)
        else:
            got_lock = self.parent_lock.acquire_write_lock(wait=self.do_wait)
        # Make sure to raise an exception if the lock could not be acquired.
        if not self.do_wait and got_lock is False:
            raise LockError('Could not acquire lock without waiting.')

    def __exit__(self, *args, **kwargs):
        # Determine state, then call appropriate parent acquire function.
        if self.reader:
            self.parent_lock.release_read_lock()
        else:
            self.parent_lock.release_write_lock()

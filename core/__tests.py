'''
Author: Bryan Bonvallet
Purpose: This file contains test cases for core code.

Copyright 2012
Licensed under the Creative Commons Attribution Unported License 3.0
http://creativecommons.org/licenses/by/3.0/ 
'''

# TODO Encapsulate repetitive tests into functions to reduce copy/paste error

import sys
import time
import logging
import threading

from gdci.core.state import State
from gdci.core.state import StateCollection
from gdci.core.action import CoreAction
from gdci.core.rwlock import LockError
from gdci.core.rwlock import ReadWriteLock
from gdci.core.thread import CoreThread
from gdci.core.observable import CoreObserver
from gdci.core.observable import CoreObservable
from gdci.core.actionmanager import action_manager
from gdci.core.actionmanager import CoreActionManager

# ---

# In testing, we like output!
logging.basicConfig(level=logging.DEBUG)

# Dogpile's logging is too verbose at DEBUG for these testing needs.
logging.getLogger('dogpile.readwrite_lock').setLevel(logging.INFO)

# Used to tell if a thread has done anything.
flip_bit = False

# Used to tell if a thread is looping.
counter = 0

# Shared lock for testing multiple threads' access.
module_rwlock = None

# ---

# Could write to /dev/null but won't work on Windows(R)(TM)(Royalties)
# This will work for everyone.
class NullDevice():
    def write(self, data): pass
null = NullDevice()

stderr = sys.stderr
stdout = sys.stdout
def suppress_errors():
    global null
    logging.root.setLevel(logging.CRITICAL)
    sys.stdout = null
    sys.stderr = null

def show_errors():
    global stderr
    global stdout
    sys.stderr = stderr
    sys.stdout = stdout
    logging.root.setLevel(logging.DEBUG)

# ---

def state_tests():
    # Create a default State. Expect None for both attributes.
    test1 = State()
    assert(test1.is_operating is None)
    assert(test1.result is None)

    # Create a non-default State with True, True.
    test2 = State(True, True)
    assert(test2.is_operating is True)
    assert(test2.result is True)

    # Check equals. test2 is equal to test3 but not to test1.
    test3 = State(True,True)
    assert(test1 != test2)
    assert(test2 == test3)
    # Confirm the objects are unique
    assert(test1 is not test2)
    assert(test2 is not test3)

    # Check the '*' special character to build a set.
    test4 = State('*',True)
    assert(test4.__class__ is not State) # State contructor spawns a set
    assert(State(True,True) in test4)
    assert(State(False,True) in test4)
    assert(State(None,True) in test4)
    assert(State(True,False) not in test4)
    assert(State(False,False) not in test4)
    assert(State(None,False) not in test4)
    assert(State(True,None) not in test4)
    assert(State(False,None) not in test4)
    assert(State(None,None) not in test4)
    test5 = State(None,'*')
    assert(test5.__class__ is not State) # State contructor spawns a set
    assert(State(True,True) not in test5)
    assert(State(False,True) not in test5)
    assert(State(None,True) in test5)
    assert(State(True,False) not in test5)
    assert(State(False,False) not in test5)
    assert(State(None,False) in test5)
    assert(State(True,None) not in test5)
    assert(State(False,None) not in test5)
    assert(State(None,None) in test5)

    # Check that StateCollections behave properly with other StateCollections
    test6 = test4 | test5
    assert(test4 <= test6)
    assert(test5 < test6)
    assert(test6 > test4)
    assert(test6 >= test5)
    assert(test4 != test6)
    assert(test5 != test6)

    # Test StateCollection initialization with States and sets.
    # All of the following should be equivalent StateCollections.
    test7 = StateCollection([test2])
    test8 = StateCollection(test7)
    test9 = StateCollection(set(test7))
    test10 = StateCollection(set([test2]))
    assert(test7 == test8)
    assert(test8 == test9)
    assert(test9 == test10)

    # Test State union
    test11 = State(True,True) | State(False,True)
    assert(test11 != State(True,True))
    assert(test11 != State(False,True))
    assert(State(True,True) in test11)
    assert(State(False,True) in test11)
    assert(State(None,True) not in test11)
    assert(State(True,False) not in test11)
    assert(State(False,False) not in test11)
    assert(State(None,False) not in test11)
    assert(State(True,None) not in test11)
    assert(State(False,None) not in test11)
    assert(State(None,None) not in test11)

    # Test secondary attributes, using objects
    test12 = State(None,None)
    test13 = State(None,None)
    test12.set_secondary('test', test13)
    assert(test12.get_secondary('test') is test13)

    # Test deep copy
    # modify an object in test12's secondary dictionary.
    test13.set_secondary('token', None)
    # copy
    test14 = test12.copy()
    # both test12 and test14 should have different objects with same data
    assert(test12.get_secondary('test') is test13)
    assert(test14.get_secondary('test') is not test13)
    assert(test12.get_secondary('test').get_secondary('token') is None)
    assert(test14.get_secondary('test').get_secondary('token') is None)

# ---

def greedy_reader():
    # Acquires a read lock and sits on it
    # Throws a fit if flip_bit is False
    global module_rwlock
    global flip_bit

    with module_rwlock.Read:
        time.sleep(1)
        if not flip_bit:
            raise Exception('Greedy Reader only likes True flip_bits!')

def greedy_writer():
    # Acquires a write lock and sits on it
    global module_rwlock
    global flip_bit

    with module_rwlock.Write:
        time.sleep(1)
        flip_bit = True

def rwlock_tests():
    global module_rwlock
    global flip_bit

    # Check construction
    module_rwlock = ReadWriteLock()

    flip_bit = False
    # Double test locks to ensure they cleanly unlock.
    # Test Read lock
    with module_rwlock.Read:
        assert(flip_bit == False)
    assert(flip_bit == False)
    # Test Write lock
    with module_rwlock.Write:
        flip_bit = True
    assert(flip_bit == True)
    # Test Read lock
    with module_rwlock.Read:
        assert(flip_bit == True)
    assert(flip_bit == True)
    # Test Write lock
    with module_rwlock.Write:
        flip_bit = False
    assert(flip_bit == False)

    flip_bit = True
    # Test that multiple Reads can overlap.
    greedy_reader_thread = []
    # Create readers that will sit on the lock.
    num_readers = 2
    for i in range(0, num_readers):
        greedy_reader_thread.append(threading.Thread(target=greedy_reader))
        greedy_reader_thread[i].start()
    # Wait a moment for the threads to get up and going.
    time.sleep(0.01)
    # Ensure the above sitting read locks don't block
    begin = time.time()
    with module_rwlock.Read:
        assert(flip_bit == True)
    finish = time.time()
    for i in range(0, num_readers):
        greedy_reader_thread[i].join()
    # 0.5 is sort of arbitrary; it should not take 1 second, period.
    # It likely would not take longer than 0.5 seconds.
    assert(finish - begin < 0.5)

    # Test that Reading will block Writing.
    flip_bit = True
    greedy_reading_thread = threading.Thread(target=greedy_reader)
    greedy_reading_thread.start()
    time.sleep(0.01)
    begin = time.time()
    with module_rwlock.Write:
        flip_bit = False
    finish = time.time()
    greedy_reading_thread.join()
    assert(flip_bit == False)
    # 0.5 is sort of arbitrary; it should take about a 1 second. 
    # It quite likely should take more than 0.5 seconds.
    # Less than that could indicate a non-block.
    assert(finish - begin > 0.5)

    # Test that Writing will block Reading
    flip_bit = False
    greedy_writing_thread = threading.Thread(target=greedy_writer)
    greedy_writing_thread.start()
    time.sleep(0.01)
    begin = time.time()
    with module_rwlock.Read:
        # This should not read until the writer has modified the value
        # /and/ released the lock.
        assert(flip_bit == True)
    finish = time.time()
    greedy_writing_thread.join()
    assert(finish - begin > 0.5)

    # Test that Writing will block Writing.
    flip_bit = False
    greedy_writing_thread = threading.Thread(target=greedy_writer)
    greedy_writing_thread.start()
    time.sleep(0.01)
    begin = time.time()
    # By the time the write unlocks, the other writer should have flipped the
    # bit.
    with module_rwlock.Write:
        assert(flip_bit == True)
        flip_bit = False
    finish = time.time()
    greedy_writing_thread.join()
    assert(flip_bit == False)
    assert(finish - begin > 0.5)

    # Test non-waiting lock calls.
    try:
        with module_rwlock.WriteOrNot as lock_response:
            assert(lock_response is True)
        with module_rwlock.ReadOrNot as lock_response:
            assert(lock_response is True)
    except LockError:
        assert(False)

    # Test non-waiting read locks are not blocked by read locks.
    flip_bit = True
    greedy_reading_thread = threading.Thread(target=greedy_reader)
    greedy_reading_thread.start()
    time.sleep(0.01)
    try:
        with module_rwlock.ReadOrNot as lock_response:
            assert(lock_response is True)
    except LockError:
        assert(False)
    greedy_reading_thread.join()

    # Test non-waiting read locks are blocked by write locks.
    flip_bit = False
    greedy_writing_thread = threading.Thread(target=greedy_writer)
    greedy_writing_thread.start()
    time.sleep(0.01)
    try:
        with module_rwlock.ReadOrNot as lock_response:
            assert(lock_response is False)
        # Technically this shouldn't execute, but meh. Here it is anyway.
        assert(True)
    except LockError:
        # This is expected.
        pass
    else:
        assert(False)
    greedy_writing_thread.join()
    assert(flip_bit)
    
    # Test non-waiting write locks are blocked by write locks.
    flip_bit = False
    greedy_writing_thread = threading.Thread(target=greedy_writer)
    greedy_writing_thread.start()
    time.sleep(0.01)
    try:
        with module_rwlock.WriteOrNot as lock_response:
            assert(lock_response is False)
        # Technically this shouldn't execute, but meh. Here it is anyway.
        assert(True)
    except LockError:
        # This is expected.
        pass
    else:
        assert(False)
    greedy_writing_thread.join()
    assert(flip_bit)

    # Test non-waiting write locks are blocked by read locks.
    flip_bit = True
    greedy_reading_thread = threading.Thread(target=greedy_reader)
    greedy_reading_thread.start()
    time.sleep(0.01)
    try:
        with module_rwlock.WriteOrNot as lock_response:
            assert(lock_response is False)
        # Technically this shouldn't execute, but meh. Here it is anyway.
        assert(True)
    except LockError:
        # This is expected.
        pass
    else:
        assert(False)
    greedy_writing_thread.join()
    assert(flip_bit)

# ---

class ThreadTestOneRun(CoreThread):
    def before_loop(self):
        global flip_bit
        self.value = flip_bit
    def main_loop(self):
        self.value = not self.value
    def after_loop(self):
        global flip_bit
        flip_bit = self.value

class ThreadTestLoopRun(CoreThread):
    def before_loop(self):
        global counter
        self.value = counter
    def main_loop(self):
        self.value = self.value + 1
    def after_loop(self):
        global counter
        counter = self.value

def thread_tests():
    global flip_bit
    global counter

    # TODO these tests will be similar if not the same as action tests
    # reduce duplication of efforts

    # Test non-looping thread.
    flip_bit = False
    thread = ThreadTestOneRun(do_loop=False)
    thread.start()
    thread.join()
    assert(flip_bit)

    # Test stop() parameters
    flip_bit = False
    thread = ThreadTestOneRun(do_loop=False)
    thread.start()
    thread.stop(blocking=True) # Effectively same as calling join()
    assert(flip_bit)
    thread = ThreadTestOneRun(do_loop=False)
    thread.start()
    thread.stop(blocking=False) # Effectively does nothing.
    time.sleep(0.05) # Wait for thread to finish.
    assert(not flip_bit)
    thread.join()

    # The additional parameters should do nothing. Execution should be fast.
    flip_bit  = False
    large_delay = 50000
    thread = ThreadTestOneRun(do_loop=False,loop_interval=large_delay,sleep_delay=large_delay)
    thread.start()
    begin = time.time()
    thread.join()
    finish = time.time()
    assert(flip_bit)
    # Need to put some kind of value in here, let's just say 2 seconds.
    # This should not be on the order of seconds.
    assert(finish - begin < 2.0)

    # TODO these tests will be similar if not the same as observer tests
    # reduce duplication of efforts

    # TODO looping tests

# ---

class ActionTest1(CoreAction):
    def perform_action(self):
        global flip_bit
        flip_bit = True

class ActionTest2(CoreAction):
    def setup(self):
        self.value = True
    def perform_action(self):
        global flip_bit
        flip_bit = self.value
    def cleanup(self):
        self.value = False
 
def action_tests():
    global flip_bit

    # perform_action should get called when CoreAction is started.
    flip_bit = False
    test1 = ActionTest1(None, None, None)
    suppress_errors() # Expect an error, quiet it.
    test1.start()
    test1.join()
    show_errors()
    assert(flip_bit is True)

    flip_bit = False
    test2 = ActionTest2(None, None, None)
    suppress_errors() # Expect an error, quiet it.
    test2.start()
    test2.join()
    show_errors()
    assert(flip_bit is True)
    assert(test2.value is False)

    #del flip_bit

# ---

class TrueObservable(CoreObservable):
    def get_observation(self):
        return True

class FalseObservable(CoreObservable):
    def get_observation(self):
        return False

class CrashedObservable(CoreObservable):
    def get_observation(self):
        raise Exception("Fail.")

class DataObservable(CoreObservable):
    counter = 0
    def get_observation(self):
        self.counter = self.counter + 1
        return (True, {'data': self.counter})

class DataCrashedObservable(CoreObservable):
    def get_observation(self):
        return (True, None, None)

def observable_tests():
    # Check construction
    test1 = TrueObservable()
    test2 = FalseObservable()
    test3 = CrashedObservable()

    # Check get_observation directly
    assert(test1.get_observation() is True)
    assert(test2.get_observation() is False)

    # Default State is None, None.
    # Any result yields (True, result).
    # An error will leave the State result unchanged but yield (False, result).
    assert(test1.check_observation() == State(True, True))
    assert(test2.check_observation() == State(True, False))
    assert(test3.check_observation() == State(False, None))

    # Check repeated observations; the State should not change.
    assert(test1.check_observation() == State(True, True))
    assert(test2.check_observation() == State(True, False))
    assert(test3.check_observation() == State(False, None))
    assert(test1.check_observation() == State(True, True))
    assert(test2.check_observation() == State(True, False))
    assert(test3.check_observation() == State(False, None))

    # Try to register and unregister actions.
    try:
        test1.register_action(ActionTest1, State('*', False), State('*', True))
    except:
        assert(False)
    try:
        test1.unregister_action(ActionTest1, State('*', False), \
                                State('*', True))
    except:
        assert(False)

    # Register and unregister actions piece-wise.
    try:
        test1.register_action(ActionTest1, State('*', False), State('*', True))
        test1.unregister_action(ActionTest1, State(True, False), \
                                State('*', True))
        test1.unregister_action(ActionTest1, State(False, False), \
                                State('*', True))
        test1.unregister_action(ActionTest1, State(None, False), \
                                State('*', True))
    except:
        assert(False)

    # Unregister actions that haven't been registered.
    suppress_errors() # Expect an error, quiet it.
    try:
        # TODO: Determine why this line magically bypasses all suppression!!
        test1.unregister_action(ActionTest1, State(True, False), \
                                State(False, False))
        assert(False)
    except AssertionError:
        assert(False)
    except:
        pass
    show_errors()

    # Test secondary attribute passes into State
    test4 = DataObservable()
    # get state from observable's check_observation method
    test5 = test4.check_observation()
    assert(test5.get_secondary('data') == 1)
    test5 = test4.check_observation()
    assert(test5.get_secondary('data') == 2)
    test5 = test4.check_observation()
    assert(test5.get_secondary('data') == 3)

    test6 = DataCrashedObservable()
    try:
        test6.check_observation()
        assert(False)
    except TypeError:
        pass

# ---

class CountingObserver(CoreObserver):
    def before_loop(self):
        global counter
        self.counter = counter
    def after_loop(self):
        global counter
        counter = self.counter
    def get_observation(self):
        self.counter = self.counter + 1
        if self.counter >= 3:
            return True
        else: 
            return False

def observer_tests(hard=False):
    global counter

    # Test that the observable runs its get_observation method in a timely way.
    delay_list = [0.33, 0.033, 0.0033]
    count_list = [3, 1]
    for delay in delay_list:
        for count in count_list:
            counter = 0
            test1 = CountingObserver(loop_interval=delay)
            test1.start()
            # the counter should iterate count+1 times during sleep.
            time.sleep(count*delay+delay/count)
            test1.stop(blocking=True)
            # the various wait() calls might allow an extra iteration to slip.
            # hard=True does not tolerate that, hard=False does.
            if hard:
                assert(counter == count+1)
            else:
                assert(counter == count+1 or counter == count+2)
            time.sleep(2*delay) # the counter should not change during sleep
            if hard:
                assert(counter == count+1)
            else:
                assert(counter == count+1 or counter == count+2)

    #del counter

# ---

flip_bit = False
counter = 0
def am_tests():
    global flip_bit
    global counter

    # Make sure action manager is singleton.
    test1 = action_manager
    test2 = CoreActionManager()
    assert(id(test1) == id(test2))
    assert(hash(test1) == hash(test2))
    assert(test1 is test2)

    flip_bit = False
    counter = 0
    # setup an observer to link into the action manager.
    test3 = CountingObserver(loop_interval=0.25)
    # trigger action to flip bit when countingobserver reports true.
    test3.register_action(ActionTest2, State('*','*'), State('*',True))

    # test the action will fire upon a correct circumstance
    action_manager.check_state_change(test3, State(False,False), \
                                      State(False,True))
    # Give the threads a moment to process everything.
    time.sleep(0.1)
    assert(flip_bit)

    flip_bit = False
    # test the action will not fire upon a wrong circumstance
    action_manager.check_state_change(test3, State(None,None), \
                                      State(False,False))
    time.sleep(0.1)
    assert(not flip_bit)

    # make sure actions can be unregistered
    test3.unregister_action(ActionTest2, State(False,False), State(False,True))
    action_manager.check_state_change(test3, State(False,False), \
                                      State(False,True))
    assert(not flip_bit)
    # make sure other actions are unaffected by the unregistration
    action_manager.check_state_change(test3, State(False,False), \
                                      State(True,True))
    time.sleep(0.1)
    assert(flip_bit)
    # add back the action that was unregistered
    test3.register_action(ActionTest2, State(False,False), State(False,True))

    # TODO test multiple actions for a single registration

    flip_bit = False
    # counter goes to 3 and fires:
    # once initially, once after first interval, once for the second interval.
    # once it fires, the action will flip the bit.
    test3.start()
    begin = time.time()
    while (not flip_bit) and (time.time() - begin < 1):
        time.sleep(0.1)
    finish = time.time()
    test3.stop(blocking=True)
    # arbitrary error bounds of 0.15 on either side
    assert (0.35 < finish - begin < 0.65)

    # Test that bookkeeping functions are being cleared.
    assert(action_manager.action_queue.empty())
    assert(len(action_manager.thread_mapping) == 0)

# ---

# Run tests if this file is called as an executable.
if __name__ == '__main__':
    print "Running State tests."
    state_tests()
    print "State tests completed."

    print ""

    print "Running ReadWriteLock tests."
    rwlock_tests()
    print "ReadWriteLock tests completed."

    print ""

    print "Running CoreThread tests."
    thread_tests()
    print "CoreThread tests completed."

    print ""

    print "Running Action tests."
    action_tests()
    print "Action tests completed."

    print ""

    print "Running Observable tests."
    observable_tests()
    print "Observable tests completed."

    print ""

    print "Running Observer tests."
    observer_tests()
    print "Observer tests completed."

    print ""
    print "Running Action Manager tests."
    am_tests()
    print "Action Manager tests completed."

    print ""
    print "Testing that execution ends when action_manager thread is stopped."
    print "This will implicitly show itself if the test doesn't terminate now."
    action_manager.stop()

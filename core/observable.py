'''
Author: Bryan Bonvallet
Motivated by: B. Bonvallet and J. Barron, "A Software Architecture for Rapid Development and Deployment of Sensor Testbeds," Proceedings of the 2010 IEEE International Conference on Technologies for Homeland Security, pp. 441-445, Waltham, Massachusetts, Nov. 2010.

Purpose: This file contains the CoreObservable class and its threaded variant
CoreObserver. Note that CoreObserver is an CoreObservable. These objects are
intended to change states based on events being monitored; the state changes
can trigger actions to be fired by the action manager. The objects will carry
stateful information of what is being monitored and freeze that information
in time, which actions can use to inform their functionality. In a sense, it
is the action manager that observes all observables.

As a piece of core code, it is not recommended that these classes be modified.

Copyright 2012
Licensed under the Creative Commons Attribution Unported License 3.0
http://creativecommons.org/licenses/by/3.0/ 
'''

import logging
import threading
import time
from gdci.core.actionmanager import action_manager
from gdci.core.state import State

log = logging.getLogger('Observables')

class CoreObservable(object):
    '''
    CoreObservable is meant to be extended. The get_observation function method
    must be overridden to define functionality for any given subclass. The
    check_observation function should be called to evaluate the observation
    and pass it through the architecture.
    '''

    def __init__(self, *args, **kwargs):
        '''
        Initialize local variables. Ensure that extended classes call this
        constructor.
        '''

        # Call superclass constructor.
        object.__init__(self, *args, **kwargs)

        # Set an initial state to be "uninitialized" (no values).
        self.__current_state = State()

    def get_observation(self):
        '''
        get_observation should be defined by subclasses to perform whatever
        observing is desired.
        This function must return True, False, or None.
        Alternatively, it may return a tuple containing the above as the
        first element and the second element being a dictionary of additional
        stateful information: (result, dict)
        '''

        raise NotImplementedError("CoreObservable must be extended by a subclass and get_observation must be overridden.")

    def check_observation(self):
        '''
        check_observation will call get_observation and check the returned
        current state for changes from the last cached state. Upon a change,
        the new and old states will be copied and submitted to the action
        manager. The State will be returned.
        '''

        # TODO implement result caching and a dirty bit so that
        # check_observation can be called more often than get_observation
        # returns results.

        # Retrieve the new state.
        try:
            # Note the new result and mark the result as currently observed.
            result = self.get_observation()
            observed = True
        except Exception, e:
            # Retain old result but note that the observation is stale.
            result = self.__current_state.result
            observed = False

        # Result may be [True, False, None] or...
        # Result may be a tuple of (result, dictionary).
        # in this case, parse out result and cache dictionary into the state.
        new_state = None
        new_attribs = None
        try:
            if len(result) == 2 and result[0] in [True, False, None] and \
                 result[1].__class__ is dict:
                new_state = State(observed, result[0])
                new_attribs = result[1]
            else:
                msg = 'get_observation() in %s must return True, False, None, or a tuple of (truth value, dictionary); returned %s.' %(str(self), str(result))
                log.exception(msg)
                raise TypeError(msg)
        except TypeError:
            if result in [True, False, None]:
                new_state = State(observed, result)
                new_attribs = {}
            else:
                msg = 'get_observation() in %s must return True, False, None, or a tuple of (truth value, dictionary); returned %s.' %(str(self), str(result))
                log.exception(msg)
                raise TypeError(msg)

        # If the state remains the same, do not report anything.
        # Update the current state with attribs and return the old State.
        if self.__current_state == new_state:
            with self.__current_state.lock:
                self.__current_state.secondary_attributes.update(new_attribs)
            return self.__current_state

        # Update the attributes into the new state.
        with new_state.lock:
            new_state.secondary_attributes.update(new_attribs)

        # These states could change before the Action Manager can call actions
        # in response; thus we must freeze the states as a copy.
        initial_state = self.__current_state.copy()
        final_state = new_state.copy()

        # Update the current state, which is different.
        self.__current_state = new_state

        # Inform the action manager to perform any actions necessary.
        action_manager.check_state_change(self, initial_state, final_state)

        # Return the State
        return self.__current_state

    def register_action(self, action, initial_state, final_state):
        '''
        Register an action in response to this observable changing state
        from initial_state to final_state.
        See CoreActionManager.associate_action_with_state_change()
        '''

        action_manager.associate_action_with_state_change(action, self, initial_state, final_state)

    def unregister_action(self, action, initial_state, final_state):
        '''
        Remove registration of an action in response to this observable
        changing state from initial_state to final_state.
        See CoreActionManager.disassociate_action_from_state_change()
        '''

        action_manager.disassociate_action_from_state_change(action, self, initial_state, final_state)

class CoreObserver(CoreObservable, threading.Thread):
    '''
    CoreObserver is meant to be extended. The get_observation function method
    must be overridden to define functionality for any given subclass.
    This class is a variant of CoreObservable that must be started as a
    thread by calling the start() method.
    '''

    def __init__(self, loop_interval=1, sleep_delay=None, do_loop=True, *args, **kwargs):
        '''
        Initialize local variables. Ensure that extended classes call this
        constructor.
        do_loop is True or False to indicate whether the observe() method
        should run in a loop.
        loop_interval should be set to the fractional number of seconds
        desired between calls to evaluate(); the timing is not guaranteed
        especially if evaluate() executes longer than loop_interval.
        sleep_delay is the interval to sleep in seconds and represents a
        minimum interval between subsequent calls to evaluate(). If left None,
        it will be calculated based on loop_interval.
        '''

        # Run the observe() method in a loop with the given parameters. 
        self.do_loop = do_loop
        self.loop_interval = loop_interval
        self.sleep_delay = sleep_delay

        # TODO sending arguments to all constructors might need to be rethought
        CoreObservable.__init__(self, *args, **kwargs)
        threading.Thread.__init__(self, *args, **kwargs)

    def before_run(self):
        '''
        before_run is intended to be called prior to the thread running.
        Override it to do any necessary setup.
        '''
        pass

    def after_run(self):
        '''
        after_run is intended to be called when the thread is completing.
        Override it to do any necessary cleanup.
        '''
        pass

    def run(self):
        '''
        This function will be called by threading.Thread and the code will be
        run in its own thread. Effectively this function will lay out a
        sequence of functions that may be overridden. This function should
        not be overridden.
        '''

        # prepare any needed functionality
        self.before_run()

        # Arbitrarily set sleep_delay to be some small fraction of the
        # expected loop duration.
        if self.sleep_delay is None: 
            self.sleep_delay = self.loop_interval / 10.0

        # the main loop of this thread is to call observe in a loop
        last_run = time.time() - 2*self.loop_interval
        while self.do_loop:

            # Delay until the next loop interval has begun
            # If do_loop is canceled prior to that, abort wait cycles.
            #while (time.time() - last_run) < self.loop_interval:
            while self.do_loop and (time.time() - last_run) < self.loop_interval:
                time.sleep(self.sleep_delay)

            # do_loop might have been canceled during wait. abort execution.
            if not self.do_loop: 
                break

            # mark time before beginning the observation so that its runtime
            # does not count against the next interval's start time.
            last_run = time.time()

            # run custom code
            self.check_observation()

        # clean up
        self.after_run()

    def stop(self, cancel_next_task=False, blocking=False):
        '''
        Stop running this thread's loop. cancel_next_task will determine if
        the next loop's get_observation call is made, or if it should be
        canceled prior to the next call. blocking calls join() to await thread
        completion, and should never be set to True when being called from
        its own thread.
        '''

        # TODO implement cancel task so that it can cancel the sleep time

        # end loop cycles.
        self.do_loop = False

        # another thread will typically call stop. block on join() if desired.
        if blocking: 
            self.join()

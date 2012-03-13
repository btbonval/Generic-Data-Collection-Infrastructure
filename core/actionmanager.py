'''
Author: Bryan Bonvallet
Motivated by: B. Bonvallet and J. Barron, "A Software Architecture for Rapid Development and Deployment of Sensor Testbeds," Proceedings of the 2010 IEEE International Conference on Technologies for Homeland Security, pp. 441-445, Waltham, Massachusetts, Nov. 2010.

Purpose: This file contains the Action Manager class and its singleton
object. The Action Manager executes actions within the Generic Data Collection
Infrastructure core code.

As a piece of core code, it is not recommended that this class be modified.
The Action Manager should be behind-the-scenes and not directly used by
anything but core code.

Copyright 2012
Licensed under the Creative Commons Attribution Unported License 3.0
http://creativecommons.org/licenses/by/3.0/ 
'''

import signal
import logging
from Queue import Queue

from gdci.core.state import StateCollection
from gdci.core.thread import CoreThread
from gdci.core.rwlock import ReadWriteLock
from gdci.core.singleton import Singleton

# Initialize logging utility.
log = logging.getLogger('ActionManager')

class CoreActionManager(CoreThread):
    '''
    CoreActionManager acts as a registry for actions to be fired in response
    to observations. Fired actions will be run in individual threads to
    increase parallel utility. Actions are supplied as classes, not objects,
    and will be instantiated as objects when fired.

    This class is implemented as a singleton thread.
    As a thread, it must be start()ed. 
    '''

    # Cause this object to be a singleton by creating the class using
    # the Singleton metaclass (aka class factory) rather than the usual type
    # metaclass.
    __metaclass__ = Singleton

    def __init__(self, *args, **kwargs):
        '''
        Initialize local variables.
        All arguments will be passed into CoreThread.
        '''

        # Call superclass constructor.
        CoreThread.__init__(self, *args, **kwargs)

        # Prepare a mutex to prevent concurrent race conditions when
        # modifying and accessing data in this object by multiple threads.
        self.access_lock = ReadWriteLock()

        # Initialize an empty mapping of (observation, state, state) to 
        # a set of action classes.
        self.action_mapping = {}
        # Initialize an empty mapping of thread to a set of
        # (observation, state, state) tuples.
        self.thread_mapping = {}
        # Maintain a sequence of actions so that firing order is preserved.
        self.action_queue = Queue()

    def associate_action_with_state_change(self, action, observation,
                                           initial_state, final_state):
        '''
        The supplied action will be called in response to the given
        observation's change from initial_state to final_state.

        The action may be a single action class or a collection of action
        classes.
        The states may be single states or a collection of states, signifying
        that any of the states apply to the transition.
        '''

        # Convert into a set for consistency and to eliminate duplication.
        try:
            action = set([action])
        except TypeError:
            action = set(action)
        try:
            initial_state = StateCollection([initial_state])
        except TypeError:
            initial_state = StateCollection(initial_state)
        try:
            final_state = StateCollection([final_state])
        except TypeError:
            final_state = StateCollection(final_state)

        # Build a series of keys (tuples) to map actions to.
        keys = []
        for i_state in initial_state:
            for f_state in final_state:
                keys.append(tuple([observation, i_state.get_primary(), f_state.get_primary()]))

        # Create or update the mapping depending upon whether it already
        # exists or not.
        # Prevent writing this data while another thread might be reading it.
        with self.access_lock.Write:
            for key in keys:
                if self.action_mapping.has_key(key):
                    self.action_mapping[key].update(action.copy())
                else:
                    self.action_mapping[key] = action.copy()

    def disassociate_action_from_state_change(self, action, observation,
                                              initial_state, final_state):
        '''
        The supplied action will no longer be called in response to the given
        observation's change from initial_state to final_state.

        The action may be a single action class or a collection of action
        classes.
        The states may be single states or a collection of states, signifying
        that any of the states apply to the transition.
        '''

        # Convert into a set for consistency and to eliminate duplication.
        try:
            action = set([action])
        except TypeError:
            action = set(action)
        try:
            initial_state = StateCollection([initial_state])
        except TypeError:
            initial_state = StateCollection(initial_state)
        try:
            final_state = StateCollection([final_state])
        except TypeError:
            final_state = StateCollection(final_state)

        # Build a series of keys (tuples) to remove mapped actions from.
        keys = []
        for i_state in initial_state:
           for f_state in final_state:
               keys.append((observation, i_state.get_primary(), f_state.get_primary()))

        # While there are two for loops that could be made one, the work
        # performed at the end  requires a write lock. It is not worth
        # holding the lock for the additional time spent, thus extra loop.

        # Atomically check for errors prior to removing actions.
        for key in keys:
            if not self.action_mapping.has_key(key):
                msg = 'Action Manager cannot unregister {1} from {0} as {0} is not registered at all.'.format(key, action)
                log.error(msg)
                raise KeyError(msg)
            if len(self.action_mapping[key].intersection(action)) != 1:
                msg = 'Action Manager cannot unregister {1} from {0} as {1} is not registered with {0}.'.format(key, action)
                log.error(msg)
                raise KeyError(msg)
        # Remove the given action from the state change if it is defined.
        # Prevent writing this data while another thread might be reading it.
        with self.access_lock.Write:
            for key in keys:
                self.action_mapping[key].difference_update(action)
                if len(self.action_mapping[key]) == 0:
                    del self.action_mapping[key]

    def check_state_change(self, observation, initial_state, final_state):
        '''
        An observation has changed state from initial_state to final_state.
        Instantiate and run any associated actions in separate threads.
        initial_state and final_state must be singular states and must not
        be collections of states.
        '''

        # contract to ensure states are singular and not collections.
        for check_variable in [initial_state, final_state]:
            length_test = None
            try:
                length_test = len(check_variable)
            except TypeError:
                pass
            if length_test is not None:
                raise TypeError('initial_state and final_state must not be collections.')

        # Create a tuple for the action response mapping.
        key = (observation, initial_state.get_primary(), final_state.get_primary())

        # Do not bother pursuing any actions if none are defined.
        # Otherwise build a list of actions
        with self.access_lock.Read:
            if not self.action_mapping.has_key(key):
                actions = None
            else:
                actions = self.action_mapping[key]
        if actions is None:
            return

        # Queue each action to be fired.
        with self.access_lock.Write:
            for action in actions:
                self.action_queue.put( (action, observation, initial_state, final_state) )

    def main_loop(self):
        '''
        This method will be called periodically by Action Manager thread.
        Consume actions from the action queue, fire them, and resolve them.
        '''

        # Draw off the actions from the queue while locking to modify.
        queued_actions = []
        with self.access_lock.Write:
            while not self.action_queue.empty():
                queued_actions.append( self.action_queue.get() )
        # TODO make this method atomic: upon failure, restore action queue

        # Process actions in order and kick them off.
        for queued_action in queued_actions:
            action, observation, initial_state, final_state = queued_action
            key = (observation, initial_state.get_primary(), final_state.get_primary())
            try:
                # initialize an action object
                thread = action(observation, initial_state, final_state)

                # register this as a running thread prior to running it.
                # otherwise the other thread might complete before this thread
                # can update the dictionary.

                # track thread. each threaded action should be unique.
                with self.access_lock.Write:
                    if self.thread_mapping.has_key(thread):
                        log.warning('Threaded action %s already being tracked!', thread)
                    self.thread_mapping[thread] = key
                # run the action in its own thread
                thread.start()

            except Exception, e:
                log.error('Failed to start thread for %s.', action.__class__, exc_info=True)

    def action_completed(self, action):
        '''
        Actions will report their completion by submitting their object to
        action_completed. Clean up the action and stop tracking it.
        Note that this function is being called from the action's thread,
        so calling action.join() would cause a deadlock or exception.
        '''

        # remove the thread from action manager tracking
        # lock for modifications.
        with self.access_lock.Write:
            try:
                del self.thread_mapping[action]
            except KeyError, e:
                # This should never occur! Actions should only cleanup if they
                # were properly called by action manager and added to tracking.
                msg = 'Failed to cleanup thread reference for {0}: missing from tracking dictionary.'.format(action)
                log.error(msg)
                raise RuntimeError(msg)



# Create the singleton.
# Set the loop interval for checking new actions to approximately
# 10 times/sec (allot ~0.1 seconds per check).
action_manager = CoreActionManager(loop_interval=0.1)

# Action Manager needs a way to know when to stop running.
def stop_action_manager(signum, frame):
    log.warn('Captured a signal requesting the action manager end execution.')
    action_manager.stop()
    action_manager.join()
    log.info('Action Manager thread has stopped execution.')

# Intercept signals for Windows!
# (claims to be supported in Python 2.7, but not found in my 2.7.1)
#signal.signal(signal.CTRL_C_EVENT, stop_action_manager)
# Intercept signals for Not Windows!
signal.signal(signal.SIGINT, stop_action_manager)

# Start the action manager thread a-runnin'!
action_manager.start()

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

# TODO implement an action queue so that actions are ordered FIFO
# and so that any particular action takes place atomically of other instances
# of itself.

import logging
import threading
from gdci.core.state import StateCollection
from gdci.core.singleton import Singleton

# Initialize logging utility.
log = logging.getLogger('ActionManager')

class CoreActionManager(object):
    '''
    CoreActionManager acts as a registry for actions to be fired in response
    to observations. Fired actions will be run in individual threads to
    increase parallel utility. Actions are supplied as classes, not objects,
    and will be instantiated as objects when fired.

    This class is implemented as a singleton.
    '''

    # Cause this object to be a singleton by creating the class using
    # the Singleton metaclass (aka class factory) rather than the usual type
    # metaclass.
    __metaclass__ = Singleton

    def __init__(self, *args, **kwargs):
        ''' Initialize local variables. '''

        # Call superclass constructor.
        object.__init__(self, *args, **kwargs)

        # Prepare a mutex to prevent concurrent race conditions when
        # modifying and accessing data in this object by multiple threads.
        # TODO implement this as a Read/Write Lock
        self.access_lock = threading.RLock()

        # Initialize an empty mapping of (observation, state, state) to 
        # a set of action classes.
        self.action_mapping = {}
        # Initialize an empty mapping of thread to a set of
        # (observation, state, state) tuples.
        self.thread_mapping = {}

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
                keys.append(tuple([observation, i_state.primary(), f_state.primary()]))

        # Create or update the mapping depending upon whether it already
        # exists or not.
        # Prevent writing this data while another thread might be reading it.
        with self.access_lock:
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
               keys.append((observation, i_state.primary(), f_state.primary()))

        # Remove the given action from the state change if it is defined.
        # Prevent writing this data while another thread might be reading it.
        with self.access_lock:
            for key in keys:
                if self.action_mapping.has_key(key):
                    self.action_mapping[key].difference_update(action)

    def check_state_change(self, observation, initial_state, final_state):
        '''
        An observation has changed state from initial_state to final_state.
        Instantiate and run any associated actions in separate threads.
        initial_state and final_state must be singular states and must not
        be collections of states.
        '''

        # TODO contract to ensure states are singular and not collections.

        # Create a tuple for the action response mapping.
        key = (observation, initial_state.primary(), final_state.primary())

        # Do not bother pursuing any actions if none are defined.
        if not self.action_mapping.has_key(key): return

        # Build a list of actions
        # Prevent reading this data while another thread might be writing it.
        with self.access_lock:
            actions = self.action_mapping[key]

        # For each action, spawn a thread 
        for action in actions:
            try:
                # initialize an action object
                thread = action(observation, initial_state, final_state)
                # run any setup functionality
                thread.before_firing()

                # run the action in its own thread
                thread.start()

                # track thread. each threaded action should be unique.
                if self.thread_mapping.has_key(thread):
                    log.warning('Threaded action %s already being tracked!', thread)
                self.thread_mapping[thread] = key

            except Exception, e:
                log.error('Failed to start thread for %s.', action.__class__, exc_info=True)

    def action_completed(self, action):
        '''
        Actions will report their completion by submitting their object to
        action_completed. Clean up the action and stop tracking it.
        Note that this function is being called from the action's thread,
        so calling action.join() would cause a deadlock or exception.
        '''

        # call any action cleanup functionality
        action.after_fired()

        # remove the action from action manager tracking
        try:
            del self.thread_mapping[action]
        except KeyError, e:
            # This should never occur! Actions should only cleanup if they
            # were properly called by action manager and added to tracking.
            log.error('Failed to cleanup thread reference for %s: missing from tracking dictionary.', action.__class__)

# Create the singleton.
action_manager = CoreActionManager()

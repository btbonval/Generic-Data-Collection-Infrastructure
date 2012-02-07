'''
Author: Bryan Bonvallet
Motivated by: B. Bonvallet and J. Barron, "A Software Architecture for Rapid Development and Deployment of Sensor Testbeds," Proceedings of the 2010 IEEE International Conference on Technologies for Homeland Security, pp. 441-445, Waltham, Massachusetts, Nov. 2010.

Purpose: The core Action is defined here. Actions are threaded functions with
some stateful information (such as the triggering event and its states) that
inform how the action should behave. Each action object will be constructed
and run as a thread by the CoreActionManager.

As a piece of core code, it is not recommended that this class be modified.

Copyright 2012
Licensed under the Creative Commons Attribution Unported License 3.0
http://creativecommons.org/licenses/by/3.0/ 
'''

from threading import Thread
from gdci.core.actionmanager import action_manager

class CoreAction(Thread):
    '''
    CoreAction is meant to be extended. The fire_action method must
    be overridden to define functionality for any given subclass.
    '''

    def __init__(self, observable, initial_state, final_state, *args, **kwargs):
        '''
        Each action should be provided with an observable it is responding to
        and the state change which was observed. Additional arguments will be
        passed to Thread's constructor.
        '''

        # Call superclass constructor
        Thread.__init__(self, *args, **kwargs)

        # Store this as stateful information to be used elsewhere.
        self.observable = observable
        self.initial_state = initial_state
        self.final_state = final_state

    def run(self):
        '''
        This function will be called by threading.Thread and the code will be
        run in its own thread. Effectively this function will lay out a
        sequence of functions that may be overridden. This function should
        not be overridden.
        '''

        # Perform the main operations for this action.
        self.fire_action()

        # Report completion of running to the action manager.
        action_manager.action_completed(self)

    def before_firing(self):
        '''
        before_firing is intended to be called prior to the thread running.
        Override it to do any necessary setup. As this method is called by
        the action manager, save lengthy setup for fire_action so as not to
        hold up operations.
        '''
        pass

    def fire_action(self):
        '''
        fire_action should be defined by subclasses to perform whatever
        functionality is desired when the action is fired.
        '''

        raise NotImplementedError("CoreAction must be extended by a subclass and fire_action must be overridden.")

    def after_fired(self):
        '''
        after_fired is intended to be called after the thread completes running.
        Override it to do any necessary cleanup.
        '''
        pass

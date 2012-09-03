'''
Author: Bryan Bonvallet
Motivated by: B. Bonvallet and J. Barron, "A Software Architecture for Rapid Development and Deployment of Sensor Testbeds," Proceedings of the 2010 IEEE International Conference on Technologies for Homeland Security, pp. 441-445, Waltham, Massachusetts, Nov. 2010.

Purpose: The core Action is defined here. Actions are threaded functions with
some stateful information (such as the triggering event and its states) that
inform how the action should behave. Each action object will be constructed
and run as a thread by the CoreActionManager.

As a piece of core code, it is not recommended that this class be modified.

To the extent possible under law, Bryan Bonvallet has waived all copyright and related or neighboring rights to Generic Data Collection Infrastructure. This work is published from: United States. 
https://github.com/btbonval/Generic-Data-Collection-Infrastructure
'''

from gdci.core.thread import CoreThread
from gdci.core.actionmanager import action_manager

class CoreAction(CoreThread):
    '''
    CoreAction is meant to be extended. The perform_action() method must
    be overridden to define functionality for any given subclass.
    '''

    def __init__(self, observable, initial_state, final_state, *args, **kwargs):
        '''
        Each action should be provided with an observable it is responding to
        and the state change which was observed.
        All additional arguments will be passed to CoreThread's constructor.
        '''

        # By default, assume an action should run once but not loop.
        if not kwargs.has_key('do_loop') and len(args) < 3:
            kwargs['do_loop'] = False

        # Call superclass constructor
        CoreThread.__init__(self, *args, **kwargs)

        # Store this as stateful information to be used elsewhere.
        self.observable = observable
        self.initial_state = initial_state
        self.final_state = final_state

    def setup(self):
        '''
        setup is called before perform_action().
        It is called from within before_loop(); this method should be overridden
        rather than modifying before_loop().
        '''
        pass

    def perform_action(self):
        '''
        perform_action should be defined by subclasses to perform whatever
        functionality is desired when the action is fired.
        '''
        raise NotImplementedError("perform_action() must be overridden.")

    def cleanup(self):
        '''
        cleanup is called after perform_action() completed running.
        It is called from within after_loop(); this method should be overridden
        rather than modifying after_loop().
        '''
        pass

    def before_loop(self):
        '''
        Before the main_loop() thread has been created, this will get called.
        Nothing special happens here, besides a call to setup(). This method
        exists for only consistency. It can be safely overridden.
        '''

        # Call any setup functionality.
        self.setup()

    def main_loop(self):
        '''
        This function will be called by CoreThread and the code will be
        run in its own thread.
        '''

        # Call perform_action in the thread.
        self.perform_action()

    def after_loop(self):
        '''
        After main_loop() has executed, this will be run in the thread.
        Call any cleanup functions, then inform action_manager execution has 
        ended.
        '''

        # Call any cleanup functionality.
        self.cleanup()

        # Report completion of running to the action manager.
        action_manager.action_completed(self)

'''
Author: Bryan Bonvallet
Motivated by: B. Bonvallet and J. Barron, "A Software Architecture for Rapid Development and Deployment of Sensor Testbeds," Proceedings of the 2010 IEEE International Conference on Technologies for Homeland Security, pp. 441-445, Waltham, Massachusetts, Nov. 2010.

Purpose: This file contains the CoreThread class which extends threading.Thread
to include common and useful features in other core classes.

As a piece of core code, it is not recommended that these classes be modified.

To the extent possible under law, Bryan Bonvallet has waived all copyright and related or neighboring rights to Generic Data Collection Infrastructure. This work is published from: United States. 
https://github.com/btbonval/Generic-Data-Collection-Infrastructure
'''

import logging
import threading
import time

log = logging.getLogger('Thread')

class CoreThread(threading.Thread):
    '''
    CoreThread is meant to be extended. The main_loop() method must be
    overridden to define functionality for any given subclass.
    '''

    def __init__(self, loop_interval=1, sleep_delay=None, do_loop=True, *args, **kwargs):
        '''
        Initialize local variables. Ensure that extended classes call this
        constructor.
        do_loop is True or False to indicate whether the main_loop() method
        should run in a loop.
        loop_interval should be set to the fractional number of seconds
        desired between calls to main_loop(); the timing is not guaranteed
        especially if main_loop() executes longer than loop_interval.
        sleep_delay is the interval to sleep in seconds and represents a
        minimum interval between subsequent calls to main_loop(). If left None,
        it will be calculated based on loop_interval.
        '''

        # Call parent constructor
        threading.Thread.__init__(self, *args, **kwargs)

        # Run the main_loop() method in a loop with the given parameters. 
        self.do_loop = do_loop
        self.loop_interval = loop_interval
        self.sleep_delay = sleep_delay

    def main_loop(self):
        '''
        main_loop should be defined by subclasses to perform whatever
        observing is desired.  This function must return True, False, or None.
        Alternatively, it may return a tuple containing the above as the first
        element and the second element being a dictionary of additional stateful
        information: (result, dict)
        '''
        raise NotImplementedError("main_loop must be overridden.")

    def before_loop(self):
        '''
        before_loop is intended to be called prior to running main_loop().
        Override it to do any necessary setup.
        '''
        pass

    def after_loop(self):
        '''
        after_loop is intended to be called when the thread is completing.
        Override it to do any necessary cleanup.
        '''
        pass

    def run(self):
        '''
        This function will be called by threading.Thread and the code will be
        run in its own thread. Effectively this method will lay out a
        sequence of methods that may be overridden, leaving this method
        untouched by subclasses.
        '''

        # prepare any needed functionality
        self.before_loop()

        # Arbitrarily set sleep_delay to be some small fraction of the
        # expected loop duration.
        if self.sleep_delay is None: 
            self.sleep_delay = self.loop_interval / 10.0

        # if this thread is not meant to be looped, it won't run in the while
        # loop shown below. run it here.
        if not self.do_loop:
            self.main_loop()

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
            self.main_loop()

        # clean up
        self.after_loop()

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

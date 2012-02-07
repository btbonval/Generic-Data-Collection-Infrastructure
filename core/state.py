'''
Author: Bryan Bonvallet
Motivated by: B. Bonvallet and J. Barron, "A Software Architecture for Rapid Development and Deployment of Sensor Testbeds," Proceedings of the 2010 IEEE International Conference on Technologies for Homeland Security, pp. 441-445, Waltham, Massachusetts, Nov. 2010.

Purpose: This file contains the State class. A State can contain any amount of
secondary information which might be of use to actions, however States must
define and utilize two primary attributes which are of core necessity:
is_operating and result. Each are defined as True, False, or None. result
is fairly generic and its meaning depends upon the context of the observable
that the state is coming from. is_operating can be False in cases where
something has gone wrong, invalidating the result (for example, the network
dropped, so an observable cannot be obtain a result across the network).

As a piece of core code, it is not recommended that this class be modified.

Copyright 2012
Licensed under the Creative Commons Attribution Unported License 3.0
http://creativecommons.org/licenses/by/3.0/ 
'''

import copy

class State(object):
    '''
    State contains important attributes whose change could cause actions
    to be fired in response.
    All other attributes assigned to a State object will be copied and sent
    along to fired actions for further processing.
    '''

    def __new__(cls, is_operating=None, result=None, *args, **kwargs):
        '''
        is_operating and result can be set to True, False, None, or '*'.
        In the case where the special value '*' is used for either or both
        parameters, a collection (set) of States will be returned instead.
        The collection will represent a cross product of all combinations.
        '''

        # TODO support more special combinations than just '*', such as [TF]
        
        # If both attributes are passed without anything fancy, we do
        # nothing special.
        if is_operating in [True, False, None] and \
           result in [True, False, None]:
               return object.__new__(cls, is_operating, result, *args, **kwargs)

        # Prepare variables for consistent parsing
        if is_operating == '*':
            op_list = [True, False, None]
        else:
            op_list = [is_operating]
        if result == '*':
            res_list = [True, False, None]
        else:
            res_list = [result]

        # Create a series of objects expanding all possibilties in case of '*'
        return_objects = StateCollection()
        for op_item in op_list:
            # Ensure each element for is_operating is valid
            if op_item not in [True, False, None]:
                raise TypeError('Invalid type for State attribute: %s',
                                op_item.__class__)

            for res_item in res_list:
                # Ensure each element of result is valid.
                if res_item not in [True, False, None]:
                    raise TypeError('Invalid type for State attribute: %s',
                                    res_item.__class__)

                # Create a new State object
                state_object = object.__new__(cls, op_item, res_item, *args, **kwargs)
                # Python will not automagically  call __init__ at this point.
                state_object.__init__(op_item, res_item, *args, **kwargs)
                return_objects.add(state_object)

        # Each State object has been created and initialized.
        # Return the set of State objects instead of a State object.
        return return_objects

    def __init__(self, is_operating=None, result=None, *args, **kwargs):
        '''
        Construct a State object with is_operating and result primary
        attributes, which each must be one of True, False, or None.
        '''

        # Primary Attributes
        self.is_operating = is_operating
        self.result = result
        # TODO allow secondary attributes to be set on construction
        # TODO enable creation of secondary attributes outside of construction
        # Secondary Attributes stored in a dictionary.
        self.secondary_attributes = {}

    def __str__(self):
        '''
        State is sort of a collection, and in that sense, it makes sense to
        represent the objects contained within it.
        '''
        return self.__repr__() + "(" + str(self.is_operating) + "," + str(self.result) + ")" + str(self.secondary_attributes)

    def __eq__(self, other):
        '''
        Two states are equal if their primary attributes are the same.
        Secondary attributes are hangers-on for action use, but as they
        do not trigger actions, they are not considered here.
        '''

        # TODO make this fancier rather than hard coding the two attributes.
        try:
            return self.is_operating == other.is_operating and \
                   self.result == other.result
        except AttributeError:
            # The other object clearly does not follow the same format
            # so these two objects cannot be the same.
            return False

    def __or__(self, other):
        '''
        Union this State with the other thing into a StateCollection.
        '''
        return self.union(other)
    def union(self, other):
        '''
        Union this State with the other thing into a StateCollection.
        '''

        # Cast other into a StateCollection or insert it into one.
        otherSC = StateCollection(set([other]))
        # Insert self into a StateCollection
        selfSC = StateCollection(set([self]))

        # Union the State Collections and return them.
        return selfSC | otherSC

    def copy(self):
        '''
        Return a new State object containing data copies, not references, to
        the internal data of this object. References to the data might change
        as the Observable modifies itself; it is not safe in a concurrent
        context.
        '''

        return copy.deepcopy(self)

    def primary(self):
        '''
        Returns primary attributes within a tuple for hashing purposes.
        '''
        return tuple([self.is_operating, self.result])

class StateCollection(set):
    '''
    StateCollection is a fancy wrapper around set so that a set of States can
    use the "in" and "not in" using the "eq" operator. By default, set uses
    the "is" operator. For use with States, it really only matters that the
    values match rather than performing specific object matching.
    '''

    def __contains__(self, item):
        '''
        The "in" operator will check for object equality first, followed by
        value equality. Either condition is sufficient to return True.
        '''

        # TODO determine if there is a faster or more efficient way to
        # perform this operation than a O(n) search.
        # (It seems unlikely without immutable and hashable objects...)
        # Parse each object in the set and see if the given item matches.
        for other_item in self:
            # Check identity first (faster), equality second (slower).
            if other_item is item or other_item == item:
                return True
        # If all items in the set have been parsed without returning True,
        # item is not in this set.
        return False

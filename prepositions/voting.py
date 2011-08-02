#### MEMORY-BASED SHALLOW PARSER ######################################################################

# Copyright (c) 2003-2010 University of Antwerp, Belgium and Tilburg University, The Netherlands
# Vincent Van Asch <vincent.vanasch@ua.ac.be>, Tom De Smedt <tom@organisms.be>
# License: GNU General Public License, see LICENSE.txt

### VOTING ###########################################################################################
# Functions to revote the output of TiMBL.
# Voting is used when TiMBL has multiple, equally good candidates (or none) for PP anchors.
# The functions take a list of tagged instances as input (see instances.py).

# Place of PP in the instances.
# This won't work if we change the instances!
_PPINDEX = 8

#-----------------------------------------------------------------------------------------------------
# A knowledge base.
# For base_candidate(), determines the kind of chunk to attach the preposition to.
# 0 = NP
# 1 = VP
# 2 = PP

majority_class = {
    u'vs.': 0, u'among': 1, u'because': 1, u'nearest': 2, u'over': 1, u'within': 1, u'near': 1, 
    u'past': 1, u'opposite': 2, u'as': 1, u'via': 0, u'through': 1, u'at': 1, u'in': 1, 
    u'notwithstanding': 1, u'throughout': 1, u'unto': 0, u'before': 1, u'by': 1, u'beyond': 1, 
    u'from': 1, u'for': 1, u'to': 1, u'until': 1, u'since': 1, u'except': 1, u'per': 0, u'than': 0, 
    u'beside': 1, u'till': 1, u'outside': 1, u'of': 0, u'en': 0, u'astride': 0, u'above': 1, 
    u'between': 0, u'out': 1, u'across': 1, u'pending': 1, u'versus': 0, u'alongside': 1, u'around': 1, 
    u'behind': 1, u'atop': 1, u'de': 0, u'upon': 1, u'v.': 0, u'underneath': 1, u'next': 1, u'if': 0, 
    u'but': 0, u'besides': 1, u'despite': 1, u'during': 1, u'along': 1, u'on': 1, u'with': 1, 
    u'below': 1, u'after': 1, u'down': 1, u'about': 1, u'save': 0, u'off': 1, u'like': 1, u'unlike': 1, 
    u'whether': 1, u'amid': 1, u'into': 1, u'including': 0, u'up': 1, u'against': 1, u'worth': 1, 
    u'while': 1, u'without': 1, u'plus': 0, u'aboard': 1, u'though': 2, u'amongst': 1, u'under': 1, 
    u'beneath': 1, u'toward': 1, u'onto': 1, u'inside': 1, u'towards': 1, u'expect': 1
}

#--- LOWEST ENTROPY ----------------------------------------------------------------------------------

def lowest_entropy(instances):
    """ Retags the tagged instances in the given list using lowest entropy. 
        Uses only the instances that give an anchor.
    """
    lowest = None
    anchor = None
    for i, instance in enumerate(instances):
        if not instance.predicted.startswith('n-'):
            entropy = instance.entropy
            if lowest is None:
                lowest = entropy
            if entropy <= lowest:
                anchor = i
                lowest = entropy
            # Set the prediction to zero (we'll set the anchor when we leave the loop).
            instance.change_prediction('n-'+instance.predicted)
    instances[anchor].change_prediction(instances[anchor].predicted[2:])
    return instances

#--- HIGHEST ENTROPY ---------------------------------------------------------------------------------

def highest_entropy(instances):
    """ Retags all instances.
        Takes the instance with the highest entropy to be the one defining the anchor. 
        This is a substitute for base_candidate().
    """
    highest = None
    anchor = None
    for i, instance in enumerate(instances):
        entropy = instance.entropy
        if highest is None:
            highest = entropy
        if entropy >= highest:
            anchor = i
            highest = entropy
    # Set the anchor (we should have all instances negative at the input).
    instances[anchor].change_prediction(instances[anchor].predicted[2:])
    return instances

#--- BASE CANDIDATE ----------------------------------------------------------------------------------

def base_candidate(instances, heuristic=majority_class):
    """ Retags the tagged instances in the given list using baseline.
        Append to the nearest candidate in front of PP of correct genre (NP/VP/PP) according to heuristic.
        The heuristic is a precomputed dictionary with the most frequent anchor genre for every PP.
        If this fails just append to the nearest.
    """
    d1, a1 = None, None # The nearest anchor according to given heuristic.
    d2, a2 = None, None # The nearest anchor in front of PP.
    d3, a3 = None, None # The nearest positive anchor that is a verb.
    d4, a4 = None, None # The nearest anchor that is a verb.
    d5, a5 = None, None # The nearest anchor behind PP.
    # Get the PP.
    # Note: this won't work if we change the instances, unless you correctly set _PPINDEX.
    pp = instances[0].instance.split()[_PPINDEX].lower()
    anchor_type = heuristic.get(pp, 0)
    typemap = {'NP':0, 'VP':1, 'PP':2} # Translate types into integer types.
    
    for i, instance in enumerate(instances):
        # Set the prediction to zero (we'll set the anchor later).
        if not instance.predicted.startswith('n-'):
            instance.change_prediction('n-'+instance.predicted)
        # Get the distance between the anchor and the PP:
        d = int(instance.instance.split()[2])
        if d1 is None: d1 = d
        if d2 is None: d2 = d
        if d3 is None: d3 = d
        if d4 is None: d4 = d
        if d5 is None: d5 = d
        # Determine the anchor candidate.
        if d > 0 and d <= d2:
            a2, d2 = i, d # Anchor is in front of PP.
        if d > 0 and d <= d3 and instance.instance.type == 'vp':
            a3, d3 = i, d # Anchor is in front of PP and is a VP.
        if abs(d) <= abs(d4) and instance.instance.type == 'vp':
            a4, d4 = i, d # Anchor is a VP.
        if abs(d) <= abs(d5):
            a5, d5 = i, d # Anchor is after PP.
        if d < 0:
            # Don't take anchors behind the PP into account.
            continue
        # Translate the type into a integer type.
        genre = typemap[instance.instance.type]
        if anchor_type == 0 and instance.instance.type in (0, 2) and d < d1:
            # If it's the correct type and it's nearer, take as anchor.
            # If we are searching for a NP also append to PP's.
            d1, a1 = d, i
        elif genre == anchor_type and d < d1:
            # If it's the correct type and it's nearer, take as anchor:
            d1, a1 = d, i
            
    if a1 is not None:
        # Use the heuristic candidate.
        instances[a1].change_prediction(instances[a1].predicted[2:])
    elif a2 is not None:
        # Use the nearest candidate in front of PP.
        instances[a2].change_prediction(instances[a2].predicted[2:])
    elif a3 is not None:
        # Use the nearest VP candidate in front of PP.
        instances[a3].change_prediction(instances[a3].predicted[2:])
    elif a4 is not None:
        # Use the nearest VP candidate to the PP.
        instances[a4].change_prediction(instances[a4].predicted[2:])
    else:
        # Use the nearest candidates after the PP.
        instances[a5].change_prediction(instances[a5].predicted[2:])
    return instances
# -*- coding: utf-8 -*-
"""
proudly developed in the studios of WDRT, Viroqua, Wisconsin

#NOTE: Changes to this file need to be saved to 'SpinPapiLib.py'
v0.1 - June 30
    functionality: gets JSON data from SpinPapi & converts to a python nested dict
    
v0.2 - July 9
    python dict is pickled in two versions : (a) unmolested, and (b) stuff I don't 
    want is stripped out (results dict is kept, success & request dicts are 
    stripped out)
    
v.0.3 - July 9
    SpinPapiTest is now separated from SpinPapiClient
    
v.0.4 - Nov 23 - Added notes on desired dict elements to add

v.0.5 - Nov 27 2015 - Added desired dict elements; Sched2 = schema #2

v.0.6 - Dec 6 2015 -

"""
'''
print type(show) #a show is a dict of show attributes
print type(day)  #a day is a key (of type string) for dict of shows
print type (Sched[day]) #key=day, value = list of shows
            
current Dict structure: (LookAtPickle.py for more insight)
all keys: type = string
all values type = string, unless otherwise specified
Day
    Show
        Scheduled (boolean)
        ShowDescription
        ShowID  
            ??Can I find other instances of the same show on diff days, based on ShowID?
        Weekdays 
            ??Does Monday view block a full list of days that a show plays??
        OnairTime
        OffairTime
        ShowUrl
        ShowCategory
        ShwowUsers [{UserID:,DJName:}]
        ShowName
        
elements to add to Show dict: 
    #these have been added to Sched2.pkl 11/28/2015
        StartRecDelta
            negative is earlier, positive is later
            hour: minute format, with plus or minus prefix
            default to zero, since shows seem to be either on time or late
        EndRecDelta
            negative is earlier, positive is later
            hour: minute format, with plus or minus prefix
            default to +5 to catch end of overrunning shows
                or default to start plus 4 hours for DRMC regulations
        Folder
            file folder location to put mp3/ogg archive file
        Subshow - boolean
            True if show is a segment within another show
            This will prevent SchedLinter from posting an error
            for double-booked shows
            
further elements *have* been added to Show dict:
        AlternatingSchedule (boolean)
            Set to True if different shows alternate during the same time slot
            example: Sonic Landscapes / Chris & Larry Show
            (1) Alternate Week
                Even/Odd
            (2) Week of the Month
                List of integers from the set 1-5, representing weeks of the month
        MultiDay (boolean)
            Set to True if show plays more than once in the same week
            
'''
from operator import itemgetter
import SpinPapiClient as Papi
import requests
#import simplejson as json
import json
import pickle
import copy

import glob
import os

import local
import key
import admin #cuz I'm crazy
from myClasses import SchedInfo, NegOne, CurrentTime, ShowTempTime

tab = '  '


def uniFix(uniStr):
    '''
    hack to replace common unicode characters that do not have an 
    ascii equivalent
    code lifted from here:
        http://www.intelligent-artifice.com/2010/02/how-to-filter-out-common-unwanted-characters-in-python.html
    presentation:
        http://farmdev.com/talks/unicode/
    '''
    text = uniStr
    character_replacements = [
    ( u'\u2018', u"'"),   # LEFT SINGLE QUOTATION MARK
    ( u'\u2019', u"'"),   # RIGHT SINGLE QUOTATION MARK
    ( u'\u201c', u'"'),   # LEFT DOUBLE QUOTATION MARK
    ( u'\u201d', u'"'),   # RIGHT DOUBLE QUOTATION MARK
    ( u'\u201e', u'"'),   # DOUBLE LOW-9 QUOTATION MARK
    ( u'\u2013', u'-'),   # EN DASH
    ( u'\u2026', u'...'), # HORIZONTAL ELLIPSIS
    ( u'\u0152', u'OE'),  # LATIN CAPITAL LIGATURE OE
    ( u'\u0153', u'oe')   # LATIN SMALL LIGATURE OE
    ]
    for (undesired_character, safe_character) in character_replacements:
         text = text.replace(undesired_character, safe_character)
    return text


            
def dictPrint (D,indent):
    '''
    recursively print the whole damn dictionary
    TODO:
        key and value of dict need to be handled differently
 
    '''

    if type(D) == dict:
        for el in D:
            print (indent * ' ') + '{';
            dictPrint(D[el],indent+3)
            print '}'
    if type(D) == list:
        for el in D:
            print(indent * ' ') + '[';
            dictPrint(el, indent+3)
            print ']'
    if type(D) == str:
        print D;
    elif type(D) == unicode:
        print uniFix(D);
    else: #maybe int, float, or bool???
        print str(D)
       
            
            

def myGetDay(day):
    '''
    use SpinPapi to load a day from Spinitron
    day = integer from 0 to 7
        0 = Sunday
        1 = Monday ...
    returns a dict
    SchedScrub is used to keep 'results' and strip 'request' and 'success'
    '''
    client = Papi.SpinPapiClient(key.userid, key.secret)
    print 'MGD.day -> ', str(day),' -> ', Days[day]
    r = requests.get(client.query({'method': 'getRegularShowsInfo', 'station': 'wdrt', 'When': str(day)}))
    #r = requests.get(Papi.client.query({'method': 'getRegularShowsInfo', 'station': 'wdrt', 'When': str(day)}))
    d = json.loads(str(r.text))
    success = d['success']
    
    return d, success
    
def myGetSchedule(days):
    '''
    get sched from Spinitron
    days is a dict {int (0-7) day(Sunday back to Sunday) : list/dict of shows
    	during that day} 
    
    #TODO research to see if there are two copies of Sunday
    
	
    '''
    print "--------------------------"
    print "myGetSchedule()------------"
    success = True
    mySchedule = {}
    errMsg = ''
    for i in days:
        print days[i]
        mySchedule[days[i]], tmpSuccess = myGetDay(i)
        if tmpSuccess == False:
            success = False
            errMsg = ''.join((i, ' -> Failure\n'))
    print errMsg
    return mySchedule, success
    
def SchedScrub(ScheduleDict):
    '''
    accept output from myGetSchedule (SpinPapi schedule converted to
        dict format)
    return schedule with unwanted crap removed, i.e.: remove  "request" 
        and "success" elements of original day schedules and keep
        "results"
    '''
    mySched = {}
    for day in ScheduleDict:
        mySched[day] = ScheduleDict[day]['results']
    return mySched
    
def PickleDump (f,d, dumpPath = local.pklDestPath):
    '''
    d is a nested dict containing one week of schedules
    actually, d can be about any damn thing
    f = string containing name of Schedule Pickle (.pkl included)
    dumpPath = string: absolute path (trailing backslash included)
        to destination folder to place .pkl files
    '''


    f = dumpPath + f
    F = open(f, 'wb')
    pickle.dump(d,F)
    F.close()
    
def OpenPickle(SchedulePickle, srcFolder = local.pklSourcePath ):
    '''
    SchedulePickle = string that contains name of .pkl file, no path
        prepended!
    srcFolder = string: absolute path to folder that contains pickle files
        trailing backslash included
    returns serialized schedule, or any other pickled object
    note:
        the terms 'serialized' and 'saved to disk' are synonymous with pickled
    '''
    #print 'SchedulePickle -> '+SchedulePickle
    #print 'srcFolder -> '+srcFolder
    
    F = open(srcFolder + SchedulePickle, 'rb')
    return pickle.load(F)
    
def newestPickle(path = local.pklSourcePath):
    '''
    returns string containing path + file name of newest pickle
    in the 'path'
    typical parameters for this function:
    path = local.pklDestPath
    path = local.pklSourcePath
    '''

    #newest file of any file type ...
    #dud = max(os.listdir(os.getcwd()), key = os.path.getctime)
    
    #newest file of type *.pkl
    os.chdir(path)
    NP = max(glob.iglob('*.[Pp][Kk][Ll]'), key =os.path.getctime)
    #print 'Newest Pickle ->', NP
    return NP

class day(object):
    '''
    a day is a dict of show objects
    key is an integer, shows to be sorted by start time
    
    '''
    def  __init__(self, Schedule):  
        self.showDict = {}
        
class show(object):
    '''
    a show is a dict of show attributes
    '''
    def __init__(self, aShow):
        '''
        myShow =
        
        '''
        pass
    
    def BuildShowDict(Schedule):
        '''
        take a week's (scrubbed) schedule
        and return a dict of show objects
        '''
        pass
    

def BuildDJList(Schedule):
    '''
    take a week's  schedule
    and return a *list* of DJs
    list is sorted by UserID
    each DJ is a 2 element dict
        UserID = unique int
        DJName = unique string
    '''
    def GrabShowUsers(aShow):
        '''
        within a show, grab both elements of a ShowUser dict
        and add them to the UserIDList and the DJNameList
        '''
        for User in aShow['ShowUsers']:
            if User['UserID'] not in UserIDList:
                if User['DJName'] in DJNameList:
                    print; print; print 'ERROR DJName list not one-to-one!!!!'; print
                else: #new User to add to lists
                    UserIDList.append(User['UserID'])
                    DJNameList.append(User['DJName'])
            else: #UserID already is in list
                if User['DJName'] not in DJNameList:
                    print User['DJName']
                    print 'ERROR UserID in list, but not DJName?!?!'; print
    
    DJList = []
    UserIDList = []
    DJNameList = []
    
    for day in Schedule:
        #sort shows by start time
        Schedule[day] = sorted (Schedule[day], key=itemgetter('OnairTime'))
        for show in Schedule[day]:
            GrabShowUsers(show) 
            
        
    for user, dj in zip(UserIDList, DJNameList):
        #print str(user) + '   ' +  dj
        DJList.append({'UserID':user,'DJName':dj})
        DJList = sorted(DJList, key = itemgetter('UserID'))
    return DJList
    
def OverLap(Schedule):
    '''
    return a dict of slots with overlaps
    key = Day/Start/End
    value = list( Day, Start, End,list (Shows) )
    partial overlaps will confuse this algorithm
    '''
    pass

def PrintAShow(Show):
    '''
    A show is a dict?
    '''
    print type(show)
    

def dudFunc(day):
    '''
    used by TraverseShows as a default action of doing nothing
    '''
    pass

def addShowAttrFunc(aShow, CTobj):
    '''
    This function adds,  the ShowTempTime object to aShow, by attaching
    it to aShow['TempTime']
    use this with TraverseShows3()
    CTobj is instantiated Current Time object
    '''
    aShow['TempTime'] =ShowTempTime(aShow, CTobj)

def myPrint(anObject):
    '''
    kind of a hack
    '''
    print anObject
    

def PrettyPrintShow(show):
    '''
    can be used in conjunction with TraverseShows to print formatted schedule
    '''
    tab = '   '
    print tab + show['ShowName']
    print tab + tab + show['OnairTime']+ tab +show['OffairTime'] 
    
def PrettyPrintShow2(show):
    '''
    a show is a dict, of course
    can be used in conjunction with TraverseShows to print a more
    complete formatted schedule
    '''
    #don't apply uniFix to the "other" object types
    otherTypes = [bool, int, SchedInfo, list, dict, ShowTempTime]
    localTypes = [SchedInfo, ShowTempTime]
    tab = '   '
    dubTab = '      '
    print tab , show['ShowName']
    for el in show:
        #print el
        if type(show[el]) not in otherTypes:
            print tab, tab, el, '-> ', str(uniFix(show[el]))
            #pass
        elif type(show[el]) not in localTypes:
            print tab, tab, el, '-> ', str(show[el])
            #pass
        elif el != 'ShowUsers':
            print dubTab, el, '->\n', str(show[el])
            #pass
        else:
            print el
            for i in range[0:20]:
                print 'xxxxxxxxxxx ShowUsers????xxxxxxxxxxxx'
            for crap in show[el]:
                print dubTab,crap['DJName']
        #TODO: Modify PrettyPrintShow2 to accept multiline strings for local
            #classes and indent properly

    
def AdminPrintShow(show, x):
    '''
    Used in conjunction with TraverseShows*2* to print formatted schedule
    by admin.selectShow()
    '''
    tab = '   '    
    print ('<'+ x + '>' + tab + show['ShowName']),
    print (show['OnairTime'] + tab + show['OffairTime'])  

def PrettyPrintNewFields(show):
    '''
    can be used in conjunction with TraverseShows to print formatted schedule
    '''
    tab = '   '    
    print (tab + show['ShowName'])
    print (tab+tab + show['OnairTime'] + tab + show['OffairTime']) 
    print (tab+tab + str(show['StartRecDelta']) + tab + str(show['EndRecDelta']) )

def makeChronological(Schedule):
    '''
    accepts a Schedule
    for each day in Scedule, put shows in chronological order, based on
        OnairTime
    returns sorted Schedule as described above
    '''
    for day in Schedule:
        Schedule[day] = sorted (Schedule[day], key=itemgetter('OnairTime'))
    return Schedule
    
def TraverseShows (Schedule, showFunc = dudFunc, dayFunc = dudFunc):
    '''
    showFunc will execute once everytime we get to a show during
        the traversal
    dayFunc will execute once everytime we get to a day during the traversal
    showFunc is a function that accepts a show as a parameter
    NOTE: If a show occurs on 5 different days, TraverseShows will go
        to each day instance of that show separately
    '''
    for day in Schedule:
        dayFunc (day)
        #sort shows by start time
        Schedule[day] = sorted (Schedule[day], key=itemgetter('OnairTime'))
        for show in Schedule[day]:
            showFunc(show)    

def TraverseShows3 (Schedule, CTobj, showFunc = addShowAttrFunc, dayFunc = dudFunc):
    '''
    The main point of this version of TraverseShows is to add the ShowTempTime 
    object to each show in the schedule.  I should really refactor and rename
    for the sake of cleaner code ...
    showFunc defaults as AddShowAttrFunc, accpeting show and CurrentTime object
        as parameters
    NOTE: If a show occurs on 5 different days, TraverseShows will go
        to each day instance of that show separately
    '''
    for day in Schedule:
        dayFunc (day)
        #sort shows by start time
        Schedule[day] = sorted (Schedule[day], key=itemgetter('OnairTime'))
        for show in Schedule[day]:
            showFunc(show, CTobj)  
            
def TraverseShows2 (Schedule, showFunc = dudFunc, dayFunc = dudFunc):
    '''
    just like TraverseShows, but NOW with added ENUMERATION!!!!
    showFunc will execute once everytime we get to a show during
        the traversal
    dayFunc will execute once everytime we get to a day during the traversal
    showFunc is a function that accepts a show as a parameter
    NOTE: If a show occurs on 5 different days, TraverseShows will go
        to each day instance of that show separately
    '''
    for day in Schedule:
        dayFunc (day)
        #sort shows by start time
        Schedule[day] = sorted (Schedule[day], key=itemgetter('OnairTime'))
        for (x,show) in enumerate(Schedule[day]):
            showFunc(show,str(x+1))  
    
def FreshPapiOld():
    '''
    This function
    uses SpinPapi to grab a fresh copy of the weekly schedule
    and save two pickled versions
    SpinSchedule is the schedule obtained from Spinitron via SpinPapi
    SchedulePickle1 is the cleaned up version of SpinSchedule
    Schedule1 replaces mySchedule
    In another function, SchedulePickle2 will take SpinSchedule1 
        and add further desired fields
        
    #TODO  make accomodations to make new pickle and not overwrite old
    '''
    
    Days = { 0: 'Sunday' , 1 : 'Monday' , 2 : 'Tuesday' , 3 : 'Wednesday' ,
            4 : 'Thursday' , 5 : 'Friday' , 6 : 'Saturday'}
            
    #SpinSchedulePickle contains an unadulterated copy of the schedule
    #as obtained from Spinitron via SpinPapi
    SpinSchedulePickle = 'SpinSchedule.pkl'
        
    Schedule1Pickle = 'Schedule1.pkl'
    #mySchedulePickle = 'mySchedule.pkl' 
        #this is old version of Schedule1Pickle
        #myShedulePickle should still be on file ...

    #TODO  make accomodations to make new pickle and not overwrite old
    SpinScheduleDict,success = myGetSchedule(Days)
    print 'New Schedule obtained from Spinitron'
    
    #save unadulterated data from SpinPapi to Pickle
    #current directory as it now stands
    PickleDump(SpinSchedulePickle, SpinScheduleDict)
    
    #strip off data I don't care about
    ScheduleDict1 = SchedScrub(SpinScheduleDict)
    print 'Schedule1 saved as ',Schedule1Pickle
    #save scrubbed data to a second Pickle file
    PickleDump(Schedule1Pickle, ScheduleDict1)
    
def enchilada():
    '''
    create new
    '''

def FreshPapi(NewSched ='today'):
    '''
    This function
    (1) use SpinPapi to grab a fresh copy of the weekly schedule
    (2) strip extra Requests fields
    #note: NewSched isn't being used for anything
    
    Sched2 = Sched1 + local schema bolted on 
    returns a schedule as Sched2, no metafication yet
    '''
    
    Days = { 0: 'Sunday' , 1 : 'Monday' , 2 : 'Tuesday' , 3 : 'Wednesday' ,
            4 : 'Thursday' , 5 : 'Friday' , 6 : 'Saturday'}
    
    #get raw schedule from SpinPapi
    SpinScheduleDict,success = myGetSchedule(Days)
    if success:
        print 'New Schedule obtained from Spinitron'
        
        #take SpinPapi schedule & strip extra Requests fields (keep)
        ScheduleDict1 = SchedScrub(SpinScheduleDict)
        
        Sched2 = Sched1toSched2(ScheduleDict1)
        return Sched2
    else:
        print 'SpinPapiLib.FreshPapi -> error!!!'
        return

def FreshPapi1 ():
    '''
    This function
    (1) use SpinPapi to grab a fresh copy of the weekly schedule
    (2) strip extra Requests fields
    
    returns a schedule as Sched1, no metafication yet
    Sched1 doesn't have any local schema bolted on
    as of May 2016, WeeklyCron.py doesn't need (or want) a metafied schedule
    '''

    Days = { 0: 'Sunday' , 1 : 'Monday' , 2 : 'Tuesday' , 3 : 'Wednesday' ,
            4 : 'Thursday' , 5 : 'Friday' , 6 : 'Saturday'}


    #single day sched for testing purposes
    #Days = { 2 : 'Tuesday' }   
    
    #get raw schedule from SpinPapi
    sched, success = myGetSchedule(Days)
    if success:
        print 'New Schedule obtained from Spinitron'
        
        #take SpinPapi schedule & strip extra Requests fields (keep)
        sched1 = SchedScrub(sched)
        #simple schedule doesn't need local schema bolted on to shows ...
        #Sched2 = Sched1toSched2(ScheduleDict1)
        return sched1
    else:
        print 'error retrieving schedule from Spinitron!!!!'
        print 'FreshPapi1'
        return
    
def Sched2toSched3(Sched2):
    '''
    This function does the following:
    (1) set CurrentTime if it hasn't been set yet - this is a precondition for 
        initializing ShowTempTime
    (2) then attach a ShowTempTime object to each show:
        sh
    returns updatedSched(Sched3), currentTimeObject(charlieTime)
    TODO: Not sure if deepcopy is necessary here, maybe it will come back to
        bite me ???
    '''

    #instantiate charlieTime, but only if it hasn't been instantiated yet
    try:
        dud = CurrentTime.initialized
        if dud != True:
            charlieTime = CurrentTime(CurrentTime.CTnow)
    except:
        charlieTime = CurrentTime(CurrentTime.CTnow)
    
    #for each show, add ShowTempTime attributes
    for day in Sched2:
        for show in Sched2[day]:
            try:  #I don't have it in me to individually test each attribute
                #of the ShowTempTime object right now
                dud = show['TempTime']
            except:
                show['TempTime'] = ShowTempTime(show,charlieTime)
                
    Sched3 = Sched2
    return Sched3, charlieTime
    #where to save this totally new, up-to-date sched?
    
def Sched1toSched2(Sched):
    '''
    This function accepts a schedule (in the format that SchedScrub() creates
    and adds the following elements to each show

        add the following fields to a show dict:
            StartRecDelta (int)
                negative is earlier, positive is later
                denominated in minutes
                default to zero, since shows seem to be either on time or late
            EndRecDelta (int)
                negative is earlier, positive is later
                denominated in minutes
                default to +5 to catch end of overrunning shows
                    ??? or default to start plus 4 hours for DRMC regulations
            Folder (string)
                file folder location to put processed mp3/ogg archive file
            Subshow (boolean)
                True if show is a segment within another show
                This will prevent SchedLinter from posting an error
                for double-booked shows
        NOTE: admin.batchShowUpdate() duplicates the functionality of Sched1toSched2
    '''
    x=1
    #make deepcopy
    tempSched = copy.deepcopy(Sched)
    #traverse tempSched and add show fields to sched
    #TraverseShows(tempSched,Add2Show)
    for day in tempSched:
        x=1
        #sort shows by start time
        Sched[day] = sorted (Sched[day], key=itemgetter('OnairTime'))
        tempSched[day] = sorted(tempSched[day], key=itemgetter('OnairTime'))
        for show in tempSched[day]:
            '''
            print type(show) #a show is a dict
            print type(day)  #a day is a key (of type string) for dict of shows
            print type (Sched[day]) #key=day, value = list of shows
            '''
            try:
                myStart = show['StartRecDelta']
            except:
                show['StartRecDelta'] = 0  
                
            try:
                myEnd = show['EndRecDelta']
            except:
                show['EndRecDelta'] = 5
                
            try:
                myFolder = show['Folder']
            except:
                show['Folder'] = None
                
            try:
                mySubshow = show['Subshow']
            except:                
                show['Subshow'] = False 
            
            try:
                myVerified = show['Verified']
            except:
                show['Verified'] = False
            
            addSchedInfo(show)
            
    return tempSched
            
            
#MAIN
#I pulled the following variable declarations out of the __main__ conditional
#since these variables may be needed by other code calling into this module
            
tab = '\t'        
Days = { 0: 'Sunday' , 1 : 'Monday' , 2 : 'Tuesday' , 3 : 'Wednesday' ,
        4 : 'Thursday' , 5 : 'Friday' , 6 : 'Saturday'}
testDays = { 0: 'Sunday' , 1 : 'Monday' }

#key.py should be obtained locally, not available from repository
client = Papi.SpinPapiClient(key.userid, key.secret)

if __name__ == '__main__':
    '''
    mySchedulePickle = 'Sched3.pkl'
    Sched3 = OpenPickle(mySchedulePickle)
    print 'Pickle Opened'
    '''
    
    '''
    Sched2 = Sched1toSched2(Sched1)
    print; print 'Sched2: '+ str(Sched2)
    PickleDump('Sched2.pkl', Sched2)
    '''
    
    #################################################################
    # grab newest pickle
    #################################################################
    dud = local.pklSourcePath
    print dud
    
    current = os.getcwd()
    newestSched = OpenPickle(newestPickle(local.pklSourcePath))
    newestSched, comment, timestamp = admin.demetafy(newestSched)
    os.chdir(current)

    #print tabbed version of weekly shedule
    TraverseShows(newestSched,PrettyPrintNewFields, myPrint)
    print; print type(newestSched)
    print type(newestSched['Monday'])

    
    '''
    for i in 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx':
        print
    dictPrint (Sched['Monday'], 3)
    '''
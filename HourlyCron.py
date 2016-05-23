# -*- coding: utf-8 -*-
"""
Created on Wed May 11 15:58:25 2016

@author: lmadeo

hourlyCron.py

#TODO: define CharlieSched format:
    dict of days, keys = fullDayString
        value is a dict
            keys = OffairTime-OnairTime (ex: '08:00:00-06:00:00' )
                OffairTime: 08:00:00
                OnairTime:
example:                
{'Tuesday': {u'08:00:00-06:00:00': 
	{'OffairTime': u'08:00:00', 
	'ShowList': [u'DriftlessMorning'], 
	'Archivable': True, 
	'OnairTime': u'06:00:00'}
     }
}

# FIRST, MOST BASIC ITERATION
-----------------------------

* Grab startDelta and endDelta from local.py

* Open most recent charlieSched in folder specified in local.py

* Build list of shows that ended in last hour
    #note this should be a two hour delay to enable tacking on of endDelta

* For each show in list:
    * build mp3 using pysox
    * send "new.mp3" to correct folder on webserver, using scp
    * Using scp, mv "new.mp3" to "current.mp3"
    
    
# FINE TUMING / FURTHER ITERATION
---------------------------------

* Error checking:
    *target folder exists? If not, create, and log an error
    *local autocharlie folder exists?  If not, create folder, then kick off
        WeeklyCron job
    
* Does loaded charlie sched encompass all 7 days of week?

#TODO: Fix that Chris & Larry show is in ShowList, but not Sonic Landscapes
"""

def getCharlieSched():
    '''
    returns newest charlieSched from key.charlieSched
    '''
    #save current working dir
    current = os.getcwd()
    charlieSched = SPlib.OpenPickle(SPlib.newestPickle(local.charlieSchedPath), 
                                    local.charlieSchedPath)
    #return to current working dir
    os.chdir(current)
    return charlieSched
    
def getCurrentTime():
    '''
    returns:
        LastHour(int (0 .. 23))
        fullDayString
    uses relative delta, so 1am minus two hours is 11pm, previous day
    '''
    Now = DT.datetime.now() + relativedelta(hour=0, minute=0, second=0, microsecond=0)
    ThisHour = DT.datetime.now() + relativedelta( minute=0, second=0, microsecond=0)
    print  'GT.ThisHour -> ',str(ThisHour)
    # if end of archive will spill over into next hour, wait an hour before 
    # building archive, otherwise you will be grabbing 60 mon audio archives 
    # that don't exist yet
    if endDelta > 0:
        LastHourRaw = ThisHour + relativedelta(hours = -2)
    else:
        LastHourRaw = ThisHour + relativedelta(hours = -1)        
    print 'GT.LastHourRaw -> ', str(LastHourRaw)
    print 'GT.LastHour.weekday() -> ', str(LastHourRaw.weekday())
    today = num2day[LastHourRaw.weekday()]
    print 'GT.today -> ', str(today)

    timeTuple = str(LastHourRaw).split(':')[0]
    LastHour = int(timeTuple.split(' ')[1])
    #print LastHour
    return LastHour, today
    
def day2spinDay(fullDayStr, hour):
    '''
    adjust for the fact that Spinitron day starts at 6am instead of midnight
    accepts full day name string
    returns adjusted full day name string
    #TODO: does this need to be implemented in datetime module???
    '''
    day2num = {'Monday':0, 'Tuesday':1, 'Wednesday':2, 'Thursday':3,
           'Friday':4, 'Saturday':5, 'Sunday':6}
    num2day = { 7: 'SaturdayAFTER', -1: 'Sunday' , 0 : 'Monday' , 
            1 : 'Tuesday' , 2 :'Wednesday',  3 : 'Thursday' , 
            4 : 'Friday' , 5 :'Saturday', 6 : 'Sunday'}
    if hour < 7:
        yesterday = num2day[((day2num[fullDayStr] - 1) % 7)]
        fullDayStr = yesterday
    return fullDayStr
    
def spinDay2day(spinDay, hour):
    '''
    converts spinitron day to real day, which only happens between
    midnight and 6am
    accepts:
        spinDay: full string day, with day ending @ 6am
        hour: int (0 .. 23) = this is the hour that the show ends
    returns:
        day string, adjusted back from spinday to realday
    '''
    day2num = {'Monday':0, 'Tuesday':1, 'Wednesday':2, 'Thursday':3,
           'Friday':4, 'Saturday':5, 'Sunday':6}
    num2day = { 7: 'SaturdayAFTER', -1: 'Sunday' , 0 : 'Monday' , 
            1 : 'Tuesday' , 2 :'Wednesday',  3 : 'Thursday' , 
            4 : 'Friday' , 5 :'Saturday', 6 : 'Sunday'}  
    realDayStr = spinDay
    if hour < 7:
        realDayStr = num2day[((day2num[spinDay] + 1) % 7)]
    return realDayStr
    
def spinDay22day(spinDay, time):
    '''
    better spinDay2day
    converts spinitron day to real day, which only happens between
    midnight and 6am
    accepts:
        spinDay: full str day, with day ending @ 6am
        time: in datetime.time format (this is the time the show ends)
    returns:
        *date* in datetime.date format (???)
        perhaps other formats, if it is discovered that these are needed
    '''
    day2num = {'Monday':0, 'Tuesday':1, 'Wednesday':2, 'Thursday':3,
           'Friday':4, 'Saturday':5, 'Sunday':6}
    num2day = { 7: 'SaturdayAFTER', -1: 'Sunday' , 0 : 'Monday' , 
            1 : 'Tuesday' , 2 :'Wednesday',  3 : 'Thursday' , 
            4 : 'Friday' , 5 :'Saturday', 6 : 'Sunday'}  
    cutoff = DT.time(6, 0, 0)
    realDayStr = spinDay
    if not(time > cutoff):
        realDayStr = num2day[((day2num[spinDay] + 1) % 7)]
    return realDayStr        
    
def getShows2Archive (sched, LastHour, spinDay):
    '''
    accepts:
        sched = schedule in CharlieSched format
        LastHour int in range from 0 ..23
        spinDay = full string day name, spinDays end @ 6am
    returns:
        a list of all shows that ended during the last hour,
    '''
    retList = []
        
    for show in sched[spinDay]:
        #print
        #print 'GS2A show -> ',str(show)
        #print 'GS2A sched[day][show] -> ', str(sched[day][show])
        showHour = int(str(sched[spinDay][show]['OffairTime']).split(':')[0]) 
        #showHour = int(str(show['OffairTime']).split(':')[0])
        if showHour == LastHour:
            retList.append(sched[spinDay][show])
    return retList   
    
def strTime2timeObject(strTime):
    '''
    accepts:
        strTime: string in this format: "00:00:00"
    returns:
        datetime.time object (hours, minutes, seconds, no date info)
    '''
    #below code is inefficient.  Oh well
    myHour = int(str(strTime).split(':')[0])
    myMin = int(str(strTime).split(':')[1])
    mySec = int(str(strTime).split(':')[2])
    DTtime = DT.time(myHour, myMin, mySec)
    return DTtime   

def mytime2DT(time, day):
    '''
    all "time math" needs to happen in datetime or dateutil format
    accepts: 
        time: string in "00:00:00" format
        day: full string (ex: "Sunday")
    returns:
        time in datetime format
    '''
    myHour = int(str(time).split(':')[0])
    myMinute = int(str(time).split(':')[1])
    mySecond = int(str(time).split(':')[2])
    DTtime = DT.datetime.now() + relativedelta(hour=myHour, minute=myMinute,
             second=mySecond, microsecond=0)
    return DTtime

def numArchives(start,end):
    '''
    accepts:
        start, end: type = datetime.datetime
    '''
    partialEnd = False
    startHour = start.timetuple().tm_hour
    endHour = end.timetuple().tm_hour
    if start.timetuple().tm_mday != end.timetuple().tm_mday:
        endHour += 24
    numHours = endHour - startHour
    #partialEnd is True if the last archived hour to grab needs to have its 
        # end truncated
        # if show ends in the 59th minute, we consider show to end on the hour
    if end.timetuple().tm_min > 0 and end.timetuple().tm_min < 59:
        numHours +=1
        partialEnd = True
    return numHours, partialEnd
    
def buildArchiveList(show, spinDay):
    '''
    accepts:
        show in showsToArchive format
        spinDay: fullStrDay (ex: 'Sunday'), spinDay ends @ 6am
    returns:
        ArchiveList (a list of hour long archives that will be used to build
            mp3 archive for a particular show)
        Each element of the ArchiveList is a dict containing the following:
            'StartTime' : type = datetime.datetime.timetuple()
            'Delta': type = datetime.timedelta
    '''
    #determine start and end of show, with deltas added in
    startHour = strTime2timeObject(show['OnairTime'])
    print 'spinDay22day(spinDay, startHour) ->',
    print spinDay22day(spinDay, startHour)
    showStart = mytime2DT(show['OnairTime'],spinDay22day(spinDay, 
                          startHour)) + relativedelta(minutes=startDelta)
    endHour = strTime2timeObject(show['OffairTime'])
    showEnd = mytime2DT(show['OffairTime'],spinDay22day(spinDay, 
                          endHour)) + relativedelta(minutes=endDelta)

    print 'showStart -> ', str(showStart)
    print 'showEnd -> ', str(showEnd)
    print type(showEnd)
    print
    
    # if start time > end time, then show must stradle midnight hour
    if showStart > showEnd:
        # I think this will fix matters if a show straddles midnight
        # otherwise, maybe get a 24 hour + audio archive ?!?!
        showStart = showStart + relativedelta(days=-1)
        
    duration = showEnd - showStart
    duraSeconds = duration.seconds
    print 'duraSeconds -> ', duraSeconds

    print 'show duration: -> ', str(duration)
    print 'type(duration) -> ', str(type(duration))
    print 'showStart -> ', str(showStart)
    print 'showEnd -> ', str(showEnd)
    
    showHours, partialEnd = numArchives(showStart, showEnd)
    print showHours #start counting @ zero
    print range(showHours)
    partialOffset = 0
    if partialEnd:
        partialOffset = 1
    
    
    archiveList = []
    archiveElement = {}
    count = 0
    #if the show is an hour or less, does not stradle an hour, and doesn't end
        # at the end of an hour, this is an edge case ...
    if showHours == 1 and partialEnd == True:
        archiveElement['StartTime'] = showStart
        archiveElement['TimeDelta'] = showEnd - showStart
    
    else: #not an edge case
        # offset = time from beginning of show to end of first hour
            # ex: show starts at 2:15, offset is 45 minutes
        offset = (showStart + relativedelta(hours=+1, 
                            minute =0, second=0)) -showStart
          
        if count < showHours:
            archiveElement['StartTime'] = showStart
            archiveElement['TimeDelta'] = offset
            archiveList.append(archiveElement)
            count += 1
        
        while count + partialOffset < showHours: # working with a complete hour
            archiveElement = {}   
            archiveElement['StartTime'] = archiveList[-1]['StartTime'] + \
                            archiveList[-1]['TimeDelta']
            archiveElement['TimeDelta'] = DT.timedelta(seconds=3600)
            archiveList.append(archiveElement)
            count += 1
        
        if partialEnd:
            archiveElement = {}
            archiveElement['StartTime'] = archiveList[-1]['StartTime'] + \
                            archiveList[-1]['TimeDelta']
            archiveElement['TimeDelta'] = showEnd - archiveElement['StartTime']
            archiveList.append(archiveElement)
                                        
    return archiveList
    
        
def buildmp3(show, spinDay):
    '''
    accepts:
        show in showsToArchive format
        spinDay: fullStrDay (ex: 'Sunday'), spinDay ends @ 6am
    returns:
        an mp3 for archiving
    '''

    #each hour has a start and end time within the hour
        # convert start & end times to datetime format, add in time deltas
        
    #if len(archiveList) == 0:
        #errorNow = DT.datetime.now() + relativedelta(hour=0, minute=0, second=0, microsecond=0)
    #elif len(archiveList) == 1:
        #pick start & end points to create mp3Out
        #for this hour long archive, create start and end attributes
    #else (two or more archives to grab):
        #for first archive:
            #modify start attribute
        #for last archive in list:
            #modify end attribute
    pass


    
    
import os
import local
import key
import SpinPapiLib as SPlib

import datetime as DT
from dateutil.relativedelta import *
import calendar

import pprint

from subprocess import call
# example of sox and call usage:
    # http://ymkimit.blogspot.com/2014/07/recording-sound-detecting-silence.html

#num2day has been modified to align with date.weekday() RTFM
num2day = { 7: 'SaturdayAFTER', -1: 'Sunday' , 0 : 'Monday' , 
            1 : 'Tuesday' , 2 :'Wednesday',  3 : 'Thursday' , 
            4 : 'Friday' , 5 :'Saturday', 6 : 'Sunday'}
            
num2dayShort = { 7: 'SatAFTER', -1: 'SunBEFORE' , 0 : 'Mon' , 
            1 : 'Tue' , 2 :'Wed',  3 : 'Thu' , 
            4 : 'Fri' , 5 :'Sat', 6 : 'Sun'}
            
day2shortDay = { 'Monday' : 'Mon', 'Tuesday' : 'Tue', 
                'Wednesday' : 'Wed', 'Thursday': 'Thu', 'Friday': 'Fri',
                'Saturday': 'Sat', 'Sunday': 'Sun'}
                
day2num = {'Monday':0, 'Tuesday':1, 'Wednesday':2, 'Thursday':3,
           'Friday':4, 'Saturday':5, 'Sunday':6}
   

if __name__ == '__main__':
    
    tab = '    '
    pp = pprint.PrettyPrinter(indent=4)
    
    Now = DT.datetime.now() + relativedelta(hour=0, minute=0, second=0, microsecond=0)
    print 'Now -> ', str(Now)
    ThisHour = DT.datetime.now() + relativedelta( minute=0, second=0, microsecond=0)
    print 'ThisHour -> ', str(ThisHour)
    
    startDelta = local.startDelta
    endDelta = local.endDelta
    
    #grab most recentCharlieSched pickle out of designated folder
    charlieSched = getCharlieSched()
    #print charlieSched
    
    #LastHour is two hours ago if EndDelta is greater than zero
    LastHour, today = getCurrentTime()
    #adjust time to Spinitron time
    spinDay = day2spinDay(today, LastHour)
    print 'LastHour -> ', LastHour
    print 'today -> ', today
    print 'spinDay -> ', spinDay
    
    #======================================
    # make list of shows to archive
    #======================================
    #showsToArchive = getShows2Archive(charlieSched, LastHour, spinDay)
    #for testing purposes ...
    showsToArchive = getShows2Archive(charlieSched, 12, 'Friday')    
    print 'showsToArchive ->'
    print tab, str(showsToArchive)
    
    #================================================================
    # build mp3 for each show in list
    #================================================================
    for show in showsToArchive:
        # build mp3 using pysox
        archiveList = buildArchiveList(show, spinDay)
        pp.pprint(archiveList)
        # send "new.mp3" to correct folder on webserver, using scp
        # Using scp, mv "new.mp3" to "current.mp3"


        
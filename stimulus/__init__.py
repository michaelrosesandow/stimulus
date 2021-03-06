import time
from utils import secs_to_time


ALWAYS_FAST_MODE = True
SKIP_ALL_SLEEP = True

class Agent(object):
    _ID = 0
    def __init__(self, schedule):
        self.id = self._ID; self.__class__._ID += 1
        self.schedule = schedule
        self.status = 'logged_off'
        self.active_call = False
        self.handling_call = None

class AgentSchedule(object):
    _ID = 0
    def __init__(self, regular_start=28800, regular_end=(3600*16.5), regular_lunch=(3600*12), lunch_duration=1800, tz='America/Chicago'):
        self.id = self._ID; self.__class__._ID += 1
        self.regular_start = regular_start
        self.regular_end = regular_end
        self.regular_lunch = regular_lunch
        self.lunch_duration = lunch_duration
        self.tz = tz

class Day(object):
    _ID = 0
    def __init__(self, agents, calls):
        self.id = self._ID; self.__class__._ID += 1
        self.agents = agents
        self.calls = calls
        self.sl_threshold = 20
        self.sl_target = 0.90
        self.interval = 15 * 60 # 15 minutes

        self.sl_interval_dict = {}

    def offered_calls(self):
        return sum([call.status!='pre-call' for call in self.calls])

    def completed_calls(self):
        return sum([call.status=='completed' for call in self.calls])

    def active_calls(self):
        return sum([call.status=='active' for call in self.calls])

    def queued_calls(self):
        return sum([call.status=='queued' for call in self.calls])

    def abandoned_calls(self):
        return sum([call.status=='abandoned' for call in self.calls])

    def calls_within_sl(self):
        return sum([call.met_sl for call in self.calls])

    def service_level(self):
        return 1.0 * self.calls_within_sl() / max(0.1, self.offered_calls())

    def print_status_line(self):
        return (' offered: ' + str(self.offered_calls()) + ' queued: ' + str(self.queued_calls()) + ' active: ' + str(self.active_calls()) +
               ' completed: ' + str(self.completed_calls()) + ' SL: ' + "{0:.2f}%".format(100*self.service_level()) +
               ' aht: ' + str(self.aht())
               )

    def list_of_completed_calls(self):
        return [call for call in self.calls if call.status=='completed']

    def aht(self):
        try:
            return sum([call.duration for call in self.list_of_completed_calls()]) / len(self.list_of_completed_calls())
        except ZeroDivisionError:
            return '--'

class Call(object):
    _ID = 0
    def __init__(self, arrival_timestamp, duration):
        self.id = self._ID; self.__class__._ID += 1
        self.arrival_timestamp = arrival_timestamp
        self.duration = duration
        self.status = 'pre-call'
        self.queued_at = None
        self.answered_at = None
        self.queue_elapsed = None
        self.handled_by = None
        self.met_sl = False

def simulate_day(day):

    for i in range(3600*24):
        day.agents = agent_logons(day.agents, i)
        day.agents = agent_logoffs(day.agents, i)
        day.calls = queue_calls(day.calls, i)
        day = answer_calls(day, i)
        day = hangup_calls(day, i)
        day = abandon_calls(day, i)

        c = 0
        pc = 0

        for call in day.calls:
            if call.status == 'completed':
                c += 1
            elif call.status == 'pre-call':
                pc += 1

        fast_mode = False
        
        if pc == len(day.calls) or c == len(day.calls) or ALWAYS_FAST_MODE:
            fast_mode = True

        if not SKIP_ALL_SLEEP:
            if fast_mode:
                time.sleep(0.00001)
            else:
                time.sleep(0.05)

    calls_within_sl = day.calls_within_sl()
    service_level = 1.0 * calls_within_sl / len(day.calls)
    
    return_dict = {'SL': service_level, # this should maybe use the day method
                   'AHT': day.aht(),
                   'simulated_day_object': day,
    }
    return return_dict

def agent_logons(agents, timestamp):
    for agent in agents:
        if agent.schedule.regular_start == timestamp and agent.status == 'logged_off':
            agent.status = 'logged_on'
    return agents

def agent_logoffs(agents, timestamp):
    for agent in agents:
        if agent.active_call == False and agent.status == 'logged_on' and agent.schedule.regular_end <= timestamp:
            agent.status = 'logged_off'
    return agents

def queue_calls(calls_list, timestamp):
    for call in calls_list:
        if call.arrival_timestamp == timestamp:
            call.status = 'queued'
            call.queued_at = timestamp
    return calls_list

def answer_calls(day, timestamp):
    for call in day.calls:
        if call.status == 'queued':
            for agent in day.agents:
                if agent.status == 'logged_on' and agent.active_call == False:
                    agent.active_call = True
                    agent.handling_call = call.id
                    call.handled_by = agent
                    call.answered_at = timestamp
                    call.queue_elapsed = timestamp - call.queued_at
                    call.met_sl = (call.queue_elapsed <= day.sl_threshold)
                    call.status = 'active'
                    break
    return day

def hangup_calls(day, timestamp):
    for call in day.calls:
        if call.status == 'active' and (call.duration + call.answered_at) <= timestamp:
            call.status = 'completed'
            call.completed_at = timestamp
            call.handled_by.active_call = False
            call.handled_by.handling_call = None 
    return day

def abandon_calls(day, timestamp):
    # not yet implemented
    # add probability distribution / curve here
    return day


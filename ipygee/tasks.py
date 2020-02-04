# coding=utf-8

""" Google Earth Engine Task Manager """
from .widgets import CheckAccordion, ConfirmationWidget
from datetime import timedelta, datetime
from collections import namedtuple
from dateutil import tz
from ipygee import utils
from ipywidgets import *
from .threading import Thread
import time
import ee
import re

EPOCH = datetime(1970, 1, 1, 0, 0, tzinfo=tz.tzutc())

TEMPLATES = dict()
TEMPLATES['PENDING'] = """
<strong>state:</strong> {state}</br>
<strong>created on:</strong> {creation}</br>
<strong>ellapsed since creation:</strong> {elapsed}
"""
TEMPLATES['RUNNING'] = """
<strong>state:</strong> {state}</br>
<strong>created on:</strong> {creation}</br>
<strong>started running on:</strong> {start}</br>
<strong>ellapsed since creation:</strong> {elapsed}</br>
<strong>running:</strong> {running}</br>
<strong>waiting:</strong> {waiting}
"""
TEMPLATES['SUCCEEDED'] = """
<strong>state:</strong> {state}</br>
<strong>created on:</strong> {creation}</br>
<strong>started running on:</strong> {start}</br>
<strong>finished running on:</strong> {finish}</br>
<strong>running:</strong> {running}</br>
<strong>waiting:</strong> {waiting}</br>
<strong>URLs:</strong> {url}
"""
TEMPLATES['FAILED'] = """
<strong>state:</strong> {state}</br>
<strong>created on:</strong> {creation}</br>
<strong>started running on:</strong> {start}</br>
<strong>failed on:</strong> {failed}</br>
<strong>ellapsed since creation:</strong> {elapsed}</br>
<strong>running:</strong> {running}</br>
<strong>waiting:</strong> {waiting}</br>
<strong>error:</strong> {error}
"""
TEMPLATES['CANCELLED'] = """
<strong>state:</strong> {state}</br>
<strong>created on:</strong> {creation}</br>
<strong>cancelled on:</strong> {cancel}</br>
<strong>running:</strong> {running}</br>
<strong>ellapsed since creation:</strong> {elapsed}</br>
<strong>waiting:</strong> {waiting}
"""

# HELPERS
def now():
    return datetime.now().astimezone(tz.tzlocal())


def get_asset_id(url):
    """ get the assetId from a URL """
    try:
        assetId = re.search('users/.+', url).group()
    except AttributeError:
        try:
            assetId = re.search('projects/.+', url).group()
        except AttributeError:
            try:
                assetId = url.split('?')[1].split('=')[1]
            except:
                assetId = None

    return assetId


def fromisoformat(iso):
    """ for python versions < 3.7 get datetime from isoformat """
    d, t = iso.split('T')
    year, month, day = d.split('-')
    hours, minutes, seconds = t.split(':')
    seconds = float(seconds[0:-1])
    sec = int(seconds)
    microseconds = int((seconds-sec)*1e6)

    return datetime(int(year), int(month), int(day), int(hours), int(minutes), sec, microseconds)


class Task(object):

    @staticmethod
    def delta2millis(dt):
        """ convert a timedelta to milliseconds """
        return dt.total_seconds() * 1000

    @staticmethod
    def millis2delta(ms):
        """ convert a timedelta to milliseconds"""
        return timedelta(seconds= ms / 1000)

    @staticmethod
    def _create_tuple_datetime(name, time):
        nt = namedtuple(name, ('utc', 'local', 'str'))
        if not time:
            return nt(utc=None, local=None, str='')

        try:
            utc = datetime.fromisoformat(time)
        except AttributeError:
            utc = fromisoformat(time)

        utc = utc.replace(tzinfo=tz.tzutc())
        local = utc.astimezone(tz.tzlocal())
        string = local.isoformat()
        return nt(utc=utc, local=local, str=string)

    @staticmethod
    def _create_tuple_timedelta(name, delta):
        nt = namedtuple(name, ('delta', 'str'))
        if not delta:
            return nt(delta=None, str='0s')

        seconds = delta.total_seconds()
        string = utils.format_elapsed(seconds)
        return nt(delta=delta, str=string)

    def __init__(self, task=None, name=None, templates=TEMPLATES, **kwargs):
        super(Task, self).__init__(**kwargs)
        self.templates = templates
        if task:
            self.task = task
            self.name = task.get('name')
        elif name:
            self.name = name
            self.task = ee.data.getOperation(name)

    @property
    def status(self):
        return ee.data.getOperation(self.name)

    @property
    def metadata(self):
        return self.task.get('metadata')

    @property
    def state(self):
        return self.metadata.get('state')

    @property
    def description(self):
        return self.metadata.get('description')

    @property
    def response(self):
        return self.metadata.get('response')

    @property
    def task_type(self):
        return self.metadata.get('type')

    @property
    def create_time(self):
        t = self.metadata.get('createTime')
        return t[:-1] if t else None

    @property
    def update_time(self):
        t = self.metadata.get('updateTime')
        return t[:-1] if t else None

    @property
    def start_time(self):
        t = self.metadata.get('startTime')
        return t[:-1] if t else None

    def update(self):
        self.task = self.status

    def cancel(self):
        ee.data.cancelOperation(self.name)

    def is_done(self):
        done = self.task.get('done')
        return done or False

    def has_started(self):
        return False if self.started.utc == EPOCH else True

    def has_finished(self):
        return True if self.state == 'SUCCEEDED' else False

    def has_failed(self):
        return True if self.state == 'FAILED' else False

    def is_running(self):
        return True if self.state == 'RUNNING' else False

    def is_pending(self):
        return True if self.state == 'PENDING' else False

    def is_cancelled(self):
        return True if self.state == 'CANCELLED' else False

    @property
    def uris(self):
        return self.metadata.get('destinationUris')

    @property
    def error(self):
        err = self.task.get('error')
        msg = err.get('message') if err else ''
        return msg

    @property
    def created(self):
        return self._create_tuple_datetime('Created', self.create_time)

    @property
    def started(self):
        return self._create_tuple_datetime('Started', self.start_time)

    @property
    def updated(self):
        return self._create_tuple_datetime('Updated', self.update_time)

    @property
    def finished(self):
        t = self.update_time if self.has_finished() else 0
        return self._create_tuple_datetime('Finished', t)

    @property
    def failed(self):
        t = self.update_time if self.has_failed() else None
        return self._create_tuple_datetime('Failed', t)

    @property
    def cancelled(self):
        t = self.update_time if self.is_cancelled() else 0
        return self._create_tuple_datetime('Cancelled', t)

    @property
    def title(self):
        if not (self.has_finished() or self.has_failed() or self.is_cancelled()):
            value = '{} ({})'.format(self.description, self.task_type)
        else:
            value = '{} ({}) [{}]'.format(self.description, self.task_type, self.running.str)

        return value

    @property
    def since_creation(self):
        td = datetime.now().astimezone(tz.tzlocal()) - self.created.local
        return self._create_tuple_timedelta('SinceCreation', td)

    @property
    def waiting(self):
        if not self.has_started():
            if self.is_cancelled():
                td = self.cancelled.local - self.created.local
            else:
                td = now() - self.created.local
        else:
            td = self.started.local - self.created.local

        return self._create_tuple_timedelta('Waiting', td)

    @property
    def running(self):
        if not self.has_started():
            td = timedelta(0)

        if self.has_started():
            if self.is_running():
                td = now() - self.started.local

            if self.has_finished():
                td = self.finished.local - self.started.local

            if self.has_failed():
                td = self.failed.local - self.started.local

            if self.is_cancelled():
                td = self.cancelled.local - self.started.local

        return self._create_tuple_timedelta('Running', td)

    def urls(self):
        if self.uris:
            return self.uris
        else:
            return []

    def html(self):
        template = self.templates.get(self.state)
        return template.format(
            creation = self.created.str,
            elapsed = self.since_creation.str,
            start = self.started.str,
            running = self.running.str,
            finish = self.finished.str,
            url = '</br>'.join(self.urls()) if self.urls() else '',
            error = self.error,
            failed = self.failed.str,
            cancel = self.cancelled.str,
            waiting = self.waiting.str,
            state = self.state
        )


class TaskList(CheckAccordion):
    def __init__(self, raw=None, limit=None, **kwargs):
        self.tasks = list()
        self.limit = limit
        self.raw = raw or []
        super(TaskList, self).__init__(widgets=self.tasks, **kwargs)

    def size(self):
        return len(self.raw)

    def filter(self, value='PENDING', by='state'):
        """ Filter the Task List and return a new Widget """
        if by == 'state':
            filtered = [task for task in self.raw if task['metadata']['state'] == value]
        return TaskList(filtered)

    def make(self):
        tasklist = list()
        taskwid = list()
        titles = list()
        if not self.limit:
            limit = self.raw
        else:
            limit = self.raw[0:self.limit]

        for task in limit:
            t = Task(task=task)
            tasklist.append(t)
            taskwid.append(HTML(t.html()))
            titles.append(t.title)

        self.tasks = tasklist
        self.widgets = taskwid
        self.set_titles(titles)

    def selected_tasks(self):
        """ Get the selected tasks """
        selected = self.checked_rows()
        return [self.tasks[sel] for sel in selected]

    def update_all_tasks(self):
        for i in range(self.size()):
            self.update_position(i)

    def update_position(self, position):
        task = self.tasks[position]
        wids = self.widgets
        title = task.title
        wids[position].value = '<b>Loading...</b>'
        task.update()
        newcontent = task.html()
        wids[position].value = newcontent

    def cancel_position(self, position):
        task = self.tasks[position]
        task.cancel()
        wids = self.widgets
        wids[position].value = '<b>Cancelled request sent</b>'

    def update_selected(self):
        selected = self.checked_rows()
        for sel in selected:
            self.update_position(sel)

    def cancel_selected(self):
        selected = self.checked_rows()
        name_list = [self.tasks[sel].title for sel in selected if self.tasks[sel].is_running()]
        if (name_list):
            names = ''
            for name in name_list:
                names += '<li>'+name+'</li>'
            title = '<b>Cancelling selected tasks</b>'
            legend = 'Are you sure you want to cancel the following tasks?? </br><ul>{}</ul>'.format(names)
            def yes(button=None):
                for sel in selected:
                    self.cancel_position(sel)
            confirmation = ConfirmationWidget(title=title, legend=legend,
                                              handle_yes=yes)
            return confirmation


class TaskHeader(HBox):
    def __init__(self, tab, logger, **kwargs):
        super(TaskHeader, self).__init__(**kwargs)
        self.tab = tab
        self.logger = logger
        self.checkbox = Checkbox(indent=False,
                                 layout=Layout(flex='1 1 20', width='auto'))
        self.cancel_selected = Button(description='Cancel Selected',
                                      tooltip='Cancel all selected tasks')
        self.refresh_all = Button(description='Refresh',
                                  tooltip='Refresh Tasks List')
        self.update_selected = Button(description='Update Selected',
                                      tooltip='Update Selected Tasks')
        self.autorefresh = ToggleButton(description='auto-refresh',
                                        tooltip='click to enable/disable autorefresh')
        self.slider = IntSlider(min=5, max=120, step=1, value=15)
        self.children = [self.checkbox, self.refresh_all, self.update_selected,
                         self.cancel_selected, self.autorefresh, self.slider]

        # Set handlers
        self.refresh_all.on_click(self.on_refresh_all)
        self.update_selected.on_click(self.on_update_selected)
        self.cancel_selected.on_click(self.on_cancel_selected)
        self.checkbox.observe(self.select_all, names='value')
        self.autorefresh.observe(self.autorefresh_handler, names='value')

        def tab_handler(change):
            self.checkbox.value = False
        self.tab.observe(tab_handler, names='selected_index')

    # Handlers
    def on_refresh_all(self, button=None):
        self.tab.refresh()

    def on_update_selected(self, button):
        self.tab.update_selected()

    def on_cancel_selected(self, button):
        wid = self.tab.cancel_selected()
        self.logger.children = [wid]

        def emptyLogger(button=None):
            self.logger.children = []
            self.on_refresh_all()

        # add handlers
        wid.yes.on_click(emptyLogger) # this adds a second handler for yes
        wid.no.on_click(emptyLogger)
        wid.cancel.on_click(emptyLogger)

    def select_all(self, change):
        value = change['new']
        TL = self.tab.get_tasklist()
        for checkrow in TL.children:
            checkrow.checkbox.value = value

    def autorefresh_loop(self, slider):
        while True:
            time.sleep(slider.value)
            self.tab.refresh()

    def autorefresh_handler(self, change):
        value = change['new']
        owner = change['owner']
        if value:
            p = Thread(target=self.autorefresh_loop, args=(self.slider,))
            p.start()
            owner.process = p
        else:
            owner.process.terminate()
            owner.process.join()


class TaskTab(Tab):
    categories = ['PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED']
    TL_index = 0

    def __init__(self, limit=None, **kwargs):
        super(TaskTab, self).__init__(**kwargs)
        self.limit = limit
        child = []

        for cat in self.categories:
            child.append(VBox())

        self.children = child
        self.make_tasklist()
        self.complete_titles()
        self.make(0)
        self.rendered = [0]

        def on_select(change):
            name = change.get('name')
            if name == 'selected_index':
                i = change.get('new')
                this = change.get('owner')
                if i not in self.rendered:
                    self.show_loading(i)
                    self.make(i)
                    self.rendered.append(i)

        self.observe(on_select)

    def show_loading(self, i):
        category = self.categories[i]
        vbox = self.children[i]
        vbox.children = [Label('Loading...')]

    def make(self, i):
        """ Make a category TaskList """
        category = self.categories[i]
        vbox = self.children[i]
        TL = self.TL.filter(category)
        if self.limit:
            TL.limit = self.limit
        TL.make()
        vbox.children = [TL]

    def make_tasklist(self):
        self.tasklist = ee.data.listOperations()
        self.TL = TaskList(self.tasklist, self.limit)

    def get_tasklist(self, i=None):
        """ Get the TaskList from a category """
        i = i or self.selected_index
        vbox = self.children[i]
        TL = vbox.children[self.TL_index]
        return TL

    def complete_titles(self):
        for category in self.categories:
            i = self.categories.index(category)
            TL = self.TL.filter(category)
            size = TL.size()
            if self.limit and size>self.limit:
                size_str = '{}+'.format(self.limit)
            else:
                size_str = '{}'.format(size)

            name = '{} [{}]'.format(category, size_str)
            self.set_title(i, name)

    def refresh(self):
        i = self.selected_index
        self.show_loading(i)
        self.make_tasklist()
        self.complete_titles()
        self.make(i)
        self.rendered = [i]

    def update_selected(self, i=None):
        TL = self.get_tasklist(i)
        TL.update_selected()

    def cancel_selected(self, i=None):
        TL = self.get_tasklist(i)
        return TL.cancel_selected()


class TaskManager(VBox):
    def __init__(self, limit=None, **kwargs):
        super(TaskManager, self).__init__(**kwargs)
        self.tabs = TaskTab(limit)
        self.logger = HBox()
        self.header = TaskHeader(self.tabs, self.logger)
        self.children = [self.header, self.logger, self.tabs]

    def selected_tasks(self):
        i = self.tabs.selected_index
        vbox = self.tabs.children[i]
        TL = vbox.children[0]
        return TL.selected_tasks()

    @staticmethod
    def _sum_deltas(deltas):
        if len(deltas) > 1:
            total = deltas[0]
            rest = deltas[1:]
            for d in rest:
                total += d
        elif len(deltas) == 1:
            total = deltas[0]
        else:
            total = timedelta(0)

        return total

    def waiting_time(self):
        """ Compute the waiting time of the selected tasks. It does not sum
        all waiting times but counts from the time of the first created to the
        time of the one that started at last
        """
        tasks = self.selected_tasks()
        delta = None
        if tasks:
            created = [task.created.local for task in tasks]
            min_created = min(created)
            started = []
            for task in tasks:
                if task.has_started():
                    started.append(task.started.local)
            if started:
                max_started = max(started)
                delta = max_started - min_created
        return delta

    def running_time(self):
        """ Compute the running time. It does not sum all running times but
        counts from the time of the first that started running to the last
        that finished
        """
        tasks = self.selected_tasks()
        delta = None
        if tasks:
            started = []
            finished = []
            for task in tasks:
                if task.has_started() and task.has_finished():
                    started.append(task.started.local)
                    finished.append(task.finished.local)
            if started and finished:
                min_started = min(started)
                max_finished = max(finished)
                delta = max_finished - min_started
        return delta

    def total_time(self):
        """ Compute running time + waiting time. It is NOT the same as summing
        both separately
        """
        tasks = self.selected_tasks()
        delta = None
        if tasks:
            created = []
            finished = []
            for task in tasks:
                if task.has_started() and task.has_finished():
                    created.append(task.created.local)
                    finished.append(task.finished.local)
            if created and finished:
                min_created = min(created)
                max_finished = max(finished)
                delta = max_finished - min_created
        return delta
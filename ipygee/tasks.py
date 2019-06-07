# coding=utf-8

""" Google Earth Engine Task Manager """

import datetime
from ipywidgets import *
from . import utils
from .threading import Thread
import time
from .widgets import CheckRow
import ee

    
def formatter(task):
    """ Format a task and return a widget """
    now_dt = datetime.datetime.now()
    state = task.get('state')
    task_id = task.get('id')
    # UPDATED TIME
    # updated = task.get('update_timestamp_ms')
    # if updated:
    #      update_ts = get_timestamp(updated)

    # CREATION TIME
    creation = task.get('creation_timestamp_ms')
    created_dt = utils.get_datetime(creation)
    created_str = utils.format_timestamp(creation) if creation else ''

    # ELLAPSED
    if creation:
        delta_ellapsed = now_dt - utils.get_datetime(creation)
        ellapsed = utils.format_elapsed(delta_ellapsed.total_seconds())
    else:
        ellapsed = ''

    if state == 'READY':
        html_str = """
        <strong>created on:</strong> {creation}</br>
        <strong>ellapsed since creation:</strong> {ellapsed}
        """.format(creation=created_str, ellapsed=ellapsed)
        widget = HTML(html_str)
    elif state == 'RUNNING':
        start = task.get('start_timestamp_ms')
        start_dt = utils.get_datetime(start)
        start_str = utils.format_timestamp(start)
        running_td = now_dt - start_dt
        running_str = utils.format_elapsed(running_td.total_seconds())
        html_str = """
        <strong>created on:</strong> {creation}</br>
        <strong>started running on:</strong> {start}</br>
        <strong>ellapsed since creation:</strong> {ellapsed}</br>
        <strong>running:</strong> {running}
        """.format(creation=created_str, ellapsed=ellapsed,
                   running=running_str, start=start_str)
        widget = HTML(html_str)
    elif state == 'COMPLETED':
        urls = task.get('output_url')
        url = urls[0]

        start = task.get('start_timestamp_ms')
        start_dt = utils.get_datetime(start)
        start_str = utils.format_timestamp(start)

        finish = task.get('update_timestamp_ms')
        finish_dt = utils.get_datetime(finish)
        finish_str = utils.format_timestamp(finish)

        running_td = finish_dt - start_dt
        running_str = utils.format_elapsed(running_td.total_seconds())

        html_str = """
        <strong>created on:</strong> {creation}</br>
        <strong>started running on:</strong> {start}</br>
        <strong>finished running on:</strong> {finish}</br>
        <strong>ellapsed since creation:</strong> {ellapsed}</br>
        <strong>running:</strong> {running}</br>
        <strong>URL:</strong> {url}
        """.format(url=url, creation=created_str, ellapsed=ellapsed,
                   running=running_str, start=start_str, finish=finish_str)
        widget = HTML(html_str)
    elif state == 'FAILED':
        widget = utils.create_accordion(task)
    elif state == 'CANCELLED':
        cancelled_ts = task.get('update_timestamp_ms')
        cancelled_dt = utils.get_datetime(cancelled_ts)
        cancelled_str = utils.format_timestamp(cancelled_ts)
        active_td = cancelled_dt - created_dt
        active_str = utils.format_elapsed(active_td.total_seconds())

        html_str = """
        <strong>created on:</strong> {creation}</br>
        <strong>cancelled on:</strong> {cancel}</br>
        <strong>active for:</strong> {active}</br>
        <strong>ellapsed since creation:</strong> {ellapsed}</br>
        """.format(creation=created_str, ellapsed=ellapsed,
                   cancel=cancelled_str, active=active_str)
        widget = HTML(html_str)
    else:
        widget = utils.create_accordion(task)

    widget.task_id = task_id
    widget.task_state = state
    return widget


class TaskManager(VBox):
    def __init__(self, **kwargs):
        super(TaskManager, self).__init__(**kwargs)
        # Header
        self.checkbox = Checkbox(indent=False,
                                 layout=Layout(flex='1 1 20', width='auto'))
        self.cancel_selected = Button(description='Cancel Selected',
                                      tooltip='Cancel all selected tasks')
        self.cancel_all = Button(description='Cancell All',
                                 tooltip='Cancel all tasks')
        self.refresh = Button(description='Refresh',
                              tooltip='Refresh Tasks List')
        self.autorefresh = ToggleButton(description='auto-refresh',
                                        tooltip='click to enable/disable autorefresh')
        self.slider = IntSlider(min=5, max=120, step=1, value=15)
        self.hbox = HBox([self.checkbox, self.refresh,
                          self.cancel_selected, self.cancel_all,
                          self.autorefresh, self.slider])

        # Tabs for COMPLETED, FAILED, etc
        self.tabs = Tab()
        # Tabs index
        self.tab_index = {
            0: 'READY',
            1: 'RUNNING',
            2: 'COMPLETED',
            3: 'FAILED',
            4: 'CANCELLED',
            5: 'UNKNOWN'
        }

        self.taskVBox = VBox()

        self.runningVBox = VBox()
        self.completedVBox = VBox()
        self.failedVBox = VBox()
        self.canceledVBox = VBox()
        self.unknownVBox = VBox()
        self.readyVBox = VBox()

        self.tab_widgets_rel = {'RUNNING': self.runningVBox,
                                'COMPLETED': self.completedVBox,
                                'FAILED': self.failedVBox,
                                'CANCELLED': self.canceledVBox,
                                'READY': self.readyVBox,
                                'UNKNOWN': self.unknownVBox}

        # Create Tabs
        self.tab_widgets = []
        for key, val in self.tab_index.items():
            widget = self.tab_widgets_rel[val]
            self.tab_widgets.append(widget)
            self.tabs.children = self.tab_widgets
            self.tabs.set_title(key, val)

        # First widget
        self.update_task_list()
        # self.children = (self.hbox, self.taskVBox)
        self.children = (self.hbox, self.tabs)

        # Set on_click for refresh button
        self.refresh.on_click(lambda refresh: self.update_task_list())

        # Set on_clicks
        self.cancel_all.on_click(self.cancel_all_click)
        self.cancel_selected.on_click(self.cancel_selected_click)
        self.autorefresh.observe(self.autorefresh_handler, names='value')

    def autorefresh_loop(self, slider):
        while True:
            time.sleep(slider.value)
            self.update_task_list()

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

    def tab_handler(self, change):
        if change['name'] == 'selected_index':
            self.update_task_list()

    def selected_tab(self):
        ''' get the selected tab '''
        index = self.tabs.selected_index
        tab_name = self.tab_index[index]
        return self.tab_widgets_rel[tab_name]

    def update_task_list(self):
        self.selected_tab().children = (HTML('Loading...'),)
        try:
            tasklist = ee.data.getTaskList()
            # empty lists
            running_list = []
            completed_list = []
            failed_list = []
            canceled_list = []
            unknown_list = []
            ready_list = []
            all_list = {'RUNNING': running_list, 'COMPLETED': completed_list,
                        'FAILED': failed_list, 'CANCELLED': canceled_list,
                        'READY': ready_list, 'UNKNOWN': unknown_list}
            for task in tasklist:
                state = task['state']
                description = task['description']
                task_type = task['task_type']
                name = '{} ({})'.format(description, task_type)
                # # Accordion for CheckRow widget
                taskwidget = formatter(task)
                mainacc = Accordion(children=(taskwidget, ))
                mainacc.set_title(0, name)
                mainacc.selected_index = None
                # CheckRow
                wid = CheckRow(mainacc)
                # Append widget to the CORRECT list
                all_list[state].append(wid)
            # Assign Children
            self.runningVBox.children = tuple(running_list)
            self.completedVBox.children = tuple(completed_list)
            self.failedVBox.children = tuple(failed_list)
            self.canceledVBox.children = tuple(canceled_list)
            self.unknownVBox.children = tuple(unknown_list)
            self.readyVBox.children = tuple(ready_list)
        except Exception as e:
            self.selected_tab().children = (HTML(str(e)),)

    def get_selected(self):
        """ Get selected Tasks

        :return: a list of the selected indexes
        """
        selected = []
        children = self.selected_tab().children
        for i, child in enumerate(children):
            # checkrow = child.children[0] # child is an accordion
            state = child.checkbox.value
            if state: selected.append(i)
        return selected

    def get_taskid(self, index):
        # Get selected Tab
        selected_wid = self.selected_tab() # VBox
        # Children of the Tab's VBox
        children = selected_wid.children
        # Get CheckRow that corresponds to the passed index
        checkrow = children[index]
        # Get main accordion
        mainacc = checkrow.widget
        # Get details accordion
        selectedacc = mainacc.children[0]
        for n, child in enumerate(selectedacc.children):
            title = selectedacc.get_title(n)
            if title == 'id':
                return child.value

    def get_selected_taskid(self):
        """ Get selected Tasks ID

        :return: a list of the selected task ids
        """
        selected_wid = self.selected_tab() # VBox
        children = selected_wid.children
        taskid_list = []
        for child in children:
            html_wid = child.widget.children[0]
            selected = child.checkbox.value
            if selected:
                taskid_list.append(html_wid.task_id)

        return taskid_list

    def cancel_selected_click(self, button):
        selected = self.get_selected_taskid()
        for taskid in selected:
            try:
                ee.data.cancelTask(taskid)
            except:
                continue
        self.update_task_list()

    def cancel_all_click(self, button):
        selected_wid = self.selected_tab() # VBox
        children = selected_wid.children
        for n, child in enumerate(children):
            taskid = self.get_taskid(n)
            try:
                ee.data.cancelTask(taskid)
            except:
                continue
        self.update_task_list()
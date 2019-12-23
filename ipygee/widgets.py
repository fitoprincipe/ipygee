# coding=utf-8

""" Generic Custom Widgets to use in this module """

from ipywidgets import *
from traitlets import *


class CheckRow(HBox):
    checkbox = Instance(Checkbox)
    widget = Instance(Widget)

    def __init__(self, widget, **kwargs):
        self.checkbox = Checkbox(indent=False,
                                 layout=Layout(flex='1 1 20', width='auto'))
        self.widget = widget
        super(CheckRow, self).__init__(children=(self.checkbox, self.widget),
                                       **kwargs)
        self.layout = Layout(display='flex', flex_flow='row',
                             align_content='flex-start')

    @observe('widget')
    def _ob_wid(self, change):
        new = change['new']
        self.children = (self.checkbox, new)

    def observe_checkbox(self, handler, extra_params={}, **kwargs):
        """ set handler for the checkbox widget. Use the property 'widget' of
        change to get the corresponding widget

        :param handler: callback function
        :type handler: function
        :param extra_params: extra parameters that can be passed to the handler
        :type extra_params: dict
        :param kwargs: parameters from traitlets.observe
        :type kwargs: dict
        """
        # by default only observe value
        name = kwargs.get('names', 'value')

        def proxy_handler(handler):
            def wrap(change):
                change['widget'] = self.widget
                for key, val in extra_params.items():
                    change[key] = val
                return handler(change)
            return wrap
        self.checkbox.observe(proxy_handler(handler), names=name, **kwargs)

    def observe_widget(self, handler, extra_params={}, **kwargs):
        """ set handler for the widget alongside de checkbox

        :param handler: callback function
        :type handler: function
        :param extra_params: extra parameters that can be passed to the handler
        :type extra_params: dict
        :param kwargs: parameters from traitlets.observe
        :type kwargs: dict
        """
        def proxy_handler(handler):
            def wrap(change):
                change['checkbox'] = self.checkbox
                for key, val in extra_params.items():
                    change[key] = val
                return handler(change)
            return wrap
        self.widget.observe(proxy_handler(handler), **kwargs)


class CheckAccordion(VBox):
    # widgets = Tuple()
    widgets = List()

    def __init__(self, widgets, **kwargs):
        # self.widgets = widgets
        super(CheckAccordion, self).__init__(**kwargs)
        self.widgets = widgets

    @observe('widgets')
    def _on_child(self, change):
        new = change['new'] # list of any widget
        newwidgets = []
        for widget in new:
            # constract the widget
            acc = Accordion(children=(widget,))
            acc.selected_index = None # this will unselect all
            # create a CheckRow
            checkrow = CheckRow(acc)
            newwidgets.append(checkrow)
        newchildren = tuple(newwidgets)
        self.children = newchildren

    def set_title(self, index, title):
        """ set the title of the widget at indicated index"""
        checkrow = self.children[index]
        acc = checkrow.widget
        acc.set_title(0, title)

    def set_titles(self, titles):
        """ set the titles for all children, `titles` size must match
        `children` size """
        for i, title in enumerate(titles):
            self.set_title(i, title)

    def get_title(self, index):
        """ get the title of the widget at indicated index"""
        checkrow = self.children[index]
        acc = checkrow.widget
        return acc.get_title(0)

    def get_check(self, index):
        """ get the state of checkbox in index """
        checkrow = self.children[index]
        return checkrow.checkbox.value

    def set_check(self, index, state):
        """ set the state of checkbox in index """
        checkrow = self.children[index]
        checkrow.checkbox.value = state

    def checked_rows(self):
        """ return a list of indexes of checked rows """
        checked = []
        for i, checkrow in enumerate(self.children):
            state = checkrow.checkbox.value
            if state: checked.append(i)
        return checked

    def get_widget(self, index):
        """ get the widget in index """
        checkrow = self.children[index]
        return checkrow.widget

    def set_widget(self, index, widget):
        """ set the widget for index """
        checkrow = self.children[index]
        checkrow.widget.children = (widget,) # Accordion has 1 child

    def set_row(self, index, title, widget):
        """ set values for the row """
        self.set_title(index, title)
        self.set_widget(index, widget)

    def set_accordion_handler(self, index, handler, **kwargs):
        """ set the handler for Accordion in index """
        checkrow = self.children[index]
        checkrow.observe_widget(handler, names=['selected_index'], **kwargs)

    def set_checkbox_handler(self, index, handler, **kwargs):
        """ set the handler for CheckBox in index """
        checkrow = self.children[index]
        checkrow.observe_checkbox(handler, **kwargs)


class ConfirmationWidget(VBox):
    def __init__(self, title='Confirmation', legend='Are you sure?',
                 handle_yes=None, handle_no=None, handle_cancel=None, **kwargs):
        super(ConfirmationWidget, self).__init__(**kwargs)
        # Title Widget
        self.title = title
        self.title_widget = HTML(self.title)
        # Legend Widget
        self.legend = legend
        self.legend_widget = HTML(self.legend)
        # Buttons
        self.yes = Button(description='Yes')
        handler_yes = handle_yes if handle_yes else lambda x: x
        self.yes.on_click(handler_yes)

        self.no = Button(description='No')
        handler_no = handle_no if handle_no else lambda x: x
        self.no.on_click(handler_no)

        self.cancel = Button(description='Cancel')
        handler_cancel = handle_cancel if handle_cancel else lambda x: x
        self.cancel.on_click(handler_cancel)

        self.buttons = HBox([self.yes, self.no, self.cancel])

        self.children = [self.title_widget, self.legend_widget, self.buttons]


class RealBox(Box):
    """ Real Box Layout

    items:
    [[widget1, widget2],
     [widget3, widget4]]

    """
    items = List()
    width = Int()
    border_inside = Unicode()
    border_outside = Unicode()

    def __init__(self, **kwargs):
        super(RealBox, self).__init__(**kwargs)

        self.layout = Layout(display='flex', flex_flow='column',
                             border=self.border_outside)

    def max_row_elements(self):
        maxn = 0
        for el in self.items:
            n = len(el)
            if n>maxn:
                maxn = n
        return maxn

    @observe('items')
    def _ob_items(self, change):
        layout_columns = Layout(display='flex', flex_flow='row')
        new = change['new']
        children = []
        # recompute size
        maxn = self.max_row_elements()
        width = 100/maxn
        for el in new:
            for wid in el:
                if not wid.layout.width:
                    if self.width:
                        wid.layout = Layout(width='{}px'.format(self.width),
                                            border=self.border_inside)
                    else:
                        wid.layout = Layout(width='{}%'.format(width),
                                            border=self.border_inside)
            hbox = Box(el, layout=layout_columns)
            children.append(hbox)
        self.children = children


class ErrorAccordion(Accordion):
    def __init__(self, error, traceback, **kwargs):
        super(ErrorAccordion, self).__init__(**kwargs)
        self.error = '{}'.format(error).replace('<','{').replace('>','}')

        newtraceback = ''
        for trace in traceback[1:]:
            newtraceback += '{}'.format(trace).replace('<','{').replace('>','}')
            newtraceback += '</br>'

        self.traceback = newtraceback

        self.errorWid = HTML(self.error)

        self.traceWid = HTML(self.traceback)

        self.children = (self.errorWid, self.traceWid)
        self.set_title(0, 'ERROR')
        self.set_title(1, 'TRACEBACK')
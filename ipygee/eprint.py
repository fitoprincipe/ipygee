# coding=utf-8

""" Print a EE Object in the Jupyter environment """

from ipywidgets import *
from IPython.display import display
from . import dispatcher, threading, utils
from geetools.ui.dispatcher import belongToEE
from .widgets import ErrorAccordion
import traceback
import sys
from time import time


class Eprint(object):
    """ Print EE Objects. Similar to `print(object.getInfo())` but with
    some magic (lol)

    :param eeobject: object to print
    :type eeobject: ee.ComputedObject
    """
    ASYNC = True

    def __call__(self, *args):
        size = len(args)

        # Output structure
        def structure():
            acc = Accordion([Output()])
            acc.set_title(0, 'Loading...')
            return acc

        # VERTICAL GRID WIDGET TO OUTPUT RESULTS
        vbox_arg = []
        for arg in args:
            if belongToEE(arg):
                vbox_arg.append(structure())
            else:
                vbox_arg.append(Label(str(arg)))
        infowin = VBox(vbox_arg)

        # HELPER
        def setchildren(vbox, i, val, local_type, server_type, dt):
            children = list(vbox.children)
            wid = children[i]
            ellapsed = utils.format_elapsed(dt)
            if isinstance(wid, (Accordion,)):
                if local_type != server_type:
                    title = '{} (local) / {} (server) [{}]'.format(
                        local_type, server_type, ellapsed)
                else:
                    title = '{} [{}]'.format(server_type, ellapsed)

                wid.set_title(0, title)
                wid.children = [val]
                wid.selected_index = None if size > 1 else 0

        def get_info(eeobject, index):
            """ Get Info """
            start = time()
            try:
                eewidget = dispatcher.dispatch(eeobject)
                widget = eewidget.widget
                local_type = eewidget.local_type
                server_type = eewidget.server_type
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                trace = traceback.format_exception(exc_type, exc_value,
                                                   exc_traceback)
                widget = ErrorAccordion(e, trace)
                local_type = 'ERROR'
                server_type = 'ERROR'
            end = time()
            dt = end-start
            setchildren(infowin, index, widget, local_type, server_type, dt)

        for i, eeobject in enumerate(args):
            # DO THE SAME FOR EVERY OBJECT
            if self.ASYNC:
                thread = threading.Thread(target=get_info,
                                          args=(eeobject, i))
                thread.start()
            else:
                get_info(eeobject, i)

        display(infowin)
# coding=utf-8

""" Print a EE Object in the Jupyter environment """

from ipywidgets import *
from IPython.display import display
from . import dispatcher, threading
from geetools.ui.dispatcher import belongToEE


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
        # infowin = VBox([Output()]*len(args))
        vbox_arg = []
        for arg in args:
            if belongToEE(arg):
                vbox_arg.append(structure())
            else:
                vbox_arg.append(Label(str(arg)))
        # infowin = VBox([structure]*len(args))
        infowin = VBox(vbox_arg)

        # HELPER
        def setchildren(vbox, i, val, local_type, server_type):
            children = list(vbox.children)
            wid = children[i]
            if isinstance(wid, (Accordion,)):
                if local_type != server_type:
                    title = '{} (local) / {} (server)'.format(local_type,
                                                              server_type)
                else:
                    title = server_type
                wid.set_title(0, title)
                wid.children = [val]
                wid.selected_index = None if size > 1 else 0

        def get_info(eeobject, index):
            """ Get Info """
            eewidget = dispatcher.dispatch(eeobject)
            widget = eewidget.widget
            setchildren(infowin, index, widget, eewidget.local_type,
                        eewidget.server_type)

        for i, eeobject in enumerate(args):
            # DO THE SAME FOR EVERY OBJECT
            if self.ASYNC:
                thread = threading.Thread(target=get_info,
                                          args=(eeobject, i))
                thread.start()
            else:
                get_info(eeobject, i)

        display(infowin)
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
            return Accordion([Output()])

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
        def setchildren(vbox, i, val, otype):
            children = list(vbox.children)
            wid = children[i]
            if isinstance(wid, (Accordion,)):
                wid.set_title(0, otype)
                wid.children = [val]
                wid.selected_index = None if size > 1 else 0

        def get_info(eeobject, index):
            """ Get Info """
            widget = dispatcher.dispatch(eeobject)
            setchildren(infowin, index, widget, eeobject.__class__.__name__)

        for i, eeobject in enumerate(args):
            # DO THE SAME FOR EVERY OBJECT
            if self.ASYNC:
                thread = threading.Thread(target=get_info,
                                          args=(eeobject, i))
                thread.start()
            else:
                get_info(eeobject, i)

        display(infowin)
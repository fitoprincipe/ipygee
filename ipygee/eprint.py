# coding=utf-8

""" Print a EE Object in the Jupyter environment """

from ipywidgets import *
from . import dispatcher, threading
from IPython.display import display

CONFIG = {'do_async': True}


def worker(obj, container):
    """ The worker to work in a Thread or not """
    eewidget = dispatcher.dispatch(obj)
    dispatcher.set_container(container, eewidget)


def process_object(obj, do_async):
    """ Process one object for printing """
    if isinstance(obj, (str, int, float)):
        return Label(str(obj))
    else:
        if do_async:
            container, button = dispatcher.create_container(True)
            thread = threading.Thread(target=worker, args=(obj, container))
            button.on_click(lambda but: dispatcher.cancel(thread, container))
            thread.start()
        else:
            container, _ = dispatcher.create_container(False)
            worker(obj, container)
        return container


def getInfo(obj, do_async=None):
    """ Get Information Widget for the parsed EE object """
    if do_async is None:
        do_async = CONFIG.get('do_async')

    return process_object(obj, do_async)


def eprint(*objs, do_async=None, container=None):
    """ Print EE Objects. Similar to `print(object.getInfo())` but returns a
    widget for Jupyter notebooks

    :param eeobject: object to print
    :type eeobject: ee.ComputedObject
    :param container: any container widget
        (see https://ipywidgets.readthedocs.io/en/stable/examples/Widget%20List.html#Container/Layout-widgets)
    :type container: ipywidget.Widget
    """
    if container is None:
        container = VBox()

    children = []
    for obj in objs:
        widget = getInfo(obj, do_async)
        children.append(widget)
        container.children = children

    display(container)


def set_eprint_async(do_async):
    """ Set the global async for eprint """
    CONFIG['do_async'] = do_async
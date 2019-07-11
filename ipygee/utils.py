# coding=utf-8

""" Util functions """

from ipywidgets import *
from .dispatcher import dispatch
import datetime


def create_accordion(dictionary):
    """ Create an Accordion output from a dict object """
    widlist = []
    ini = 0
    widget = Accordion()
    widget.selected_index = None # this will unselect all
    for key, val in dictionary.items():
        if isinstance(val, dict):
            newwidget = create_accordion(val)
            widlist.append(newwidget)
        elif isinstance(val, list):
            # tranform list to a dictionary
            dictval = {k: v for k, v in enumerate(val)}
            newwidget = create_accordion(dictval)
            widlist.append(newwidget)
        else:
            value = HTML(str(val))
            widlist.append(value)
        widget.set_title(ini, key)
        ini += 1
    widget.children = widlist
    return widget


def get_datetime(timestamp):
    return datetime.datetime.fromtimestamp(float(timestamp)/1000)


def format_timestamp(timestamp):
    """ Format a POSIX timestamp given in milliseconds """
    dt = get_datetime(timestamp)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def format_elapsed(seconds):
    if seconds < 60:
        return '{}s'.format(int(seconds))
    elif seconds < 3600:
        minutes = seconds/60
        seconds = (minutes-int(minutes))*60
        return '{}m {}s'.format(int(minutes), int(seconds))
    elif seconds < 86400:
        hours = seconds/3600
        minutes = (hours-int(hours))*60
        seconds = (minutes-int(minutes))*60
        return '{}h {}m {}s'.format(int(hours), int(minutes), int(seconds))
    else:
        days = seconds/86400
        hours = (days-int(days))*60
        minutes = (hours-int(hours))*60
        seconds = (minutes-int(minutes))*60
        return '{}d {}h {}m {}s'.format(int(days), int(hours), 
                                        int(minutes), int(seconds))


def create_object_output(object):
    """ Create a output Widget for Images, Geometries and Features """

    ty = object.__class__.__name__

    if ty == 'Image':
        return dispatch(object).widget
    elif ty == 'FeatureCollection':
        try:
            info = object.getInfo()
        except:
            print('FeatureCollection limited to 4000 features')
            info = object.limit(4000)

        return create_accordion(info)
    else:
        info = object.getInfo()
        return create_accordion(info)


def create_async_output(object, widget):
    try:
        child = create_object_output(object)
    except Exception as e:
        child = HTML('There has been an error: {}'.format(str(e)))

    widget.children = [child]


# coding=utf-8

""" Dispatch methods for different EE Object types

The dispatcher functions must take as single argument the information return
by ee.ComputedObject.getInfo(), process it and return an ipywidget
"""

import ee
from ipywidgets import *
from . import utils
from geetools.ui.dispatcher import belongToEE
from time import time
import sys
import traceback
from .widgets import ErrorAccordion
from datetime import datetime

DISPATCHERS = dict()


# HELPERS
def order(d):
    """ Order a dict and return a list of [key, val] """
    results = []
    if isinstance(d, dict):
        keys = list(d.keys())
        keys.sort()
        for k in keys:
            results.append([str(k), d[k]])
    else:
        for i, val in enumerate(d):
            results.append([str(i), val])
    return results


def isurl(value):
    """ Determine if the parsed string is a url """
    url = False
    if isinstance(value, str):
        if value[:4] == 'http' or value[:3] == 'www':
            url = True
    return url


def new_line(val, n):
    newval = ''
    for i, v in enumerate(val):
        if i%n == 0 and i != 0:
            newval += '</br>'+v
        else:
            newval += v
    return newval


def create_container(thread=False):
    """ Create the structure for each object. Returns an Accordion """
    if thread:
        cancel_button = Button(description='Cancel')
        acc = Accordion([cancel_button])
        acc.set_title(0, 'Loading...')
    else:
        acc = Accordion([Output()])
        acc.set_title(0, 'Loading...')
        cancel_button = None
    return acc, cancel_button


def set_container(container, eewidget):
    # format elapsed
    elapsed = utils.format_elapsed(eewidget.processing_time)
    if isinstance(container, (Accordion, Tab)):
        if eewidget.local_type != eewidget.server_type:
            title = '{} (local) / {} (server) [{}]'.format(
                eewidget.local_type, eewidget.server_type, elapsed)
        else:
            title = '{} [{}]'.format(eewidget.server_type, elapsed)

        container.set_title(0, title)
        container.children = [eewidget.widget]
        container.selected_index = None


def cancel(thread, acc):
    """ Cancel a thread and set the title of the first element of accordion
       as CANCELLED """
    if thread.isAlive():
        thread.terminate()

    while True:
        if not thread.isAlive():
            acc.set_title(0, 'CANCELLED')
            break


def register(*names):
    """ Register dispatchers """
    def wrap(func):
        for name in names:
            DISPATCHERS[name] = func
        def wrap2(info):
            return func(info)
        return wrap2
    return wrap


class EEWidget(object):
    """ A simple class to hold the widget for dispatching and the type
    retrieved from the server """
    def __init__(self, widget, server_type, local_type, processing_time):
        self.widget = widget
        self.server_type = server_type
        self.local_type = local_type
        self.processing_time = processing_time


# GENERAL DISPATCHER
def dispatch(obj):
    """ General dispatcher """
    local_type = obj.__class__.__name__

    start = time()

    try:
        # Create Widget
        if belongToEE(obj):
            info = obj.getInfo()
            try:
                obj_type = info['type']
            except:
                obj_type = local_type

            if obj_type in DISPATCHERS.keys():
                widget = DISPATCHERS[obj_type](info)
            else:
                if isinstance(info, (dict,)):
                    widget = utils.create_accordion(info)
                else:
                    widget = HTML(str(info)+'<br/>')
        else:
            try:
                obj_type = obj['type']
            except:
                obj_type = local_type

            if obj_type in DISPATCHERS.keys():
                widget = DISPATCHERS[obj_type](obj)
            else:
                info = str(obj)
                widget = Label(info)

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        trace = traceback.format_exception(exc_type, exc_value,
                                           exc_traceback)

        # Widget
        widget = ErrorAccordion(e, trace)
        obj_type = 'ERROR'
        local_type = 'ERROR'

    end = time()
    dt = end-start

    return EEWidget(widget, obj_type, local_type, dt)


@register('str', 'String')
def string(info):
    """ Dispatch Strings """
    # info = new_line(info, 100)

    if isurl(info):
        if info[:3] == 'www':
            html = "<a href=http://{} target='_blank'>{}</a>"
        else:
            html = "<a href={} target='_blank'>{}</a>"
        widget = HTML(html.format(info, info))
    else:
        html = "{}"
        widget = HTML(html.format(info))

    return widget


@register('int', 'float', 'Number')
def number(info):
    """ Dispatch Numbers """
    return HTML(str(info))


@register('Dictionary', 'dict', 'List', 'list', 'tuple')
def iterable(info):
    """ Dispatch Iterables (list and dict) """
    widget = VBox()
    elements = []

    info = order(info)

    for key, val in info:
        if isinstance(val, (str, int, float)):
            try:
                length = len(val)
            except:
                length = 1

            if length < 500:
                html = '<div style="border:solid 1px; padding-left:5px;"><strong>{}:</strong> {}</div>'
                container = HTML(html.format(key, dispatch(val).widget.value))
            else:
                container = dispatch(val).widget
                container = Accordion([container])
                container.set_title(0, key)
                container.selected_index = None
        else:
            container, _ = create_container()
            eewidget = dispatch(val)
            set_container(container, eewidget)
            container = Accordion([container])
            container.set_title(0, key)
            container.selected_index = None
        elements.append(container)
    widget.children = elements

    return widget


@register('Image')
def image(info):
    """ Dispatch a Widget for an Image Object """
    # IMAGE
    image_id = info['id'] if 'id' in info else 'No Image ID'
    prop = info.get('properties')
    bands = info.get('bands')
    bands_names = [band.get('id') for band in bands]

    # BAND PRECISION
    bands_precision = []
    for band in bands:
        data = band.get('data_type')
        if data:
            precision = data.get('precision')
            bands_precision.append(precision)

    # BAND CRS
    bands_crs = []
    for band in bands:
        crs = band.get('crs')
        bands_crs.append(crs)

    # BAND MIN AND MAX
    bands_min = []
    for band in bands:
        data = band.get('data_type')
        if data:
            bmin = data.get('min')
            bands_min.append(bmin)

    bands_max = []
    for band in bands:
        data = band.get('data_type')
        if data:
            bmax = data.get('max')
            bands_max.append(bmax)

    # BANDS
    new_band_names = []
    zipped_data = zip(bands_names, bands_precision, bands_min, bands_max,
                      bands_crs)
    for name, ty, mn, mx, epsg in zipped_data:
        value = '<li><b>{}</b> ({}) {} to {} - {}</li>'.format(name,ty,
                                                               mn,mx,epsg)
        new_band_names.append(value)
    bands_wid = HTML('<ul>'+''.join(new_band_names)+'</ul>')

    # PROPERTIES
    if prop:
        prop_wid = dispatch(prop).widget
    else:
        prop_wid = HTML('Image has no properties')

    # ID
    header = HTML('<b>Image id:</b> {id} </br>'.format(id=image_id))

    acc = Accordion([bands_wid, prop_wid])
    acc.set_title(0, 'Bands')
    acc.set_title(1, 'Properties')
    acc.selected_index = None # thisp will unselect all

    return VBox([header, acc])


@register('Date')
def date(info):
    """ Dispatch a ee.Date """
    date = ee.Date(info.get('value'))
    return Label(date.format().getInfo())


@register('DateRange')
def daterange(info):
    """ Dispatch a DateRange """
    dates = info['dates']
    start = datetime.utcfromtimestamp(dates[0]/1000).isoformat()
    end = datetime.utcfromtimestamp(dates[1]/1000).isoformat()
    value = '{} to {}'.format(start, end)
    return Label(value)


@register('Point', 'LineString', 'LinearRing', 'Polygon', 'Rectangle',
          'MultiPoint', 'MultiLineString', 'MultiPolygon')
def geometry(info):
    """ Dispatch a ee.Geometry """
    coords = info.get('coordinates')
    typee = info.get('type')
    widget = Accordion()

    if typee in ['MultiPoint', 'MultiPolygon', 'MultiLineString']:
        inner_children = []
        for coord in coords:
            inner_children.append(Label(str(coord)))
        inner_acc = Accordion(inner_children)
        inner_acc.selected_index = None # this will unselect all
        for i, _ in enumerate(coords):
            inner_acc.set_title(i, str(i))
        children = [inner_acc]
    else:
        children = [Label(str(coords))]

    widget.children = children
    widget.set_title(0, 'coordinates')
    widget.selected_index = None
    return widget


@register('Feature')
def feature(info):
    """ Dispatch a ee.Feature """
    geom = info.get('geometry')
    geomtype = geom.get('type')
    props = info.get('properties')

    # Contruct an accordion with the geometries
    acc = geometry(geom)
    children = list(acc.children)

    # Properties
    if props:
        # dispatch properties
        prop_acc = dispatch(props)
    else:
        prop_acc = dispatch('Feature has no properties')

    # Append properties as a child
    children.append(prop_acc.widget)
    acc.set_title(1, 'properties')
    acc.children = children
    acc.selected_index = None

    # Geometry Type
    typewid = dispatch(geomtype)


    return acc


@register('FeatureCollection', 'ImageCollection')
def collection(info):
    """ Dispatch a Collection """
    try:
        fcid = info['id']
    except KeyError:
        try:
            fcid = info['properties']['system:index']
        except:
            fcid = None

    idlabel = HTML('<strong>Collection ID:</strong> {}'.format(fcid))

    # dispatch properties
    props = info.get('properties')
    if props:
        properties = dispatch(info['properties']) # acc
    else:
        properties = dispatch('{} has no properties'.format(info.get('type')))
    properties_acc = Accordion([properties.widget])
    properties_acc.set_title(0, 'Properties')
    properties_acc.selected_index = None

    # Features
    features = info['features']

    features_children = []
    for i, feat in enumerate(features):
        featacc = dispatch(feat).widget
        acc = Accordion([featacc])
        acc.set_title(0, str(i))
        acc.selected_index = None
        features_children.append(acc)

    features_wid = VBox(features_children)
    features_acc = Accordion([features_wid])
    title = 'Features' if info['type'] == 'FeatureCollection' else 'Images'
    features_acc.set_title(0, title)
    features_acc.selected_index = None

    if info['type'] == 'FeatureCollection':
        # columns
        columns = dispatch(info['columns']).widget # acc
        columns_acc = Accordion([columns])
        columns_acc.set_title(0, 'Columns')
        columns_acc.selected_index = None

        widgets = [idlabel, columns_acc, properties_acc, features_acc]
    else:
        widgets = [idlabel, properties_acc, features_acc]

    return VBox(widgets)

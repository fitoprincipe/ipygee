# coding=utf-8

""" Dispatch methods for different EE Object types

The dispatcher functions must take as single argument the information return
by ee.ComputedObject.getInfo() and process it

"""

import ee
from ipywidgets import *
from . import utils
from geetools.ui.dispatcher import belongToEE


class EEWidget(object):
    """ A simple class to hold the widget for dispatching and the type
    retrieved from the server """
    def __init__(self, widget, server_type, local_type):
        self.widget = widget
        self.server_type = server_type
        self.local_type = local_type


# GENERAL DISPATCHER
def dispatch(eeobject):
    """ General dispatcher """
    info = eeobject.getInfo()
    local_type = eeobject.__class__.__name__
    try:
        server_type = info.get('type')
    except AttributeError:
        server_type = local_type

    # Create Widget
    if belongToEE(eeobject):
        # DISPATCH!!
        if server_type == 'Image':
            widget = dispatchImage(info)
        elif server_type == 'Date':
            widget = dispatchDate(info)
        elif server_type == 'DateRange':
            widget = dispatchDaterange(info)
        # ADD MORE ABOVE ME!
        else:
            info = eeobject.getInfo()
            if isinstance(info, (dict,)):
                widget = utils.create_accordion(info)
            else:
                widget = HTML(str(info)+'<br/>')
    else:
        info = str(eeobject)
        widget = Label(info)

    return EEWidget(widget, server_type, local_type)


def dispatchImage(info):
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
        new_properties = []
        for key, val in prop.items():
            value = '<li><b>{}</b>: {}</li>'.format(key, val)
            new_properties.append(value)
        prop_wid = HTML('<ul>'+''.join(new_properties)+'</ul>')
    else:
        prop_wid = HTML('Image has no properties')

    # ID
    header = HTML('<b>Image id:</b> {id} </br>'.format(id=image_id))

    acc = Accordion([bands_wid, prop_wid])
    acc.set_title(0, 'Bands')
    acc.set_title(1, 'Properties')
    acc.selected_index = None # thisp will unselect all

    return VBox([header, acc])


def dispatchDate(info):
    """ Dispatch a ee.Date """
    return Label(info)


def dispatchDaterange(info):
    """ Dispatch a DateRange """

    start = ee.Date(info.get('dates')[0]).format().getInfo()
    end = ee.Date(info.get('dates')[0]).format().getInfo()
    value = '{} to {}'.format(start, end)
    return Label(value)

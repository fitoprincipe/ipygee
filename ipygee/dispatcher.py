# coding=utf-8

""" Dispatch methods for different EE Object types """

import ee
from ipywidgets import *
from . import utils
from geetools.ui.dispatcher import belongToEE


# GENERAL DISPATCHER
def dispatch(eeobject):
    """ General dispatcher """
    if belongToEE(eeobject):
        # DISPATCH!!
        if isinstance(eeobject, (ee.Image,)):
            return dispatchImage(eeobject)
        elif isinstance(eeobject, (ee.Date,)):
            return dispatchDate(eeobject)
        elif isinstance(eeobject, (ee.DateRange,)):
            return dispatchDaterange(eeobject)
        # ADD MORE ABOVE ME!
        else:
            info = eeobject.getInfo()
            if isinstance(info, (dict,)):
                return utils.create_accordion(info)
            else:
                return HTML(str(info)+'<br/>')
    else:
        info = str(eeobject)
        return Label(info)


def dispatchImage(image):
    """ Dispatch a Widget for an Image Object """
    info = image.getInfo()

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


def dispatchDate(date):
    """ Dispatch a ee.Date """
    info = date.format().getInfo()
    return Label(info)


def dispatchDaterange(daterange):
    """ Dispatch a DateRange """
    start = daterange.start().format().getInfo()
    end = daterange.end().format().getInfo()
    value = '{} to {}'.format(start, end)

    return Label(value)

# coding=utf-8

""" Preview widget """

import requests
from geetools import tools
import base64
from ipywidgets import HTML, Label, Accordion
import threading
from time import time
from . import utils

CONFIG = {'do_async': True}


def image(image, region=None, visualization=None, name=None,
          dimensions=(500, 500), do_async=None):
    """ Preview an Earth Engine Image """
    if do_async is None:
        do_async = CONFIG.get('do_async')

    start = time()

    if name:
        label = '{} (Image)'.format(name)
        loading = 'Loading {} preview...'.format(name)
    else:
        label = 'Image Preview'
        loading = 'Loading preview...'

    formatdimension = "x".join([str(d) for d in dimensions])

    wid = Accordion([Label(loading)])
    wid.set_title(0, loading)

    def compute(image, region, visualization):
        if not region:
            region = tools.geometry.getRegion(image)
        else:
            region = tools.geometry.getRegion(region)
        params = dict(dimensions=formatdimension, region=region)
        if visualization:
            params.update(visualization)
        url = image.getThumbURL(params)
        req = requests.get(url)
        content = req.content
        rtype = req.headers['Content-type']
        if rtype in ['image/jpeg', 'image/png']:
            img64 = base64.b64encode(content).decode('utf-8')
            src = '<img src="data:image/png;base64,{}"></img>'.format(img64)
            result = HTML(src)
        else:
            result = Label(content.decode('utf-8'))

        return result

    def setAccordion(acc):
        widget = compute(image, region, visualization)
        end = time()
        elapsed = end-start
        acc.children = [widget]
        elapsed = utils.format_elapsed(elapsed)
        acc.set_title(0, '{} [{}]'.format(label, elapsed))

    if do_async:
        thread = threading.Thread(target=setAccordion, args=(wid,))
        thread.start()
    else:
        setAccordion(wid)

    return wid


def set_preview_async(do_async):
    """ Set the global async for eprint """
    CONFIG['do_async'] = do_async
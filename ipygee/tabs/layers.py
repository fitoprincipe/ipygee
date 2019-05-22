# coding=utf-8

""" Layers widget for Map tab """

from ..widgets import RealBox
from ipywidgets import *
from ..threading import Thread
from traitlets import *
from .. import utils


class FloatBandWidget(HBox):
    min = Float(0)
    max = Float(1)

    def __init__(self, **kwargs):
        super(FloatBandWidget, self).__init__(**kwargs)
        self.minWid = FloatText(value=self.min, description='min')
        self.maxWid = FloatText(value=self.max, description='max')

        self.children = [self.minWid, self.maxWid]

        self.observe(self._ob_min, names=['min'])
        self.observe(self._ob_max, names=['max'])

    def _ob_min(self, change):
        new = change['new']
        self.minWid.value = new

    def _ob_max(self, change):
        new = change['new']
        self.maxWid.value = new


class LayersWidget(RealBox):
    def __init__(self, map=None, **kwargs):
        super(LayersWidget, self).__init__(**kwargs)
        self.map = map
        self.selector = Select()

        # define init EELayer
        self.EELayer = None

        # Buttons
        self.center = Button(description='Center')
        self.center.on_click(self.onClickCenter)

        self.remove = Button(description='Remove')
        self.remove.on_click(self.onClickRemove)

        self.show_prop = Button(description='Show Object')
        self.show_prop.on_click(self.onClickShowObject)

        self.vis = Button(description='Visualization')
        self.vis.on_click(self.onClickVis)

        self.move_up = Button(description='Move up')
        self.move_up.on_click(self.onUp)

        self.move_down = Button(description='Move down')
        self.move_down.on_click(self.onDown)

        # Buttons Group 1
        self.group1 = VBox([self.center, self.remove,
                            self.vis, self.show_prop])

        # Buttons Group 2
        self.group2 = VBox([self.move_up, self.move_down])

        # self.children = [self.selector, self.group1]
        self.items = [[self.selector, self.group1, self.group2]]

        self.selector.observe(self.handle_selection, names='value')

    def onUp(self, button=None):
        if self.EELayer:
            self.map.moveLayer(self.layer.name, 'up')

    def onDown(self, button=None):
        if self.EELayer:
            self.map.moveLayer(self.layer.name, 'down')

    def handle_selection(self, change):
        new = change['new']
        self.EELayer = new

        # set original display
        self.items = [[self.selector, self.group1, self.group2]]

        if new:
            self.layer = new['layer']
            self.obj = new['object']
            self.ty = new['type']
            self.vis = new['visParams']

    def onClickShowObject(self, button=None):
        if self.EELayer:
            loading = HTML('Loading <b>{}</b>...'.format(self.layer.name))
            widget = VBox([loading])
            thread = Thread(target=utils.create_async_output,
                            args=(self.obj, widget))
            self.items = [[self.selector, self.group1],
                          [widget]]
            thread.start()

    def onClickCenter(self, button=None):
        if self.EELayer:
            self.map.centerObject(self.obj)

    def onClickRemove(self, button=None):
        if self.EELayer:
            self.map.removeLayer(self.layer.name)

    def onClickVis(self, button=None):
        if self.EELayer:
            # options
            selector = self.selector
            group1 = self.group1

            # map
            map = self.map
            layer_name = self.layer.name
            image = self.obj

            # Image Bands
            try:
                info = self.obj.getInfo()
            except Exception as e:
                self.items = [[self.selector, self.group1],
                              [HTML(str(e))]]
                return

            # IMAGES
            if self.ty == 'Image':
                ### image data ###
                bands = info['bands']
                imbands = [band['id'] for band in bands]
                bands_type = [band['data_type']['precision'] for band in bands]
                bands_min = []
                bands_max = []
                # as float bands don't hava an specific range, reduce region to get the
                # real range
                if 'float' in bands_type:
                    try:
                        minmax = image.reduceRegion(ee.Reducer.minMax())
                        for band in bands:
                            bandname = band['id']
                            try:
                                tmin = minmax.get('{}_min'.format(bandname)).getInfo() # 0
                                tmax = minmax.get('{}_max'.format(bandname)).getInfo() # 1
                            except:
                                tmin = 0
                                tmax = 1
                            bands_min.append(tmin)
                            bands_max.append(tmax)
                    except:
                        for band in bands:
                            dt = band['data_type']
                            try:
                                tmin = dt['min']
                                tmax = dt['max']
                            except:
                                tmin = 0
                                tmax = 1
                            bands_min.append(tmin)
                            bands_max.append(tmax)
                else:
                    for band in bands:
                        dt = band['data_type']
                        try:
                            tmin = dt['min']
                            tmax = dt['max']
                        except:
                            tmin = 0
                            tmax = 1
                        bands_min.append(tmin)
                        bands_max.append(tmax)


                # dict of {band: min} and {band:max}
                min_dict = dict(zip(imbands, bands_min))
                max_dict = dict(zip(imbands, bands_max))
                ######

                # Layer data
                layer_data = self.map.EELayers[layer_name]
                visParams = layer_data['visParams']

                # vis bands
                visBands = visParams['bands'].split(',')

                # vis min
                visMin = visParams['min']
                if isinstance(visMin, str):
                    visMin = [float(vis) for vis in visMin.split(',')]
                else:
                    visMin = [visMin]

                # vis max
                visMax = visParams['max']
                if isinstance(visMax, str):
                    visMax = [float(vis) for vis in visMax.split(',')]
                else:
                    visMax = [visMax]

                # dropdown handler
                def handle_dropdown(band_slider):
                    def wrap(change):
                        new = change['new']
                        band_slider.min = min_dict[new]
                        band_slider.max = max_dict[new]
                    return wrap

                def slider_1band(float=False, name='band'):
                    ''' Create the widget for one band '''
                    # get params to set in slider and dropdown
                    vismin = visMin[0]
                    vismax = visMax[0]
                    band = visBands[0]

                    drop = Dropdown(description=name, options=imbands, value=band)

                    if float:
                        slider = FloatBandWidget(min=min_dict[drop.value],
                                                 max=max_dict[drop.value])
                    else:
                        slider = FloatRangeSlider(min=min_dict[drop.value],
                                                  max=max_dict[drop.value],
                                                  value=[vismin, vismax],
                                                  step=0.01)
                    # set handler
                    drop.observe(handle_dropdown(slider), names=['value'])

                    # widget for band selector + slider
                    band_slider = HBox([drop, slider])
                    # return VBox([band_slider], layout=Layout(width='500px'))
                    return band_slider

                def slider_3bands(float=False):
                    ''' Create the widget for one band '''
                    # get params to set in slider and dropdown
                    if len(visMin) == 1:
                        visminR = visminG = visminB = visMin[0]
                    else:
                        visminR = visMin[0]
                        visminG = visMin[1]
                        visminB = visMin[2]

                    if len(visMax) == 1:
                        vismaxR = vismaxG = vismaxB = visMax[0]
                    else:
                        vismaxR = visMax[0]
                        vismaxG = visMax[1]
                        vismaxB = visMax[2]

                    if len(visBands) == 1:
                        visbandR = visbandG = visbandB = visBands[0]
                    else:
                        visbandR = visBands[0]
                        visbandG = visBands[1]
                        visbandB = visBands[2]

                    drop = Dropdown(description='red', options=imbands, value=visbandR)
                    drop2 = Dropdown(description='green', options=imbands, value=visbandG)
                    drop3 = Dropdown(description='blue', options=imbands, value=visbandB)
                    slider = FloatRangeSlider(min=min_dict[drop.value],
                                              max=max_dict[drop.value],
                                              value=[visminR, vismaxR],
                                              step=0.01)
                    slider2 = FloatRangeSlider(min=min_dict[drop2.value],
                                               max=max_dict[drop2.value],
                                               value=[visminG, vismaxG],
                                               step=0.01)
                    slider3 = FloatRangeSlider(min=min_dict[drop3.value],
                                               max=max_dict[drop3.value],
                                               value=[visminB, vismaxB],
                                               step=0.01)
                    # set handlers
                    drop.observe(handle_dropdown(slider), names=['value'])
                    drop2.observe(handle_dropdown(slider2), names=['value'])
                    drop3.observe(handle_dropdown(slider3), names=['value'])

                    # widget for band selector + slider
                    band_slider = HBox([drop, slider])
                    band_slider2 = HBox([drop2, slider2])
                    band_slider3 = HBox([drop3, slider3])

                    return VBox([band_slider, band_slider2, band_slider3],
                                layout=Layout(width='700px'))

                # Create widget for 1 or 3 bands
                bands = RadioButtons(options=['1 band', '3 bands'],
                                     layout=Layout(width='80px'))

                # Create widget for band, min and max selection
                selection = slider_1band()

                # Apply button
                apply = Button(description='Apply', layout=Layout(width='100px'))

                # new row
                new_row = [bands, selection, apply]

                # update row of widgets
                def update_row_items(new_row):
                    self.items = [[selector, group1],
                                  new_row]

                # handler for radio button (1 band / 3 bands)
                def handle_radio_button(change):
                    new = change['new']
                    if new == '1 band':
                        # create widget
                        selection = slider_1band() # TODO
                        # update row of widgets
                        update_row_items([bands, selection, apply])
                    else:
                        red = slider_1band(name='red') # TODO
                        green = slider_1band(name='green')
                        blue = slider_1band(name='blue')
                        selection = VBox([red, green, blue])
                        # selection = slider_3bands()
                        update_row_items([bands, selection, apply])

                def handle_apply(button):
                    radio = self.items[1][0].value # radio button
                    vbox = self.items[1][1]
                    if radio == '1 band':  # 1 band
                        hbox_band = vbox.children[0].children

                        band = hbox_band[0].value
                        min = hbox_band[1].value[0]
                        max = hbox_band[1].value[1]

                        map.addLayer(image, {'bands':[band], 'min':min, 'max':max},
                                     layer_name)
                    else:  # 3 bands
                        hbox_bandR = vbox.children[0].children
                        hbox_bandG = vbox.children[1].children
                        hbox_bandB = vbox.children[2].children

                        bandR = hbox_bandR[0].value
                        bandG = hbox_bandG[0].value
                        bandB = hbox_bandB[0].value

                        minR = hbox_bandR[1].value[0]
                        minG = hbox_bandG[1].value[0]
                        minB = hbox_bandB[1].value[0]

                        maxR = hbox_bandR[1].value[1]
                        maxG = hbox_bandG[1].value[1]
                        maxB = hbox_bandB[1].value[1]

                        map.addLayer(image, {'bands':[bandR, bandG, bandB],
                                             'min':[float(minR), float(minG), float(minB)],
                                             'max':[float(maxR), float(maxG), float(maxB)]},
                                     layer_name)

                bands.observe(handle_radio_button, names='value')
                update_row_items(new_row)
                apply.on_click(handle_apply)
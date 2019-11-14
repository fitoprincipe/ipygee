# coding=utf-8

""" Display an interactive Map for Google Earth Engine using ipyleaflet """

import ee
import ipyleaflet
from ipywidgets import Layout, HTML, Accordion
from traitlets import *
from collections import OrderedDict
from .tasks import TaskManager
from .assets import AssetManager
from geetools import tools, utils
from IPython.display import display
from .tabs.layers import LayersWidget
from copy import copy
import traceback
from .maptools import *
from .widgets import ErrorAccordion
from .utils import *
import re


ZOOM_SCALES = {
    0: 156543, 1: 78271, 2: 39135, 3: 19567, 4: 9783, 5: 4891, 6: 2445,
    7: 1222, 8: 611, 9: 305, 10: 152, 11: 76, 12: 38, 13: 19, 14: 9, 15: 5,
    16: 2, 17: 1, 18: 0.5, 19: 0.3, 20: 0.15, 21: 0.07, 22: 0.03,
}


class Map(ipyleaflet.Map):
    tab_children_dict = Dict()
    EELayers = Dict()

    def __init__(self, tabs=('Inspector', 'Layers'), **kwargs):
        # Change defaults
        kwargs.setdefault('center', [0, 0])
        kwargs.setdefault('zoom', 2)
        kwargs.setdefault('scroll_wheel_zoom', True)
        kwargs.setdefault('max_zoom', 22)
        super(Map, self).__init__(**kwargs)
        self.is_shown = False

        # Width and Height
        self.width = kwargs.get('width', None)
        self.height = kwargs.get('height', None)
        self.setDimensions(self.width, self.height)

        # Correct base layer name
        baselayer = self.layers[0]
        baselayer.name = 'OpenStreetMap'
        self.layers = (baselayer,)

        # Dictionary of map's handlers
        self.handlers = {}

        # Dictonary to hold tab's widgets
        # (tab's name:widget)
        self.tab_names = []
        self.tab_children = []
        self.tab_children_dict = OrderedDict(zip(self.tab_names,
                                                 self.tab_children))

        # TABS
        # Tab widget
        self.tab_widget = Tab()
        # Handler for Tab
        self.tab_widget.observe(self.handle_change_tab)

        self.tabs = tabs
        if len(tabs) > 0:
            # TODO: create widgets only if are in tuple
            # Inspector Widget (Accordion)
            self.inspector_wid = CustomInspector()
            self.inspector_wid.main.selected_index = None # this will unselect all

            # Task Manager Widget
            task_manager = TaskManager()

            # Asset Manager Widget
            asset_manager = AssetManager(self)

            # Layers
            self.layers_widget = LayersWidget(map=self)

            widgets = {'Inspector': self.inspector_wid,
                       'Layers': self.layers_widget,
                       'Assets': asset_manager,
                       'Tasks': task_manager,
                       }
            handlers = {'Inspector': self.handle_inspector,
                        'Layers': None,
                        'Assets': None,
                        'Tasks': None,
                        }

            # Add tabs and handlers
            for tab in tabs:
                if tab in widgets.keys():
                    widget = widgets[tab]
                    handler = handlers[tab]
                    self.addTab(tab, handler, widget)
                else:
                    raise ValueError('Tab {} is not recognized. Choose one of {}'.format(tab, widgets.keys()))

            # First handler: Inspector
            self.on_interaction(self.handlers[tabs[0]])

        # As I cannot create a Geometry with a GeoJSON string I do a workaround
        self.draw_types = {'Polygon': ee.Geometry.Polygon,
                           'Point': ee.Geometry.Point,
                           'LineString': ee.Geometry.LineString,
                           }
        # create EELayers
        self.EELayers = OrderedDict()

    def _add_EELayer(self, name, data):
        """ Add a pair of name, data to EELayers. Data must be:

        - type: str
        - object: ee object
        - visParams: dict
        - layer: ipyleaflet layer

        """
        copyEELayers = copy(self.EELayers)
        copyEELayers[name] = data
        self.EELayers = copyEELayers

    def _remove_EELayer(self, name):
        """ remove layer from EELayers """
        copyEELayers = copy(self.EELayers)
        if name in copyEELayers:
            copyEELayers.pop(name)
        self.EELayers = copyEELayers

    def addBasemap(self, name, url, **kwargs):
        """ Add a basemap with the given URL """
        layer = ipyleaflet.TileLayer(url=url, name=name, base=True, **kwargs)
        self.add_layer(layer)

    def setDimensions(self, width=None, height=None):
        """ Set the dimensions for the map """
        def check(value, t):
            if value is None: return value
            if isinstance(value, (int, float)):
                return '{}px'.format(value)
            elif isinstance(value, (str,)):
                search = re.search('(\d+)', value).groups()
                intvalue = search[0]
                splitted = value.split(intvalue)
                units = splitted[1]
                if units == '%':
                    if t == 'width': return '{}%'.format(intvalue)
                    else: return None
                else:
                    return '{}px'.format(intvalue)
            else:
                msg = 'parameter {} of setDimensions must be int or str'
                raise ValueError(msg.format(t))
        self.layout = Layout(width=check(width, 'width'),
                             height=check(height, 'height'))

    def moveLayer(self, layer_name, direction='up'):
        """ Move one step up a layer """
        names = list(self.EELayers.keys())
        values = list(self.EELayers.values())

        if direction == 'up':
            dir = 1
        elif direction == 'down':
            dir = -1
        else:
            dir = 0

        if layer_name in names:  # if layer exists
            # index and value of layer to move_layer
            i = names.index(layer_name)
            condition = (i < len(names)-1) if dir == 1 else (i > 0)
            if condition:  # if layer is not in the edge
                ival = values[i]
                # new index for layer
                newi = i+dir
                # get index and value that already exist in the new index
                iname_before = names[newi]
                ival_before = values[newi]
                # Change order
                # set layer and value in the new index
                names[newi] = layer_name
                values[newi] = ival
                # set replaced layer and its value in the index of moving layer
                names[i] = iname_before
                values[i] = ival_before

                newlayers = OrderedDict(zip(names, values))
                self.EELayers = newlayers

    @observe('EELayers')
    def _ob_EELayers(self, change):
        new = change['new']
        proxy_layers = [l for l in self.layers if l.base == True]

        for val in new.values():
            layer = val['layer']
            proxy_layers.append(layer)

        self.layers = tuple(proxy_layers)

        # UPDATE INSPECTOR
        # Clear options
        self.inspector_wid.selector.options = {}
        # Add layer to the Inspector Widget
        self.inspector_wid.selector.options = new # self.EELayers

        # UPDATE LAYERS WIDGET
        # update Layers Widget
        self.layers_widget.selector.options = {}
        self.layers_widget.selector.options = new # self.EELayers

    @property
    def addedImages(self):
        return sum(
            [1 for val in self.EELayers.values() if val['type'] == 'Image'])

    @property
    def addedGeometries(self):
        return sum(
            [1 for val in self.EELayers.values() if val['type'] == 'Geometry'])

    def show(self, tabs=True, layer_control=True, draw_control=False,
             fullscreen=True):
        """ Show the Map on the Notebook """
        if not self.is_shown:
            if layer_control:
                # Layers Control
                lc = ipyleaflet.LayersControl()
                self.add_control(lc)
            if draw_control:
                # Draw Control
                dc = ipyleaflet.DrawControl(edit=False)
                dc.on_draw(self.handle_draw)
                self.add_control(dc)
            if fullscreen:
                # Control
                full_control = ipyleaflet.FullScreenControl()
                self.add_control(full_control)

            if tabs:
                display(self, self.tab_widget)
            else:
                display(self)
        else:
            if tabs:
                display(self, self.tab_widget)
            else:
                display(self)

        self.is_shown = True
        # Start with crosshair cursor
        self.default_style = {'cursor': 'crosshair'}

    def showTab(self, name):
        """ Show only a Tab Widget by calling its name. This is useful mainly
        in Jupyter Lab where you can see outputs in different tab_widget

        :param name: the name of the tab to show
        :type name: str
        """
        try:
            widget = self.tab_children_dict[name]
            display(widget)
        except:
            print('Tab not found')

    def addImage(self, image, visParams=None, name=None, show=True,
                 opacity=None, replace=True):
        """ Add an ee.Image to the Map

        :param image: Image to add to Map
        :type image: ee.Image
        :param visParams: visualization parameters. Can have the
            following arguments: bands, min, max.
        :type visParams: dict
        :param name: name for the layer
        :type name: str
        :return: the name of the added layer
        :rtype: str
        """
        # Check if layer exists
        if name in self.EELayers.keys():
            if not replace:
                return self.getLayer(name)
            else:
                # Get URL, attribution & vis params
                params = getImageTile(image, visParams, show, opacity)

                # Remove Layer
                self.removeLayer(name)
        else:
            # Get URL, attribution & vis params
            params = getImageTile(image, visParams, show, opacity)

        layer = ipyleaflet.TileLayer(url=params['url'],
                                     attribution=params['attribution'],
                                     name=name)

        EELayer = {'type': 'Image',
                   'object': image,
                   'visParams': params['visParams'],
                   'layer': layer}

        # self._add_EELayer(name, EELayer)
        # return name
        return EELayer

    def addMarker(self, marker, visParams=None, name=None, show=True,
                  opacity=None, replace=True,
                  inspect={'data':None, 'reducer':None, 'scale':None}):
        """ General method to add Geometries, Features or FeatureCollections
        as Markers """

        if isinstance(marker, ee.Geometry):
            self.addGeometry(marker, visParams, name, show, opacity, replace,
                             inspect)

        elif isinstance(marker, ee.Feature):
            self.addFeature(marker, visParams, name, show, opacity, replace,
                            inspect)

        elif isinstance(marker, ee.FeatureCollection):
            geometry = marker.geometry()
            self.addGeometry(marker, visParams, name, show, opacity, replace,
                             inspect)

    def addFeature(self, feature, visParams=None, name=None, show=True,
                   opacity=None, replace=True,
                   inspect={'data':None, 'reducer':None, 'scale':None}):
        """ Add a Feature to the Map

        :param feature: the Feature to add to Map
        :type feature: ee.Feature
        :param visParams:
        :type visParams: dict
        :param name: name for the layer
        :type name: str
        :param inspect: when adding a geometry or a feature you can pop up data
            from a desired layer. Params are:
            :data: the EEObject where to get the data from
            :reducer: the reducer to use
            :scale: the scale to reduce
        :type inspect: dict
        :return: the name of the added layer
        :rtype: str
        """
        thename = name if name else 'Feature {}'.format(self.addedGeometries)

        # Check if layer exists
        if thename in self.EELayers.keys():
            if not replace:
                print("Layer with name '{}' exists already, please choose another name".format(thename))
                return
            else:
                self.removeLayer(thename)

        params = getGeojsonTile(feature, thename, inspect)
        layer = ipyleaflet.GeoJSON(data=params['geojson'],
                                   name=thename,
                                   popup=HTML(params['pop']))

        self._add_EELayer(thename, {'type': 'Feature',
                                    'object': feature,
                                    'visParams': None,
                                    'layer': layer})
        return thename

    def addGeometry(self, geometry, visParams=None, name=None, show=True,
                    opacity=None, replace=True,
                    inspect={'data':None, 'reducer':None, 'scale':None}):
        """ Add a Geometry to the Map

        :param geometry: the Geometry to add to Map
        :type geometry: ee.Geometry
        :param visParams:
        :type visParams: dict
        :param name: name for the layer
        :type name: str
        :param inspect: when adding a geometry or a feature you can pop up data
            from a desired layer. Params are:
            :data: the EEObject where to get the data from
            :reducer: the reducer to use
            :scale: the scale to reduce
        :type inspect: dict
        :return: the name of the added layer
        :rtype: str
        """
        thename = name if name else 'Geometry {}'.format(self.addedGeometries)

        # Check if layer exists
        if thename in self.EELayers.keys():
            if not replace:
                print("Layer with name '{}' exists already, please choose another name".format(thename))
                return
            else:
                self.removeLayer(thename)

        params = getGeojsonTile(geometry, thename, inspect)
        layer = ipyleaflet.GeoJSON(data=params['geojson'],
                                   name=thename,
                                   popup=HTML(params['pop']))

        self._add_EELayer(thename, {'type': 'Geometry',
                                    'object': geometry,
                                    'visParams':None,
                                    'layer': layer})
        return thename

    def addFeatureLayer(self, feature, visParams=None, name=None, show=True,
                        opacity=None, replace=True):
        """ Paint a Feature on the map, but the layer underneath is the
        actual added Feature """

        visParams = visParams if visParams else {}

        if isinstance(feature, ee.Feature):
            ty = 'Feature'
        elif isinstance(feature, ee.FeatureCollection):
            ty = 'FeatureCollection'
        else:
            print('The object is not a Feature or FeatureCollection')
            return

        fill_color = visParams.get('fill_color', None)

        if 'outline_color' in visParams:
            out_color = visParams['outline_color']
        elif 'border_color' in visParams:
            out_color = visParams['border_color']
        else:
            out_color = 'black'

        outline = visParams.get('outline', 2)

        proxy_layer = paint(feature, out_color, fill_color, outline)

        thename = name if name else '{} {}'.format(ty, self.addedGeometries)

        img_params = {'bands':['vis-red', 'vis-green', 'vis-blue'],
                      'min': 0, 'max':255}

        # Check if layer exists
        if thename in self.EELayers.keys():
            if not replace:
                print("{} with name '{}' exists already, please choose another name".format(ty, thename))
                return
            else:
                # Get URL, attribution & vis params
                params = getImageTile(proxy_layer, img_params, show, opacity)

                # Remove Layer
                self.removeLayer(thename)
        else:
            # Get URL, attribution & vis params
            params = getImageTile(proxy_layer, img_params, show, opacity)

        layer = ipyleaflet.TileLayer(url=params['url'],
                                     attribution=params['attribution'],
                                     name=thename)

        self._add_EELayer(thename, {'type': ty,
                                    'object': feature,
                                    'visParams': visParams,
                                    'layer': layer})
        return thename

    def addMosaic(self, collection, visParams=None, name=None, show=False,
                  opacity=None, replace=True):
        """ Add an ImageCollection to EELayer and its mosaic to the Map.
        When using the inspector over this layer, it will print all values from
        the collection """
        proxy = ee.ImageCollection(collection).sort('system:time_start')
        mosaic = ee.Image(proxy.mosaic())

        self.addImage(mosaic, visParams, name, show, opacity, replace)
        # modify EELayer
        # EELayer['type'] = 'ImageCollection'
        # EELayer['object'] = ee.ImageCollection(collection)
        # return EELayer

    def addImageCollection(self, collection, visParams=None,
                           namePattern='{id}', show=False, opacity=None,
                           datePattern='yyyyMMdd', replace=True):
        """ Add every Image of an ImageCollection to the Map

        :param collection: the ImageCollection
        :type collection: ee.ImageCollection
        :param visParams: visualization parameter for each image. See `addImage`
        :type visParams: dict
        :param namePattern: the name pattern (uses geetools.utils.makeName)
        :type namePattern: str
        :param show: If True, adds and shows the Image, otherwise only add it
        :type show: bool
        """
        size = collection.size()
        collist = collection.toList(size)
        n = 0
        while True:
            try:
                img = ee.Image(collist.get(n))
                extra = dict(position=n)
                name = utils.makeName(img, namePattern, datePattern, extra=extra)
                self.addLayer(img, visParams, name.getInfo(), show, opacity,
                              replace=replace)
                n += 1
            except:
                break

    def addLayer(self, eeObject, visParams=None, name=None, show=True,
                 opacity=None, replace=True, **kwargs):
        """ Adds a given EE object to the map as a layer.

        :param eeObject: Earth Engine object to add to map
        :type eeObject: ee.Image || ee.Geometry || ee.Feature
        :param replace: if True, if there is a layer with the same name, this
            replace that layer.
        :type replace: bool

        For ee.Image and ee.ImageCollection see `addImage`
        for ee.Geometry and ee.Feature see `addGeometry`
        """
        if name in self.EELayers.keys():
            return None

        visParams = visParams if visParams else {}

        # CASE: ee.Image
        if isinstance(eeObject, ee.Image):
            image_name = name if name else 'Image {}'.format(self.addedImages)
            EELayer = self.addImage(eeObject, visParams=visParams,
                                    name=image_name, show=show,
                                    opacity=opacity, replace=replace)

            self._add_EELayer(image_name, EELayer)

        # CASE: ee.Geometry
        elif isinstance(eeObject, ee.Geometry):
            geom = eeObject if isinstance(eeObject, ee.Geometry) else eeObject.geometry()
            kw = {'visParams':visParams, 'name':name, 'show':show, 'opacity':opacity}
            if kwargs.get('inspect'): kw.setdefault('inspect', kwargs.get('inspect'))
            self.addGeometry(geom, replace=replace, **kw)

        # CASE: ee.Feature & ee.FeatureCollection
        elif isinstance(eeObject, ee.Feature) or isinstance(eeObject, ee.FeatureCollection):
            feat = eeObject
            kw = {'visParams':visParams, 'name':name, 'show':show, 'opacity':opacity}
            self.addFeatureLayer(feat, replace=replace, **kw)

        # CASE: ee.ImageCollection
        elif isinstance(eeObject, ee.ImageCollection):
            thename = name if name else 'ImageCollection {}'.format(self.addedImages)
            EELayer = self.addMosaic(eeObject, visParams, thename, show,
                                     opacity, replace)
            self._add_EELayer(thename, EELayer)
        else:
            print("`addLayer` doesn't support adding {} objects to the map".format(type(eeObject)))


    def removeLayer(self, name):
        """ Remove a layer by its name """
        if name in self.EELayers.keys():
            self._remove_EELayer(name)
        else:
            print('Layer {} is not present in the map'.format(name))
            return

    # GETTERS
    def getLayer(self, name):
        """ Get a layer by its name

        :param name: the name of the layer
        :type name: str
        :return: The complete EELayer which is a dict of

            :type: the type of the layer
            :object: the EE Object associated with the layer
            :visParams: the visualization parameters of the layer
            :layer: the TileLayer added to the Map (ipyleaflet.Map)

        :rtype: dict
        """
        if name in self.EELayers:
            layer = self.EELayers[name]
            return layer
        else:
            print('Layer {} is not present in the map'.format(name))
            return

    def getObject(self, name):
        """ Get the EE Object from a layer's name """
        obj = self.getLayer(name)['object']
        return obj

    def getVisParams(self, name):
        """ Get the Visualization Parameters from a layer's name """
        vis = self.getLayer(name)['visParams']
        return vis

    def getLayerURL(self, name):
        """ Get the layer URL by name """
        layer = self.getLayer(name)
        tile = layer['layer']
        return tile.url

    def getCenter(self):
        """ Returns the coordinates at the center of the map.

        No arguments.
        Returns: Geometry.Point

        :return:
        """
        center = self.center
        coords = inverseCoordinates(center)
        return ee.Geometry.Point(coords)

    def getBounds(self, asGeoJSON=True):
        """ Returns the bounds of the current map view, as a list in the
        format [west, south, east, north] in degrees.

        Arguments:
        asGeoJSON (Boolean, optional):
        If true, returns map bounds as GeoJSON.

        Returns: GeoJSONGeometry|List<Number>|String
        """
        bounds = inverseCoordinates(self.bounds)
        if asGeoJSON:
            return ee.Geometry.Rectangle(bounds)
        else:
            return bounds

    def centerObject(self, eeObject, zoom=None, method=1):
        """ Center an eeObject

        :param eeObject:
        :param zoom:
        :param method: experimetal methods to estimate zoom for fitting bounds
            Currently: 1 or 2
        :type: int
        """
        bounds = getBounds(eeObject)
        if bounds:
            try:
                inverse = inverseCoordinates(bounds)
                centroid = ee.Geometry.Polygon(inverse) \
                    .centroid().getInfo()['coordinates']
            except:
                centroid = [0, 0]

            self.center = inverseCoordinates(centroid)
            if zoom:
                self.zoom = zoom
            else:
                self.zoom = getZoom(bounds, method)

    def _update_tab_children(self):
        """ Update Tab children from tab_children_dict """
        # Set tab_widget children
        self.tab_widget.children = tuple(self.tab_children_dict.values())
        # Set tab_widget names
        for i, name in enumerate(self.tab_children_dict.keys()):
            self.tab_widget.set_title(i, name)

    def addTab(self, name, handler=None, widget=None):
        """ Add a Tab to the Panel. The handler is for the Map

        :param name: name for the new tab
        :type name: str
        :param handler: handle function for the new tab. Arguments of the
        function are:

          - type: the type of the event (click, mouseover, etc..)
          - coordinates: coordinates where the event occurred [lon, lat]
          - widget: the widget inside the Tab
          - map: the Map instance

        :param widget: widget inside the Tab. Defaults to HTML('')
        :type widget: ipywidgets.Widget
        """
        # Widget
        wid = widget if widget else HTML('')
        # Get tab's children as a list
        # tab_children = list(self.tab_widget.children)
        tab_children = self.tab_children_dict.values()
        # Get a list of tab's titles
        # titles = [self.tab_widget.get_title(i) for i, child in enumerate(tab_children)]
        titles = self.tab_children_dict.keys()
        # Check if tab already exists
        if name not in titles:
            ntabs = len(tab_children)

            # UPDATE DICTS
            # Add widget as a new children
            self.tab_children_dict[name] = wid
            # Set the handler for the new tab
            if handler:
                def proxy_handler(f):
                    def wrap(**kwargs):
                        # Add widget to handler arguments
                        kwargs['widget'] = self.tab_children_dict[name]
                        coords = kwargs['coordinates']
                        kwargs['coordinates'] = inverseCoordinates(coords)
                        kwargs['map'] = self
                        return f(**kwargs)
                    return wrap
                self.handlers[name] = proxy_handler(handler)
            else:
                self.handlers[name] = handler

            # Update tab children
            self._update_tab_children()
        else:
            print('Tab {} already exists, please choose another name'.format(name))

    def removeTab(self, name):
        """ Remove a tab by its name """
        children = self.tab_children_dict.keys()
        if name in children:
            self.tab_children_dict.pop(name)
        self._update_tab_children()

    def handle_change_tab(self, change):
        """ Handle function to trigger when tab changes """
        # Remove all handlers
        if change['name'] == 'selected_index':
            old = change['old']
            new = change['new']
            old_name = self.tab_widget.get_title(old)
            new_name = self.tab_widget.get_title(new)
            # Remove all handlers
            for handl in self.handlers.values():
                self.on_interaction(handl, True)
            # Set new handler if not None
            if new_name in self.handlers.keys():
                handler = self.handlers[new_name]
                if handler:
                    self.on_interaction(handler)

            # Set cursor type
            if new_name == 'Inspector':
                self.default_style = {'cursor': 'crosshair'}
            else:
                self.default_style = {'cursor': 'grab'}

    def handle_inspector(self, **change):
        """ Handle function for the Inspector Widget """
        # Get click coordinates
        coords = change['coordinates']

        point_name = 'point inspect at {}'.format(coords)
        # Widget for adding/removing the point at click
        def point_widget(coords):
            coords = inverseCoordinates(coords)
            add_button = Button(description='ADD', tooltip='add point to map')
            rem_button = Button(description='REMOVE',
                                tooltip='remove point from map')

            def add_func(button=None):
                p = ipyleaflet.Marker(name=point_name,
                                      location=coords,
                                      draggable=False)

                self._add_EELayer(point_name, {
                    'type': 'temp',
                    'object': None,
                    'visParams': None,
                    'layer': p
                })

            def remove_func(button=None):
                self._remove_EELayer(point_name)

            add_button.on_click(add_func)
            rem_button.on_click(remove_func)

            return HBox([add_button, rem_button])

        event = change['type'] # event type
        if event == 'click':  # If the user clicked
            # create a point where the user clicked
            point = ee.Geometry.Point(coords)

            # Get widget
            thewidget = change['widget'].main  # Accordion

            # First Accordion row text (name)
            first = 'Point {} at {} zoom'.format(coords, self.zoom)
            namelist = [first]
            # wids4acc = [HTML('')] # first row has no content
            wids4acc = [point_widget(coords)]

            # Get only Selected Layers in the Inspector Selector
            selected_layers = dict(zip(self.inspector_wid.selector.label,
                                       self.inspector_wid.selector.value))

            length = len(selected_layers.keys())
            i = 1

            for name, obj in selected_layers.items(): # for every added layer
                # Clear children // Loading
                thewidget.children = [HTML('wait a second please..')]
                thewidget.set_title(0, 'Loading {} of {}...'.format(i, length))
                i += 1

                # Image
                if obj['type'] == 'Image':
                    # Get the image's values
                    try:
                        image = obj['object']
                        values = tools.image.getValue(image, point,
                                                      scale=ZOOM_SCALES[self.zoom],
                                                      side='client')
                        values = tools.dictionary.sort(values)
                        # Create the content
                        img_html = ''
                        for band, value in values.items():
                            img_html += '<b>{}</b>: {}</br>'.format(band,
                                                                    value)
                        wid = HTML(img_html)
                        # append widget to list of widgets
                        wids4acc.append(wid)
                        namelist.append(name)
                    except Exception as e:
                        # wid = HTML(str(e).replace('<','{').replace('>','}'))
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        trace = traceback.format_exception(exc_type, exc_value,
                                                           exc_traceback)
                        wid = ErrorAccordion(e, trace)
                        wids4acc.append(wid)
                        namelist.append('ERROR at layer {}'.format(name))

                # ImageCollection
                if obj['type'] == 'ImageCollection':
                    # Get the values from all images
                    try:
                        collection = obj['object']
                        values = tools.imagecollection.getValues(
                            collection, point, scale=ZOOM_SCALES[self.zoom],
                            properties=['system:time_start'],
                            side='client')

                        # header
                        allbands = [val.keys() for bands, val in values.items()]
                        bands = []
                        for bandlist in allbands:
                            for band in bandlist:
                                if band not in bands:
                                    bands.append(band)

                        header = ['image']+bands

                        # rows
                        rows = []
                        for imgid, val in values.items():
                            row = ['']*len(header)
                            row[0] = str(imgid)
                            for bandname, bandvalue in val.items():
                                pos = header.index(bandname) if bandname in header else None
                                if pos:
                                    row[pos] = str(bandvalue)
                            rows.append(row)

                        # Create the content
                        html = createHTMLTable(header, rows)
                        wid = HTML(html)
                        # append widget to list of widgets
                        wids4acc.append(wid)
                        namelist.append(name)
                    except Exception as e:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        trace = traceback.format_exception(exc_type, exc_value,
                                                           exc_traceback)
                        wid = ErrorAccordion(e, trace)
                        wids4acc.append(wid)
                        namelist.append('ERROR at layer {}'.format(name))

                # Features
                if obj['type'] == 'Feature':
                    try:
                        feat = obj['object']
                        feat_geom = feat.geometry()
                        if feat_geom.contains(point).getInfo():
                            info = featurePropertiesOutput(feat)
                            wid = HTML(info)
                            # append widget to list of widgets
                            wids4acc.append(wid)
                            namelist.append(name)
                    except Exception as e:
                        # wid = HTML(str(e).replace('<','{').replace('>','}'))
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        trace = traceback.format_exception(exc_type, exc_value,
                                                           exc_traceback)
                        wid = ErrorAccordion(e, trace)
                        wids4acc.append(wid)
                        namelist.append('ERROR at layer {}'.format(name))

                # FeatureCollections
                if obj['type'] == 'FeatureCollection':
                    try:
                        fc = obj['object']
                        filtered = fc.filterBounds(point)
                        if filtered.size().getInfo() > 0:
                            feat = ee.Feature(filtered.first())
                            info = featurePropertiesOutput(feat)
                            wid = HTML(info)
                            # append widget to list of widgets
                            wids4acc.append(wid)
                            namelist.append(name)
                    except Exception as e:
                        wid = HTML(str(e).replace('<','{').replace('>','}'))
                        wids4acc.append(wid)
                        namelist.append('ERROR at layer {}'.format(name))

            # Set children and children's name of inspector widget
            thewidget.children = wids4acc
            for i, n in enumerate(namelist):
                thewidget.set_title(i, n)

    def handle_object_inspector(self, **change):
        """ Handle function for the Object Inspector Widget

        DEPRECATED
        """
        event = change['type'] # event type
        thewidget = change['widget']
        if event == 'click':  # If the user clicked
            # Clear children // Loading
            thewidget.children = [HTML('wait a second please..')]
            thewidget.set_title(0, 'Loading...')

            widgets = []
            i = 0

            for name, obj in self.EELayers.items(): # for every added layer
                the_object = obj['object']
                try:
                    properties = the_object.getInfo()
                    wid = create_accordion(properties) # Accordion
                    wid.selected_index = None # this will unselect all
                except Exception as e:
                    wid = HTML(str(e))
                widgets.append(wid)
                thewidget.set_title(i, name)
                i += 1

            thewidget.children = widgets

    def handle_draw(self, dc_widget, action, geo_json):
        """ Handles drawings """
        ty = geo_json['geometry']['type']
        coords = geo_json['geometry']['coordinates']
        geom = self.draw_types[ty](coords)
        if action == 'created':
            self.addGeometry(geom)
            dc_widget.clear()
        elif action == 'deleted':
            for key, val in self.EELayers.items():
                if geom == val:
                    self.removeLayer(key)

class CustomInspector(HBox):
    def __init__(self, **kwargs):
        desc = 'Select one or more layers'
        super(CustomInspector, self).__init__(description=desc, **kwargs)
        self.selector = SelectMultiple()
        self.main = Accordion()
        self.children = [self.selector, self.main]


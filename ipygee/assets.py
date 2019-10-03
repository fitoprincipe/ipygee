# coding=utf-8

""" Google Earth Engine Asset Manager """

from ipywidgets import *
import ee
from .threading import Thread
from geetools import batch
from .widgets import *
from . import utils
from . import dispatcher


class AssetManager(VBox):
    """ Asset Manager Widget """
    POOL_SIZE = 5

    def __init__(self, map=None, **kwargs):
        super(AssetManager, self).__init__(**kwargs)
        # Thumb height
        self.thumb_height = kwargs.get('thumb_height', 300)
        self.root_path = ee.data.getAssetRoots()[0]['id']

        # Map
        self.map = map

        # Header
        self.user_label = HTML('<strong>User:</strong> {}'.format(self.root_path))
        self.reload_button = Button(description='Reload')
        self.add2map = Button(description='Add to Map')
        self.delete = Button(description='Delete Selected')
        header_children = [self.reload_button, self.delete]

        # Add2map only if a Map has been passed
        if self.map:
            header_children.append(self.add2map)

        self.header = HBox(header_children)

        # Reload handler
        def reload_handler(button):
            new_accordion = self.core(self.root_path)
            # Set VBox children
            self.children = [self.header, new_accordion]

        # add2map handler
        def add2map_handler(themap):
            def wrap(button):
                selected_rows = self.get_selected()
                for asset, ty in selected_rows.items():
                    if ty == 'Image':
                        im = ee.Image(asset)
                        themap.addLayer(im, {}, asset)
                    elif ty == 'ImageCollection':
                        col = ee.ImageCollection(asset)
                        themap.addLayer(col)
            return wrap

        # Set reload handler
        # self.reload_button.on_click(reload_handler)
        self.reload_button.on_click(self.reload)

        # Set reload handler
        self.add2map.on_click(add2map_handler(self.map))

        # Set delete selected handler
        self.delete.on_click(self.delete_selected)

        # First Accordion
        self.root_acc = self.core(self.root_path)

        # Set VBox children
        self.children = [self.user_label, self.header, self.root_acc]

    def delete_selected(self, button=None):
        """ function to delete selected assets """
        selected = self.get_selected()

        # Output widget
        output = HTML('')

        def handle_yes(button):
            self.children = [self.header, output]
            # pool = pp.ProcessPool(self.POOL_SIZE)
            if selected:
                assets = [ass for ass in selected.keys()]
                for assetid in assets:
                    thread = Thread(target=batch.utils.recrusiveDeleteAsset,
                                    args=(assetid,))
                    thread.start()

            # when deleting end, reload
            self.reload()

        def handle_no(button):
            self.reload()
        def handle_cancel(button):
            self.reload()

        assets_str = ['{} ({})'.format(ass, ty) for ass, ty in selected.items()]
        assets_str = '</br>'.join(assets_str)
        confirm = ConfirmationWidget('<h2>Delete {} assets</h2>'.format(len(selected.keys())),
                                     'The following assets are going to be deleted: </br> {} </br> Are you sure?'.format(assets_str),
                                     handle_yes=handle_yes,
                                     handle_no=handle_no,
                                     handle_cancel=handle_cancel)

        self.children = [self.header, confirm, output]

    def reload(self, button=None):
        new_accordion = self.core(self.root_path)
        # Set VBox children
        self.children = [self.header, new_accordion]

    def get_selected(self):
        """ get the selected assets

        :return: a dictionary with the type as key and asset root as value
        :rtype: dict
        """
        def wrap(checkacc, assets={}, root=self.root_path):
            children = checkacc.children # list of CheckRow
            for child in children:
                checkbox = child.children[0] # checkbox of the CheckRow
                widget = child.children[1] # widget of the CheckRow (Accordion)
                state = checkbox.value

                if isinstance(widget.children[0], CheckAccordion):
                    title = widget.get_title(0).split(' ')[0]
                    new_root = '{}/{}'.format(root, title)
                    newselection = wrap(widget.children[0], assets, new_root)
                    assets = newselection
                else:
                    if state:
                        title = child.children[1].get_title(0)
                        # remove type that is between ()
                        ass = title.split(' ')[0]
                        ty = title.split(' ')[1][1:-1]
                        # append root
                        ass = '{}/{}'.format(root, ass)
                        # append title to selected list
                        # assets.append(title)
                        assets[ass] = ty

            return assets

        # get selection on root
        begin = self.children[2]  # CheckAccordion of root
        return wrap(begin)

    def core(self, path):
        # Get Assets data

        root_list = ee.data.getList({'id': path})

        # empty lists to fill with ids, types, widgets and paths
        ids = []
        types = []
        widgets = []
        paths = []

        # iterate over the list of the root
        for content in root_list:
            # get data
            id = content['id']
            ty = content['type']
            # append data to lists
            paths.append(id)
            ids.append(id.replace(path+'/', ''))
            types.append(ty)
            wid = HTML('Loading..')
            widgets.append(wid)

        # super(AssetManager, self).__init__(widgets=widgets, **kwargs)
        # self.widgets = widgets
        asset_acc = CheckAccordion(widgets=widgets)

        # set titles
        for i, (title, ty) in enumerate(zip(ids, types)):
            final_title = '{title} ({type})'.format(title=title, type=ty)
            asset_acc.set_title(i, final_title)

        def handle_new_accordion(change):
            path = change['path']
            index = change['index']
            ty = change['type']
            if ty == 'Folder' or ty == 'ImageCollection':
                wid = self.core(path)
            else:
                if ty == 'Image':
                    obj = ee.Image(path)
                else:
                    obj = ee.FeatureCollection(path)

                try:
                    wid = dispatcher.dispatch(obj).widget
                except Exception as e:
                    message = str(e)
                    wid = HTML(message)

            asset_acc.set_widget(index, wid)

        def handle_checkbox(change):
            path = change['path']
            widget = change['widget'] # Accordion
            wid_children = widget.children[0]  # can be a HTML or CheckAccordion
            new = change['new']

            if isinstance(wid_children, CheckAccordion): # set all checkboxes to True
                for child in wid_children.children:
                    check = child.children[0]
                    check.value = new

        # set handlers
        for i, (path, ty) in enumerate(zip(paths, types)):
            asset_acc.set_accordion_handler(
                i, handle_new_accordion,
                extra_params={'path':path, 'index':i, 'type': ty}
            )
            asset_acc.set_checkbox_handler(
                i, handle_checkbox,
                extra_params={'path':path, 'index':i, 'type': ty}
            )

        return asset_acc
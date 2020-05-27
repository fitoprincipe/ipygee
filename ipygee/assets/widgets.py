# coding=utf-8
import ee
from .. import helpers
from . import base
from ipywidgets import *
from .. import widgets


class ImageWidget(VBox):
    HTML = """
    <b>ID:</b> {id}</br>
    <b>Time:</b> {time}</br>
    <b>Bands:</b> {bands}</br>
    <b>Size:</b> {size}</br>
    """
    def __init__(self, asset, **kwargs):
        super(ImageWidget, self).__init__(**kwargs)
        self.asset = asset

        size = helpers.formatSize(float(self.asset.sizeBytes))
        sizeN = size[0]
        sizeU = size[1]
        sizeName = '{} {}'.format(sizeN, sizeU)
        # Bands
        bands = [b['id'] for b in self.asset.bands]
        # Set Widget
        widget1 = HTML(self.HTML.format(
            id=self.asset.id,
            time=self.asset.updateTime,
            bands=bands, size=sizeName
        ))
        visbands = bands[:3] if len(bands)>=3 else bands[0]
        url = self.asset.eeObject.getThumbURL(
            dict(bands=visbands, min=0, max=255, dimensions="200x200"))
        widget2 = HTML("<img src={} style='border: 1px solid black;'></img>".format(url))

        # set children
        self.children = [widget1, widget2]


class Image(base.Image):
    """ Add widget to Image Asset """
    _widget = None

    @property
    def widget(self):
        if not self._widget:
            self._widget = ImageWidget(self)
        return self._widget


class TableWidget(VBox):
    HTML = """
    <b>ID:</b> {id}</br>
    <b>Time:</b> {time}</br>
    <b>Size:</b> {size}</br>
    """
    def __init__(self, asset, **kwargs):
        super(TableWidget, self).__init__(**kwargs)
        self.asset = asset

        widget1 = HTML(self.HTML.format(
            id=self.asset.id,
            time=self.asset.updateTime,
            size=asset.size
        ))
        # set children
        self.children = [widget1]


class Table(base.Table):
    _widget = None

    @property
    def widget(self):
        if not self._widget:
            self._widget = TableWidget(self)
        return self._widget


class ContainerWidget(widgets.CheckAccordion):
    TITLE = "{id} ({type})"
    LOADING = HTML('Loading...')
    def __init__(self, assets, **kwargs):
        """ Get the container's children and create an CheckAccordion
        with every child """
        super(ContainerWidget, self).__init__(**kwargs)
        self.assets = assets
        # self.all_selected = False

        # create
        self.widgets = [self.LOADING]*len(self.assets)

        for i, asset in enumerate(self.assets):
            # set title
            title = self.TITLE.format(id=asset.last_name, type=asset.type)
            self.set_title(i, title)
            # set handlers
            self.set_accordion_handler(i, self.accordion_handler(asset))
            self.set_checkbox_handler(i, self.checkbox_handler(asset))

    def is_open(self, index):
        """ Return True if the folder in index is open """
        wid = self.get_widget(index)
        return True if wid.selected_index is not None else False

    def all_selected(self):
        """ Determine if all checkboxes are selected """
        checked = len([1 for child in self.children if child.checkbox.value])
        return checked == len(self.children)

    def select_all(self):
        """ Select all assets """
        for i, _ in enumerate(self.children):
            self.set_check(i, True)

    def unselect_all(self):
        """ Unselect all assets """
        for i, _ in enumerate(self.children):
            self.set_check(i, False)

    def accordion_handler(self, asset):
        def wrap(change):
            acc = change['owner']
            acc.children = (asset.widget,)
        return wrap

    def checkbox_handler(self, asset):
        def wrap(change):
            value = change['new']
            accordion = change['widget']
            widget = accordion.children[0]

            if isinstance(widget, (ContainerWidget,)):
                if value:
                    widget.select_all()
                else:
                    widget.unselect_all()
        return wrap

    def get_selected(self):
        """ Get selected assets, not nested """
        checked_wid = self.checked_rows()
        selected = []

        for i, _ in enumerate(self.children):
            wid = self.assets[i]
            if i in checked_wid:
                selected.append(wid)

        return selected

    def get_all_selected(self, selected=None):
        """ Get selected assets, not nested """
        if selected is None:
            selected = []

        for i, checkrow in enumerate(self.children):
            wid = self.assets[i]
            check = checkrow.checkbox
            if check.value:
                selected.append(wid)

            if isinstance(wid._widget, ContainerWidget):
                wid.get_all_selected(selected)

        return selected

    def get_delete_selected(self, selected=None):
        """ Get selected assets for deletion """
        if selected is None:
            selected = []

        if not (self.all_selected() and self in selected):
            for i, checkrow in enumerate(self.children):
                # checkrow = self.widget.children[i]
                wid = self.assets[i]
                check = checkrow.checkbox
                if check.value:
                    selected.append(wid)

                if isinstance(wid._widget, ContainerWidget):
                    wid.get_delete_selected(selected)

        if self in selected and not self.widget.all_selected():
            selected.remove(self)

        return selected


class ContainerMixin:
    _widget = None

    @property
    def children(self):
        """ fetch children """
        if not self._children:
            children = list()
            assets = ee.data.listAssets(dict(parent=self.name))['assets']
            for asset in assets:
                name = asset['name']
                ty = asset['type']
                child = dispatch(name, ty)
                child.parent = self
                children.append(child)
            self._children = children
        return self._children

    @property
    def widget(self):
        if not self._widget:
            self._widget = ContainerWidget(self.children)
        return self._widget

    def get_selected(self):
        """ Get selected assets, not nested """
        if not self._widget:
            return []
        
        return self.widget.get_selected()
        # checked_wid = self.widget.checked_rows()
        # selected = []
        #
        # for i, wid in enumerate(self.children):
        #     if i in checked_wid:
        #         selected.append(wid)
        # 
        # return selected

    def get_all_selected(self, selected=None):
        """ Get selected assets, not nested """
        if not self._widget:
            return []

        return self.widget.get_all_selected(selected)
        # if selected is None:
        #     selected = []
        #
        # for i, wid in enumerate(self.children):
        #     checkrow = self.widget.children[i]
        #     check = checkrow.checkbox
        #     if check.value:
        #         selected.append(wid)
        #
        #     if isinstance(wid._widget, ContainerWidget):
        #         wid.get_all_selected(selected)
        #
        # return selected


    def get_delete_selected(self, selected=None):
        """ Get selected assets for deletion """
        if not self._widget:
            return []

        return self.widget.get_delete_selected(selected)
        # if selected is None:
        #     selected = []
        #
        # if not (self.widget.all_selected() and self in selected):
        #     for i, wid in enumerate(self.children):
        #         checkrow = self.widget.children[i]
        #         check = checkrow.checkbox
        #         if check.value:
        #             selected.append(wid)
        #
        #         if isinstance(wid._widget, ContainerWidget):
        #             wid.get_delete_selected(selected)
        #
        # if self in selected and not self.widget.all_selected():
        #     selected.remove(self)
        #
        # return selected


class Folder(ContainerMixin, base.Folder):
    pass


class ImageCollection(ContainerMixin, base.ImageCollection):
    pass

# class Folder(base.Folder):
#     _widget = None
#
#     @property
#     def children(self):
#         """ fetch children """
#         return children(self)
#
#     @property
#     def widget(self):
#         if not self._widget:
#             self._widget = ContainerWidget(self.children)
#         return self._widget
#
#     def get_selected(self):
#         """ Get selected assets, not nested """
#         checked_wid = self.widget.checked_rows()
#         selected = []
#
#         for i, wid in enumerate(self.children):
#             if i in checked_wid:
#                 selected.append(wid)
#
#         return selected
#
#
# class ImageCollection(base.ImageCollection):
#     _widget = None
#
#     @property
#     def children(self):
#         """ fetch children """
#         return children(self)
#
#     @property
#     def widget(self):
#         if not self._widget:
#             self._widget = ContainerWidget(self.children)
#         return self._widget


TYPES = {
    # 'ROOT': Root,
    'TABLE': Table,
    'FOLDER': Folder,
    'IMAGE': Image,
    'IMAGE_COLLECTION': ImageCollection,
}


def dispatch(asset, TYPE):
    return TYPES[TYPE](asset)
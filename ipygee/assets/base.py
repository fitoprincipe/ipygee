# coding=utf-8
""" Base objects for the Asset Manager """
import ee
from .mixin import HaveChildren, HaveObject
from . import helpers


class Asset:
    have_children = False

    def __init__(self, name, data=None, parent=None):
        """ Initiate an Asset using the name or id """
        self.name = ee.data.convert_asset_id_to_asset_name(name)
        self._data = data
        self.parent = parent

    @property
    def data(self):
        if not self._data:
            self.fetch()
        return self._data

    def clear(self):
        self._data = None

    def fetch(self):
        """ Fetch all data """
        self._data = ee.data.getAsset(self.name)

    @property
    def id(self):
        if not self._data:
            return helpers.convert_asset_name_to_asset_id(self.name)
        else:
            return self.data.get('id')

    @property
    def last_name(self):
        return helpers.get_last_name(self.id)

    @property
    def type(self):
        return self.data.get('type')

    def copy(self, destination, overwrite=False):
        """ Copies the asset from sourceId into destinationId """
        ee.data.copyAsset(self.id, destination, overwrite)

    def delete(self, recursive=False, verbose=False):
        # self delete
        if verbose:
            print('Deleting {}'.format(self.name))

        # DELETE
        ee.data.deleteAsset(self.id)


class Root(HaveChildren, Asset):
    def __init__(self, *args, **kwargs):
        self._children = None
        super(Root, self).__init__(*args, **kwargs)
        self.parent = None

    @property
    def sizeBytes(self):
        return self.data['quota']['sizeBytes']

    @property
    def maxSizeBytes(self):
        return self.data['quota']['maxSizeBytes']

    @property
    def assetCount(self):
        return self.data['quota']['assetCount']

    @property
    def maxAssetCount(self):
        return self.data['quota']['maxAssetCount']

    def createFolder(self, name):
        """ Create a folder inside the root """
        dst = '{}/{}'.format(self.id, name)
        ee.data.createAsset({'type': ee.data.ASSET_TYPE_FOLDER}, dst)

    def createImageCollection(self, name):
        """ Create an empty ImageCollection inside the root """
        dst = '{}/{}'.format(self.id, name)
        ee.data.createAsset({'type': ee.data.ASSET_TYPE_IMAGE_COLL}, dst)


class Folder(HaveChildren, Asset):
    def __init__(self, *args, **kwargs):
        self._children = None
        super(Folder, self).__init__(*args, **kwargs)

    def clear(self):
        super(Folder, self).clear()
        self._children = None

    def createFolder(self, name):
        """ Create a folder inside the root """
        dst = '{}/{}'.format(self.id, name)
        ee.data.createAsset({'type': ee.data.ASSET_TYPE_FOLDER}, dst)

    def createImageCollection(self, name):
        """ Create an empty ImageCollection inside the root """
        dst = '{}/{}'.format(self.id, name)
        ee.data.createAsset({'type': ee.data.ASSET_TYPE_IMAGE_COLL}, dst)


class Table(HaveObject, Asset):
    def __init__(self, *args, **kwargs):
        self._eeObjectInfo = None
        self._size = None
        super(Table, self).__init__(*args, **kwargs)

    def clear(self):
        super(Table, self).clear()
        self._eeObjectInfo = None
        self._size = None

    @property
    def updateTime(self):
        return self.data.get('updateTime')

    @property
    def sizeBytes(self):
        return self.data.get('sizeBytes')

    @property
    def eeObject(self):
        return ee.FeatureCollection(self.id)

    @property
    def size(self):
        if self._size is None:
            self._size = self.eeObject.size().getInfo()
        return self._size


class ImageCollection(HaveObject, HaveChildren, Asset):
    def __init__(self, *args, **kwargs):
        self._children = None
        self._eeObjectInfo = None
        self._size = None
        super(ImageCollection, self).__init__(*args, **kwargs)

    def clear(self):
        super(ImageCollection, self).clear()
        self._eeObjectInfo = None
        self._size = None
        self._children = None

    @property
    def updateTime(self):
        return self.data.get('updateTime')

    @property
    def eeObject(self):
        return ee.ImageCollection(self.id)

    @property
    def size(self):
        if self._size is None:
            self._size = self.eeObject.size().getInfo()
        return self._size


class Image(HaveObject, Asset):

    def __init__(self, *args, **kwargs):
        self._eeObjectInfo = None
        super(Image, self).__init__(*args, **kwargs)

    def clear(self):
        super(Image, self).clear()
        self._eeObjectInfo = None

    @property
    def updateTime(self):
        return self.data.get('updateTime')

    @property
    def sizeBytes(self):
        return self.data.get('sizeBytes')

    @property
    def properties(self):
        return self.data.get('properties')

    @property
    def startTime(self):
        return self.data.get('startTime')

    @property
    def geometry(self):
        return self.data.get('geometry')

    @property
    def bands(self):
        return self.data.get('bands')

    @property
    def eeObject(self):
        return ee.Image(self.id)


TYPES = {
    'ROOT': Root,
    'TABLE': Table,
    'FOLDER': Folder,
    'IMAGE': Image,
    'IMAGE_COLLECTION': ImageCollection,
}


def dispatch(asset, TYPE):
    return TYPES[TYPE](asset)
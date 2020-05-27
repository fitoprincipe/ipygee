from .base import *

TYPES = {
    'ROOT': Root,
    'TABLE': Table,
    'FOLDER': Folder,
    'IMAGE': Image,
    'IMAGE_COLLECTION': ImageCollection,
}

def dispatch(name, type):
    """ Dispatch using the name and type """
    if type not in TYPES:
        raise ValueError('Type {} not recognized'.format(type))
    return TYPES[type](name)


def from_data(data, root=False):
    """ Dispatcher from data """
    ty = 'ROOT' if root else data.get('type')
    if ty not in TYPES:
        raise ValueError('Type {} not recognized'.format(ty))
    return TYPES.get(ty)(data=data)


def from_name(name, root=False):
    """ Dispatcher from name """
    name = ee.data.convert_asset_id_to_asset_name(name)
    data = ee.data.getAsset(name)
    return from_data(data, root)
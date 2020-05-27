# coding=utf-8
""" Helpers only for assets """


def convert_asset_name_to_asset_id(name):
    return name.split('assets/')[1]


def get_last_name(id):
    """ The last name of the asset is the latter part: users/.../last_name """
    return id.split('/')[-1]
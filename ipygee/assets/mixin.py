# coding=utf-8
import ee


class HaveChildren(object):
    """ A Mixin class """
    have_children = True

    @property
    def children(self):
        """ fetch children """
        from .dispatcher import dispatch
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

    def delete(self, recursive=False, verbose=False):
        # delete children
        if recursive:
            for child in self.children:
                child.delete(recursive, verbose)

        # self delete
        if verbose:
            print('Deleting {}'.format(self.name))

        # DELETE
        ee.data.deleteAsset(self.id)

        # clear children
        self._children = None


class HaveObject(object):
    @property
    def eeObjectInfo(self):
        if not self._eeObjectInfo:
            self._eeObjectInfo = self.eeObject.getInfo()
        return self._eeObjectInfo
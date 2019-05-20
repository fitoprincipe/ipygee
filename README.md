# IpyGEE

A set of tools and Widgets for working with **Google Earth Engine** in Jupyter notebooks and Jupyter Lab

## Install

`pip install ipygee`

*Note: Installation **does not** install Earth Engine Python API. You have to install it before installing `ipygee`, see: https://developers.google.com/earth-engine/python_install*

## Main Widgets

### - Map

``` python
from ipygee import *
Map = Map()
Map.show()
```

### - AssetManager
``` python
from ipygee import *
AM = AssetManager()
AM
```

### - TaskManager
``` python
from ipygee import *
TM = TaskManager()
TM
```

See examples in [here](https://github.com/fitoprincipe/ipygee/tree/master/examples)
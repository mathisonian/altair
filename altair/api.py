"""
Main API for Vega-lite spec generation.

DSL mapping Vega types to IPython traitlets
"""

try:
    import traitlets as T
    from traitlets.config import Configurable, Config
except ImportError:
    from IPython.utils import traitlets as T

from .utils import parse_shorthand, infer_vegalite_type, DataFrameTrait
from ._py3k_compat import string_types
from .renderer import Renderer

import pandas as pd




class BaseObject(Configurable):

    skip = []

    def __contains__(self, key):
        value = getattr(self, key)
        if isinstance(value, pd.DataFrame):
            return True
        return ((value is not None)
                and (not (not isinstance(value, bool) and not value)))

    def to_dict(self):
        result = {}
        for k in self.traits():
            if k in self and k not in self.skip:
                v = getattr(self, k)
                if isinstance(v, BaseObject):
                    result[k] = v.to_dict()
                else:
                    result[k] = v
        return result

    def __repr__(self):
        return repr(self.to_dict())


class Data(BaseObject):

    formatType = T.Enum(['json', 'csv'], default_value='json')
    url = T.Unicode(default_value=None, allow_none=True)
    values = T.List(default_value=None, allow_none=True)

    def to_dict(self):
        result = {'formatType': self.formatType,
                  'values': self.data.to_dict('records')}
        return result


class Scale(BaseObject):
    pass


class Axis(BaseObject):
    pass


class Band(BaseObject):
    size = T.Int(600)


class Legend(BaseObject):
    pass


class Bin(BaseObject):
    maxbins = T.Int(0, config=True)


class SortItems(BaseObject):
    name = T.Unicode(default_value=None, allow_none=True)
    aggregate = T.Enum(['avg', 'sum', 'min', 'max', 'count'],
                       default_value=True)
    reverse = T.Bool(False)


class Shelf(BaseObject):

    skip = ['shorthand', 'config']

    def __init__(self, shorthand, **kwargs):
        kwargs['shorthand'] = shorthand
        super(Shelf, self).__init__(**kwargs)

    def _infer_type(self, data):
        if self.type is None and self.name in data:
            self.type = infer_vegalite_type(data[self.name])

    def _shorthand_changed(self, name, old, new):
        D = parse_shorthand(self.shorthand)
        for key, val in D.items():
            setattr(self, key, val)

    shorthand = T.Unicode('')
    name = T.Unicode('', config=True)
    type = T.Enum(['N', 'O', 'Q', 'T'], default_value=None, allow_none=True,
                  config=True)
    timeUnit = T.Enum(['year', 'month', 'day', 'date',
                       'hours', 'minutes', 'seconds'],
                      default_value=None, allow_none=True)
    bin = T.Union([T.Bool(), T.Instance(Bin)], default_value=False)
    sort = T.List(T.Instance(SortItems), default_value=None, allow_none=True)
    aggregate = T.Enum(['avg', 'sum', 'median', 'min', 'max', 'count'],
                       default_value=None, allow_none=True, config=True)


class DataCoordinate(Shelf):
    scale = T.Instance(Scale, default_value=None, allow_none=True)
    axis = T.Instance(Axis, default_value=None, allow_none=True)
    band = T.Instance(Band, default_value=None, allow_none=True)


class X(DataCoordinate):
    pass


class Y(DataCoordinate):
    pass


class FacetCoordinate(Shelf):
    aggregate = T.Enum(['count'], default_value=None, allow_none=True)
    padding = T.CFloat(0.1)
    axis = T.Instance(Axis, default_value=None, allow_none=True)
    height = T.CInt(150)


class Row(FacetCoordinate):
    pass


class Col(FacetCoordinate):
    pass


class Size(Shelf):
    scale = T.Instance(Scale, default_value=None, allow_none=True)
    legend = T.Instance(Legend, default_value=None, allow_none=True)
    value = T.CInt(30)


class Color(Shelf):
    value = T.Unicode('#4682b4')
    scale = T.Instance(Scale, default_value=None, allow_none=True)
    legend = T.Instance(Legend, default_value=None, allow_none=True)
    opacity = T.Float(1.0)


class Shape(Shelf):
    value = T.Enum(['circle', 'square', 'cross', 'diamond', 'triangle-up',
                    'triangle-down'], default_value='circle')
    aggregate = T.Enum(['count'], default_value=None, allow_none=True)
    legend = T.Instance(Legend, default_value=None, allow_none=True)
    filled = T.Bool(False)


class Encoding(BaseObject):
    x = T.Union([T.Instance(X), T.Unicode()],
                default_value=None, allow_none=True)
    y = T.Union([T.Instance(Y), T.Unicode()],
                default_value=None, allow_none=True)
    row = T.Union([T.Instance(Row), T.Unicode()],
                  default_value=None, allow_none=True)
    col = T.Union([T.Instance(Col), T.Unicode()],
                  default_value=None, allow_none=True)
    size = T.Union([T.Instance(Size), T.Unicode()],
                   default_value=None, allow_none=True)
    color = T.Union([T.Instance(Color), T.Unicode()],
                    default_value=None, allow_none=True)
    shape = T.Union([T.Instance(Shape), T.Unicode()],
                    default_value=None, allow_none=True)

    parent = T.Instance(BaseObject, default_value=None, allow_none=True)

    skip = ['parent', 'config']

    def _infer_types(self, data):
        for attr in ['x', 'y', 'row', 'col', 'size', 'color', 'shape']:
            val = getattr(self, attr)
            if val is not None:
                val._infer_type(data)

    def _x_changed(self, name, old, new):
        if isinstance(new, string_types):
            self.x = X(new, config=self.config)
        if getattr(self.parent, 'data', None) is not None:
            self.x._infer_type(self.parent.data)

    def _y_changed(self, name, old, new):
        if isinstance(new, string_types):
            self.y = Y(new, config=self.config)
        if getattr(self.parent, 'data', None) is not None:
            self.y._infer_type(self.parent.data)

    def _row_changed(self, name, old, new):
        if isinstance(new, string_types):
            self.row = Row(new)
        if getattr(self.parent, 'data', None) is not None:
            self.row._infer_type(self.parent.data)

    def _col_changed(self, name, old, new):
        if isinstance(new, string_types):
            self.col = Col(new)
        if getattr(self.parent, 'data', None) is not None:
            self.col._infer_type(self.parent.data)

    def _size_changed(self, name, old, new):
        if isinstance(new, string_types):
            self.size = Size(new)
        if getattr(self.parent, 'data', None) is not None:
            self.size._infer_type(self.parent.data)

    def _color_changed(self, name, old, new):
        if isinstance(new, string_types):
            self.color = Color(new)
        if getattr(self.parent, 'data', None) is not None:
            self.color._infer_type(self.parent.data)

    def _shape_changed(self, name, old, new):
        if isinstance(new, string_types):
            self.shape = Shape(new)
        if self.parent is not None:
            self.shape._infer_type(self.parent.data)


class VLConfig(BaseObject):

    width = T.Int(600)
    height = T.Int(400)
    singleWidth = T.Int(default_value=None, allow_none=True)
    singleHeight = T.Int(default_value=None, allow_none=True)
    gridColor = T.Unicode('black')
    gridOpacity = T.Float(0.08)


class Viz(BaseObject):

    marktype = T.Enum(['point', 'tick', 'bar', 'line',
                      'area', 'circle', 'square', 'text'],
                      default_value='point')
    encoding = T.Instance(Encoding, default_value=None, allow_none=True)
    vlconfig = T.Instance(VLConfig, allow_none=True)

    def _vlconfig_default(self):
        return VLConfig()

    _data = T.Instance(Data, default_value=None, allow_none=True)
    data = DataFrameTrait(default_value=None, allow_none=True)

    def _encoding_changed(self, name, old, new):
        if isinstance(new, Encoding):
            self.encoding.parent = self
            if 'data' in self:
                self.encoding._infer_types(self.data)

    def _data_changed(self, name, old, new):
        if not isinstance(new, pd.DataFrame):
            self.data = pd.DataFrame(new)
            return
        self._data = Data(data=new)
        if self.encoding is not None:
            self.encoding._infer_types(self.data)

    skip = ['data', '_data', 'vlconfig']

    def __init__(self, data, **kwargs):
        kwargs['data'] = data
        super(Viz, self).__init__(**kwargs)

    def to_dict(self):
        D = super(Viz, self).to_dict()
        D['data'] = self._data.to_dict()
        D['config'] = self.vlconfig.to_dict()
        return D

    def encode(self, **kwargs):
        self.encoding = Encoding(**kwargs)
        return self

    def configure(self, **kwargs):
        """Set chart configuration"""
        self.vlconfig = VLConfig(**kwargs)
        return self

    def set_single_dims(self, width, height):
        """
        Helper function for setting single-widths

        Parameters
        ----------
        width: int
        height: int
        """
        self.vlconfig.width = width
        self.vlconfig.height = height
        self.vlconfig.singleWidth = int(width * 0.75)
        self.vlconfig.singleHeight = int(height * 0.75)

        if self.encoding.x.type in ('N', 'O'):
            self.encoding.x.band = Band(size=int(width/10))

        if self.encoding.y.type in ('N', 'O'):
            self.encoding.y.band = Band(size=int(height/10))
        return self

    def mark(self, mt):
        """
        Set mark to given string value.

        Parameters
        ----------
        mt: str
        """
        self.marktype = mt
        return self

    def point(self):
        return self.mark('point')

    def tick(self):
        return self.mark('tick')

    def bar(self):
        return self.mark('bar')

    def line(self):
        return self.mark('line')

    def area(self):
        return self.mark('area')

    def circle(self):
        return self.mark('circle')

    def square(self):
        return self.mark('square')

    def text(self):
        return self.mark('text')

    def hist(self, bins=10, **kwargs):
        """
        Render histogram with given `bins`.

        Parameters
        ----------
        bins: int, default 10
        """

        self.marktype = "bar"

        config = Config()

        config.Y.type = "Q"
        config.Y.aggregate = "count"

        # We're making sure a y-change is triggered
        self.encoding = Encoding(config=config, y='', **kwargs)

        if isinstance(kwargs.get("x"), str):
            self.encoding.x.bin = Bin(maxbins=bins)

        # Hack: y.name should be "*", but version weirdness
        self.encoding.y.name = self.encoding.x.name

        return self
        
    def render(self, **kwargs):
        global _renderer
        return _renderer.render(self, **kwargs)


# Renderer logic

def _get_matplotlib_renderer():
    from .mpl import MatplotlibRenderer
    return MatplotlibRenderer()

def _get_lightning_renderer():
    from .lgn import LightningRenderer
    return LightningRenderer()

_renderers = {
    'matplotlib': _get_matplotlib_renderer,
    'lightning': _get_lightning_renderer
}


_renderer = None

def register_renderer(name, rfactory):
    """Register a renderer factory that creates renderer instances."""
    global _renderers
    _renderers[name] = rfactory

def use_renderer(r):
    """Use a particular renderer, registered by name or an actual Renderer instance."""
    global _renderer
    global _renderers
    if isinstance(r, Renderer):
        _renderer = r
    else:
        if r in _renderers:
            _renderer = _renderers[r]()
        else:
            raise ValueError('renderer could not be found: {0}').format(r)

def list_renderers():
    global _renderers
    return list(_renderers.keys())

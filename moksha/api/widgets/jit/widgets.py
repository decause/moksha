# Authors: Ralph Bean <ralph.bean@gmail.com

from moksha.api.widgets import LiveWidget
from tw2.jit import AreaChart

class LiveAreaChartWidget(AreaChart, LiveWidget):
    """ A live graphing widget using tw2.jit """
    onmessage = 'window._jitwidgets["${id}"].loadJSON(json[0])'

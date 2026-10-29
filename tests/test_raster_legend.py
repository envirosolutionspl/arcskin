"""Pro's "High : max" / "Low : min" labels on raster ramp legends."""

import struct
import tempfile
import unittest
from pathlib import Path

from osgeo import gdal
from qgis.core import (
    QgsColorRampLegendNode, QgsColorRampShader, QgsLayerTreeModel,
    QgsProject, QgsRasterLayer, QgsRasterShader,
    QgsSingleBandPseudoColorRenderer, QgsStyle,
)

from arcskin.contents_views import ramp_limits

LOW, HIGH = 5, 104  # values of the test raster


def raster(directory):
    """Single band raster with the values LOW..HIGH."""
    path = str(Path(directory) / "ramp.tif")
    data = gdal.GetDriverByName("GTiff").Create(path, 10, 10, 1,
                                                gdal.GDT_Float32)
    data.SetGeoTransform((0, 1, 0, 10, 0, -1))
    data.GetRasterBand(1).WriteRaster(
        0, 0, 10, 10, struct.pack("100f", *range(LOW, HIGH + 1)))
    data = None  # written to disk
    layer = QgsRasterLayer(path, "ramp")
    assert layer.isValid()
    return layer


def pseudocolor(layer):
    function = QgsColorRampShader(
        LOW, HIGH, QgsStyle.defaultStyle().colorRamp("Viridis"))
    function.classifyColorRamp(5, 1)
    shader = QgsRasterShader()
    shader.setRasterShaderFunction(function)
    layer.setRenderer(QgsSingleBandPseudoColorRenderer(
        layer.dataProvider(), 1, shader))


class RampLimits(unittest.TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.layer = raster(self.directory.name)

    def tearDown(self):
        QgsProject.instance().removeAllMapLayers()
        self.directory.cleanup()

    def ramp_nodes(self):
        project = QgsProject.instance()
        project.addMapLayer(self.layer)
        self.model = QgsLayerTreeModel(project.layerTreeRoot())
        node = project.layerTreeRoot().findLayer(self.layer.id())
        return [n for n in self.model.layerLegendNodes(node)
                if isinstance(n, QgsColorRampLegendNode)]

    def test_grey_stretch(self):
        ramps = self.ramp_nodes()
        self.assertEqual(len(ramps), 1)
        self.assertEqual(ramp_limits(ramps[0]), (LOW, HIGH))

    def test_pseudocolor(self):
        pseudocolor(self.layer)
        ramps = self.ramp_nodes()
        self.assertEqual(len(ramps), 1)
        self.assertEqual(ramp_limits(ramps[0]), (LOW, HIGH))

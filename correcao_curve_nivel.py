# -*- coding: utf-8 -*-

"""
/***************************************************************************
 CorrecaoCurvaNivel
                                 A QGIS plugin
 Este plugin identifica e corrige linhas de curva de nível que intersectam vetores de massa d'água.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2023-11-21
        copyright            : (C) 2023 by Cap Tadeu; 1° Ten Kreitlon; 1° Ten Vinicius; Cap Raphael Luiz
        email                : e.tadeu.eb@ime.eb.br; joao.pereira@ime.eb.br; viniciusmagalhaes@ime.eb.br; raphaelluiz.franca@ime.eb.br
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""

__author__ = 'Cap Tadeu; 1° Ten Kreitlon; 1° Ten Vinicius; Cap Raphael Luiz'
__date__ = '2023-11-21'
__copyright__ = '(C) 2023 by Cap Tadeu; 1° Ten Kreitlon; 1° Ten Vinicius; Cap Raphael Luiz'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
import sys
import inspect

from qgis.core import QgsProcessingAlgorithm, QgsApplication
from .correcao_curve_nivel_provider import CorrecaoCurvaNivelProvider

cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]

if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)


class CorrecaoCurvaNivelPlugin(object):

    def __init__(self):
        self.provider = None

    def initProcessing(self):
        """Init Processing provider for QGIS >= 3.8."""
        self.provider = CorrecaoCurvaNivelProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)

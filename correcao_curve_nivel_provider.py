# -*- coding: utf-8 -*-

"""
/***************************************************************************
 CorrecaoCurvaNivel
                                 A QGIS plugin
 Este plugin identifica e corrige linhas de curva de nível que intersectam vetores de massa d'água.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2023-11-21
        copyright            : (C) 2023 by Cap Tadeu; 1° Ten Kreitlon; 1° Ten Vinicius
        email                : e.tadeu.eb@ime.eb.br; joao.pereira@ime.eb.br; viniciusmagalhaes@ime.eb.br
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'Cap Tadeu; 1° Ten Kreitlon; 1° Ten Vinicius'
__date__ = '2023-11-21'
__copyright__ = '(C) 2023 by Cap Tadeu; 1° Ten Kreitlon; 1° Ten Vinicius'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
from .correcao_curve_nivel_algorithm import CorrecaoCurvaNivelAlgorithm


class CorrecaoCurvaNivelProvider(QgsProcessingProvider):

    def __init__(self):
        """
        Default constructor.
        """
        QgsProcessingProvider.__init__(self)

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    def loadAlgorithms(self):
        """
        Loads all algorithms belonging to this provider.
        """
        self.addAlgorithm(CorrecaoCurvaNivelAlgorithm())

    def id(self):
        """
        Returns the unique provider id, used for identifying the provider. This
        string should be a unique, short, character only string, eg "qgis" or
        "gdal". This string should not be localised.
        """
        return "Adequar curvas de nível com massa d'água"

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.

        This string should be short (e.g. "Lastools") and localised.
        """
        return self.tr("PROJETO DE FIM DE CURSO")

    def icon(self):
        """
        Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        return QIcon(os.path.join(os.path.dirname(__file__), 'pfc.png'))

    def longName(self):
        """
        Returns the a longer version of the provider name, which can include
        extra details such as version numbers. E.g. "Lastools LIDAR tools
        (version 2.2.1)". This string should be localised. The default
        implementation returns the same string as name().
        """
        return self.name()

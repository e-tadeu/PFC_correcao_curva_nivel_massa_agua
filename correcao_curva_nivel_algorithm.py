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
from code import interact
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterFeatureSink)
import processing


class CorrecaoCurvaNivelAlgorithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    OUTPUT = 'OUTPUT'
    INPUT_RASTER = 'INPUT_RASTER'
    INPUT_VECTOR = 'INPUT_VECTOR'
    INPUT_AGUA = 'INPUT_AGUA'

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT_RASTER,
                self.tr("Insira o Modelo Digital de Elevação"),
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_VECTOR, 
                self.tr("Insira as curvas de nível"),
                [QgsProcessing.TypeVectorLine]
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_AGUA,
                self.tr("Insira a camada de massa d'água"),
                types=[QgsProcessing.TypeVectorPolygon]
            )
        )

        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Output layer')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        curvas = self.parameterAsVectorLayer(parameters, self.INPUT_VECTOR, context)
        massas = self.parameterAsVectorLayer(parameters, self.INPUT_AGUA, context)
        (sink, dest_id) = self.parameterAsSink(parameters, 
                                               self.OUTPUT,
                                                context,
                                                curvas.fields(),
                                                curvas.wkbType(),
                                                curvas.sourceCrs())

        feedback.setProgressText('\nProcurando e corrigindo geometrias inválidas nas camadas de vetores...')

        #Correção de geometrias inválidas nas camadas de vetores
        curves = processing.run("native:fixgeometries",
                                {'INPUT':curvas,
                                 'METHOD':0,
                                 'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
        
        water = processing.run("native:fixgeometries", 
                               {'INPUT':massas,
                                'METHOD':1,
                                'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
        
        feedback.setProgressText("\nExecutando a intersecção das linhas de curvas de nível com as massas d'água...")

        #Obtenção da intersecção das curvas de nível com as massas d'água
        intersection = processing.run("native:intersection",
                                      {'INPUT':curves,
                                       'OVERLAY':water,
                                       'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
        
        # Compute the number of steps to display within the progress bar and
        # get features from source
        total = 100.0 / intersection.featureCount() if intersection.featureCount() else 0
        features = intersection.getFeatures()

        feedback.setProgressText("\nInserindo as feições de intersecção na camada de saída...")
        for current, feature in enumerate(features):
            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                return {self.OUTPUT: "Cancelado pelo usuário"}

            # Add a feature in the sink
            sink.addFeature(feature, QgsFeatureSink.FastInsert)

            # Update the progress bar
            feedback.setProgress(int(current * total))

        feedback.setProgressText("\nConfigurando o estilo camada de saída...")
        # Configurando o estilo da camada
        style_file = os.path.join(os.path.dirname(__file__), 'interseccoes.qml')
        processing.run('native:setlayerstyle', 
                       {'INPUT': dest_id,
                        'STYLE': style_file}, 
                       context=context, 
                       feedback=feedback, 
                       is_child_algorithm=True)
        
        return {self.OUTPUT: dest_id}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "Corretor de curvas de nível com massa d'água"

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr("Corretor de curvas de nível com massa d'água")

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return CorrecaoCurvaNivelAlgorithm()
    
    def shortHelpString(self):
        return self.tr("Este processing identifica e corrige curvas de nível que interceptam vetores de massa d'água deixando-os conforme a Norma da Especificação Técnica para Aquisição de Dados Geoespaciais Vetoriais (ET-ADVG) versão 3.0 (EB80-N-72.005) e faz parte do Projeto de Fim de Curso da Graduação em Eng Cartográfica do IME 2024.")

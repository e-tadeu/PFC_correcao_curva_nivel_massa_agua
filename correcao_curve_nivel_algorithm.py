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
from qgis.PyQt.QtGui import QIcon
from qgis.core import (QgsProcessing,
                       QgsFeature,
                       QgsFeatureSink,
                       QgsField,
                       QgsFields,
                       QgsGeometry,
                       QgsPointXY,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterField,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterNumber,
                       QgsProcessingException,
                       QgsProject,
                       QgsVectorLayer,
                       QgsWkbTypes,
                       QgsProcessingMultiStepFeedback,
                       QgsProcessingFeatureSourceDefinition,
                       QgsProcessingFeedback,
                       QgsFeatureRequest,
                       QgsSpatialIndex)
from qgis.gui import QgsCollapsibleGroupBox
import processing
from .pontas_soltas import pontas_soltas
from math import cos, radians

class CorrecaoCurvaNivelAlgorithm(QgsProcessingAlgorithm):
 
    INPUT_VECTOR = 'INPUT_VECTOR'
    INPUT_FIELD =  'INPUT_FIELD'
    INPUT_AGUA = 'INPUT_AGUA'
    INPUT_SCALE = 'INPUT_SCALE'
    CUSTOM_SCALE = 'CUSTOM_SCALE'
    BUFFER_SIZE = 'BUFFER_SIZE'
    OUTPUT = 'OUTPUT'
    SELECTED_CURVES = 'SELECTED_CURVES'
    SELECTED_WATER = 'SELECTED_WATER'
    MOLDURA = 'MOLDURA'
    REMOVE_FEATURES = 'REMOVE_FEATURES'
    PERCENTAGE = 'PERCENTAGE'

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_VECTOR, 
                self.tr("Insira as curvas de nível"),
                [QgsProcessing.TypeVectorLine]
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SELECTED_CURVES, self.tr("Process only selected features of contour lines")
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                'INPUT_FIELD',
                self.tr('Selecione o atributo de cota'), 
                type=QgsProcessingParameterField.Numeric, 
                parentLayerParameterName='INPUT_VECTOR',
                defaultValue = 'cota')
            )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_AGUA,
                self.tr("Insira a camada de massa d'água"),
                types=[QgsProcessing.TypeVectorPolygon]
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SELECTED_WATER, self.tr("Process only selected features of water")
            )
        )

        # Parâmetro de seleção para a escala
        self.addParameter(
            QgsProcessingParameterEnum(
                self.INPUT_SCALE,
                self.tr("Selecione a escala"),
                options=['1/25.000', '1/50.000', '1/100.000', '1/250.000', 'Personalizada'],
                defaultValue=0,
                optional=True  # Opção de entrada opcional
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.CUSTOM_SCALE,
                self.tr("Insira a escala personalizada (apenas se 'Personalizada' for selecionada)"),
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BUFFER_SIZE,
                self.tr("Tamanho do buffer em torno das massas d'água"),
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.REMOVE_FEATURES,
                self.tr(f"Deseja eliminar feições com mais de um dado percentual abaixo dentro de massa d'água?"),
                defaultValue=True
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.PERCENTAGE,
                self.tr(f"Insira a porcentagem (0% - 100%)"),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=50,
                minValue=0,
                maxValue=100,
            )
        )

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.MOLDURA,
                self.tr("Insira a camada de moldura"),
                types=[QgsProcessing.TypeVectorPolygon]
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Curvas de Nível Ajustadas')
            )
        )
    
    def processAlgorithm(self, parameters, context, feedback):
        """
        Executa o processamento principal do algoritmo.
        """
        curvas = self.parameterAsVectorLayer(parameters, self.INPUT_VECTOR, context)
        cota_field = self.parameterAsFields(parameters,'INPUT_FIELD', context )
        massas = self.parameterAsVectorLayer(parameters, self.INPUT_AGUA, context)
        scale_option = self.parameterAsEnum(parameters, self.INPUT_SCALE, context)
        custom_scale = self.parameterAsDouble(parameters, self.CUSTOM_SCALE, context)
        buffer_size = self.parameterAsDouble(parameters, self.BUFFER_SIZE, context)
        onlySelectedCN = self.parameterAsBool(parameters, self.SELECTED_CURVES, context)
        onlySelectedWater = self.parameterAsBool(parameters, self.SELECTED_WATER, context)
        moldura = self.parameterAsVectorLayer(parameters, self.MOLDURA, context)
        remove_features = self.parameterAsBool(parameters, self.REMOVE_FEATURES, context)
        percentage = self.parameterAsInt(parameters, self.PERCENTAGE, context)

        # Criação de uma camada de CN somente com as feições selecionadas de CN
        if onlySelectedCN == False: inputLayerCN = curvas
        else: 
            inputLayerCN = self.layer_features_selected(curvas)
        
        # Criação de uma camada de água somente com as feições selecionadas de água
        if onlySelectedWater == False: inputLayerWater = massas
        else: 
            inputLayerWater = self.layer_features_selected(massas)
       
        # A variável scale refere-se ao denominador de escala
        if scale_option == 4:  # Personalizada
            if custom_scale <= 0:
                raise QgsProcessingException(self.tr("A escala personalizada deve ser um valor positivo."))
            scale = custom_scale
        else:
            scales = [25000, 50000, 100000, 250000]
            scale = scales[scale_option]

        (sink, dest_id) = self.parameterAsSink(parameters, 
                                               self.OUTPUT,
                                                context,
                                                curvas.fields(),
                                                QgsWkbTypes.LineString,
                                                curvas.sourceCrs())

        feedback.setProgressText('Procurando e corrigindo geometrias inválidas nas camadas de vetores...')
        # Correção de geometrias inválidas nas camadas de vetores
        curves = self.fix_geometry(inputLayerCN)
        water = self.fix_geometry(inputLayerWater)
        
        total = 100.0 / water.featureCount() if water.featureCount() else 0

        moldura_line = processing.run("native:polygonstolines",
                                {'INPUT': moldura,
                                'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']

        # 1) Obtenção da intersecção das curvas de nível com as massas d'água
        feedback.setProgressText('\nProcurando e identificando as intersecções entre as camadas de vetores...')
        intersection = self.interseccao(parameters, context, curves, water)

        # 2) Eliminação de feições dentro de massas d'água
        feedback.setProgressText('\nDeletando curvas de nível dentro de massas d\'água...')
        curves = self.case_cn_within_water(curves, water, remove_features, percentage)

        cn_adequadas = curves

        for current, massa_feat in enumerate(water.getFeatures()):
            
            if feedback.isCanceled():
                break

            massa_geom = massa_feat.geometry()
            cotas_list = list()

            for line in intersection.getFeatures():
                geom_inter = line.geometry()

                if geom_inter.intersects(massa_geom):
                    cota = line[cota_field[0]] #Aqui ele pega a string 'cota'
                    cotas_list.append(cota)
                    feedback.pushInfo(f'A feição {line} possui a cota {cota} e está dentro da massa {massa_feat}.')
            
            cotas_list = sorted(set(cotas_list)) #Elementos únicos (sem cotas duplicadas) e crescentemente ordenadas
            
            if len(cotas_list) > 0:
                
                # 3) Inserção de n camada de buffer em torno da massa d'água
                feedback.setProgressText(f'\nAplicando {len(cotas_list)} buffers ao redor da massa d\'água {massa_feat.id()}...')
                buffers_list = self.list_buffers(parameters, context, buffer_size, curvas, massas, massa_feat, massa_geom, cotas_list, scale)                      
                
                # 4) Criação de uma camada de linhas no contorno do buffer
                feedback.setProgressText(f'\nExtraindo o contorno dos buffers da massa d\'água {massa_feat.id()}...')
                boundaries_list = self.contour_buffer(parameters, context, buffers_list, moldura)
                feedback.pushInfo(f'A massa {massa_feat} possui {len(boundaries_list)} contorno(s) de buffer com as seguintes camadas {boundaries_list}.')
                
                # 5) Secção da linha de contorno
                feedback.setProgressText(f'\nSeccionando o contorno dos buffers da massa d\'água {massa_feat.id()} com curvas de nível...')
                split_boundaries_list = self.split_contour(parameters, context, feedback, boundaries_list, curves, moldura_line, cotas_list, cota_field[0])
                feedback.pushInfo(f'A massa {massa_feat} possui {len(split_boundaries_list)} contorno(s) de buffer seccionados pelas CN com as seguintes camadas {split_boundaries_list}.')
                #O ordenamento na lista, segue a lógica de ligar o primeiro elemento com a menor cota
                
                #feedback.pushInfo(f'\nO alcance da lista de buffer é {len(buffers_list)} de cota é {len(cotas_list)} e da split_boundaries {len(split_boundaries_list)}.')
                for b in range (0,len(buffers_list)):
                    elevacao = cotas_list[b] 
                    # 6) Criação das CN cortada pelo buffer
                    feedback.setProgressText(f'\nCortando as curvas de nível que intersectam o buffer da massa d\'água {massa_feat.id()}...')
                    buffer = buffers_list[b]

                    #feedback.pushInfo(f'\n\nA camada de CN a ser cortadas pelo buffer é {cn_adequadas}.')
                    cn_cortadas = self.cut_cn(parameters, context, feedback, cn_adequadas, buffer, cota_field[0], elevacao)
                    feedback.pushInfo(f'O recorte das CN {cn_adequadas} pelo buffer {buffers_list[b]} de cota {cotas_list[b]}.')

                    #cn_cortadas = self.fix_geometry(cn_cortadas)
                    
                    #feedback.pushInfo(f'\n\nA camada de CN cortadas é {cn_cortadas}.')

                    # 7) Substituição de trechos das curvas de nível
                    feedback.setProgressText(f"\nIniciando a conexão das curvas de nível que foram cortadas...")
                    trechos_substitutos = split_boundaries_list[b]
                    cn_adequadas = self.substituicao_trecho(parameters, context, feedback, trechos_substitutos, cn_cortadas, cota_field[0], elevacao)

                    #cn_adequadas = self.fix_geometry(cn_adequadas)
                    #feedback.pushInfo(f'\n\nA camada de CN adequadas é {cn_adequadas}.')

            feedback.setProgress(int(current * total))
        
        points_soltas = pontas_soltas(self, parameters, context, feedback, cn_adequadas, moldura)
        # Adicionar a nova camada ao projeto
        QgsProject.instance().addMapLayer(points_soltas)

        # Adição das feições na camada output
        for feat in cn_adequadas.getFeatures():
            sink.addFeature(feat, QgsFeatureSink.FastInsert)
        
        return {self.OUTPUT: dest_id}

    def interseccao(self, parameter, context, cn_layer, water_layer):

        intersection = processing.run("native:intersection",
                                      {'INPUT':cn_layer,
                                       'OVERLAY':water_layer,
                                       'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']

        intersection = processing.run("native:multiparttosingleparts", 
                                      {'INPUT': intersection,
                                       'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
        
        intersection.setName("Intersecções")
        
        QgsProject.instance().addMapLayer(intersection)

        return intersection

    def list_buffers(self, parameters, context, buffer_tamanho, cn_layer, water_layer, water_feat, water_geom, cotas_lista, escala):
        
        buffers = list()
        if buffer_tamanho:
                                
            #Caso seja um buffer personalizado, ele verifica se o sistema é geográfico e converte no equivalente a graus
            if cn_layer.crs().isGeographic():
                extent = cn_layer.extent()
                centroid_lat = (extent.yMinimum() + extent.yMaximum()) / 2 #Pega a latitude do centroide do projeto
                buffer_size_graus = buffer_tamanho / (111320 * cos(radians(centroid_lat)))
                
                for i in range (0, len(cotas_lista)):
                    buffer = water_geom.buffer(buffer_size_graus*(i+1), 5)
                    crs = water_layer.sourceCrs()
                    buffer_vector = QgsVectorLayer(f"{QgsWkbTypes.displayString(water_layer.wkbType())}?crs={crs.authid()}", "buffer", "memory")
                    buffer_vector.dataProvider().addAttributes(water_layer.fields())
                    buffer_vector.updateFields()
                    buffer_feat = QgsFeature()
                    buffer_feat.setGeometry(buffer)
                    buffer_feat.setAttributes(water_feat.attributes())
                    buffer_vector.dataProvider().addFeatures([buffer_feat])
                    buffer_vector.updateExtents()
                    
                    #QgsProject.instance().addMapLayer(buffer_vector)
                    buffers.append(buffer_vector) #Lista de buffers em camada

                
            else:
                for i in range (0, len(cotas_lista)):
                    buffer = water_geom.buffer(buffer_tamanho*(i+1), 5)
                    crs = water_layer.sourceCrs()
                    buffer_vector = QgsVectorLayer(f"{QgsWkbTypes.displayString(water_layer.wkbType())}?crs={crs.authid()}", "buffer", "memory")
                    buffer_vector.dataProvider().addAttributes(water_layer.fields())
                    buffer_vector.updateFields()
                    buffer_feat = QgsFeature()
                    buffer_feat.setGeometry(buffer)
                    buffer_feat.setAttributes(water_feat.attributes())
                    buffer_vector.dataProvider().addFeatures([buffer_feat])
                    buffer_vector.updateExtents()
                    #QgsProject.instance().addMapLayer(buffer_vector)
                    buffers.append(buffer_vector) #Lista de buffers em camada             

        else:
            lim_aquidade = 0.0002 # O limite da aquidade visual é de 0,2mm (0,0002m)
            if cn_layer.crs().isGeographic():
                extent = cn_layer.extent()
                centroid_lat = (extent.yMinimum() + extent.yMaximum()) / 2 #Pega a latitude do centroide do projeto
                buffer_size_meters = lim_aquidade * escala
                buffer_size = buffer_size_meters / (111320 * cos(radians(centroid_lat)))
               
                for i in range (0, len(cotas_lista)):
                # Aplicar buffer nas coordenadas geográficas (latitude e longitude)
                    buffer = water_geom.buffer(buffer_size*(i+1), 5)
                    crs = water_layer.sourceCrs()
                    buffer_vector = QgsVectorLayer(f"{QgsWkbTypes.displayString(water_layer.wkbType())}?crs={crs.authid()}", "buffer", "memory")
                    buffer_vector.dataProvider().addAttributes(water_layer.fields())
                    buffer_vector.updateFields()
                    buffer_feat = QgsFeature()
                    buffer_feat.setGeometry(buffer)
                    buffer_feat.setAttributes(water_feat.attributes())
                    buffer_vector.dataProvider().addFeatures([buffer_feat])
                    buffer_vector.updateExtents()
                    #QgsProject.instance().addMapLayer(buffer_vector)
                    buffers.append(buffer_vector) #Lista de buffers em camada

            else:
                
                buffer_size = lim_aquidade * escala
                for i in range (0, len(cotas_lista)):
                    buffer = water_geom.buffer(buffer_size*(i+1), 5)
                    crs = water_layer.sourceCrs()
                    buffer_vector = QgsVectorLayer(f"{QgsWkbTypes.displayString(water_layer.wkbType())}?crs={crs.authid()}", "buffer", "memory")
                    buffer_vector.dataProvider().addAttributes(water_layer.fields())
                    buffer_vector.updateFields()
                    buffer_feat = QgsFeature()
                    buffer_feat.setGeometry(buffer)
                    buffer_feat.setAttributes(water_feat.attributes())
                    buffer_vector.dataProvider().addFeatures([buffer_feat])
                    buffer_vector.updateExtents()
                    #QgsProject.instance().addMapLayer(buffer_vector)
                    buffers.append(buffer_vector) #Lista de buffers em camada

        return buffers

    def contour_buffer(self, parameters, context, buffers_lista, mold):
        
        boundaries = list()

        for buffer in buffers_lista:
            boundary = processing.run("native:polygonstolines",
                                    {'INPUT': buffer,
                                    'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']

            boundary = processing.run("native:clip", 
                                        {'INPUT':boundary,
                                        'OVERLAY':mold,
                                        'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
            #QgsProject.instance().addMapLayer(boundary)
            boundaries.append(boundary)
        
        return boundaries

    def split_contour(self, parameters, context, feedback, boundaries, cn_layer, mold_line, cotas_lista, cota_field):

        split_boundaries = list()
        for f in range (0, len(boundaries)):
            # Filtrar feições da moldura_line com base no atributo desejado (exemplo: 'category' == 1)
            atributo = cota_field #nome do atributo
            valor_cota = cotas_lista[f] #A lista de cotas crescente está par a par com o buffer

            # Criar uma nova camada temporária com as feições filtradas
            features_filtradas = [feat for feat in cn_layer.getFeatures() if feat[atributo] == valor_cota]

            crs = cn_layer.sourceCrs()
            mem_layer = QgsVectorLayer(f"{QgsWkbTypes.displayString(cn_layer.wkbType())}?crs={crs.authid()}", "feições_selecionadas", "memory")
            mem_layer.dataProvider().addAttributes(cn_layer.fields())
            mem_layer.updateFields()
            mem_layer.dataProvider().addFeatures(features_filtradas)
            mem_layer.updateExtents()

            # Executar o algoritmo de divisão com a camada filtrada
            split_boundary = processing.run("native:splitwithlines",
                                            {'INPUT': boundaries[f],
                                            'LINES': mem_layer,
                                            'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
            
            split_boundary = processing.run("native:splitwithlines",
                                            {'INPUT': split_boundary,
                                            'LINES': mold_line,
                                            'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT'] #Secção da linha pela moldura

            # Adicionar a camada de contorno seccionada ao projeto
            #QgsProject.instance().addMapLayer(split_boundary)
            split_boundaries.append(split_boundary)
        
        return split_boundaries

    def cut_cn(self, parameters, context, feedback, cn, buffer_layer, cota_field, cota):        
             
        # Atributo e valor da cota a ser filtrado
        atributo = cota_field #atributo 'cota'
        valor_cota = cota #valor de cota filtrado

        # Criar uma nova camada de memória para armazenar as feições modificadas
        crs = cn.sourceCrs()
        mem_layer = QgsVectorLayer(f"{QgsWkbTypes.displayString(cn.wkbType())}?crs={crs.authid()}", f"CN_cortada_na_cota_{valor_cota}", "memory")
        mem_layer.dataProvider().addAttributes(cn.fields())
        mem_layer.updateFields()

        trechos = list()
        # Iterar sobre as feições da camada de linhas
        for line_feat in cn.getFeatures():
            line_geom = line_feat.geometry()

            # Verificar se a feição atende ao critério de cota
            if line_feat[atributo] == valor_cota:
                # Aplicação da diferença (difference) com cada geometria da camada de buffer
                for buffer_feat in buffer_layer.getFeatures():
                    buffer_geom = buffer_feat.geometry()
                    
                    # Aplicar a diferença
                    diff_geom = line_geom.difference(buffer_geom)

                    # Criação de uma nova feição para armazenar a geometria resultante
                    new_feature = QgsFeature()
                    new_feature.setGeometry(diff_geom)
                    new_feature.setAttributes(line_feat.attributes())  # Manter os atributos da linha original
                    
                    # Adicionar a feição resultante à camada de memória
                    trechos.append(new_feature)

            else:
                # Se não for a feição com cota desejada, adicionar a feição original
                trechos.append(line_feat)

        # Atualizar a extensão da nova camada
        mem_layer.dataProvider().addFeatures(trechos)
        mem_layer.updateExtents()

        cn = processing.run("native:multiparttosingleparts", 
                        {'INPUT': mem_layer,
                        'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
        
        # Adicionar a nova camada ao projeto
        #QgsProject.instance().addMapLayer(cn)

        return cn
    
    def substituicao_trecho(self, parameters, context, feedback, split_boundary, cn_cortadas_layer, cota_field, cota):
        
        trechos_feat = list()
        for line_con in split_boundary.getFeatures():
            line_con_geom = line_con.geometry()
            line_con_geom_buffer = line_con.geometry().buffer(1, 5)
            bbox = line_con_geom_buffer.boundingBox()

            for line in cn_cortadas_layer.getFeatures(bbox):
                line_geom = line.geometry()

                if line_con_geom_buffer.intersects(line_geom):
                    
                    for line_2 in cn_cortadas_layer.getFeatures(bbox):
                        line_2_geom = line_2.geometry()

                        if line_con_geom_buffer.intersects(line_2_geom):
                            if line.id() != line_2.id() and line.id() > line_2.id() and line[cota_field] == cota and line_2[cota_field] == cota:
                                #feedback.pushInfo(f'A linha de conexão {line_con} conecta as linhas {line.id()} de cota {line[cota_field]} e {line_2.id()} de cota {line_2[cota_field]}.')
                                new_feature = QgsFeature(cn_cortadas_layer.fields())
                                new_feature.setGeometry(line_con_geom)
                                new_feature.setAttributes(line.attributes())
                                trechos_feat.append(new_feature)

        cn_cortadas_layer.dataProvider().addFeatures(trechos_feat)
        cn_cortadas_layer.updateExtents()
        #QgsProject.instance().addMapLayer(cn_cortadas_layer)
        
        return cn_cortadas_layer
    
    def layer_features_selected(self, layer):
            
        crs = layer.sourceCrs()
        outputLayer = QgsVectorLayer(f"{QgsWkbTypes.displayString(layer.wkbType())}?crs={crs.authid()}",
                                    "feições_selecionadas", 
                                    "memory")
        outputLayer.dataProvider().addAttributes(layer.fields())
        outputLayer.updateFields()
        outputFeat = layer.selectedFeatures()
        outputLayer.dataProvider().addFeatures(outputFeat)
        outputLayer.updateExtents()

        return outputLayer
    
    def fix_geometry (self, layer):

        outputLayer = processing.run("native:fixgeometries",
                                     {'INPUT':layer,
                                      'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
        
        return outputLayer
    
    def case_cn_within_water(self, layer_cn, layer_water, remove_features, percentage):
        layer_cn.startEditing()

        for linha_feature in layer_cn.getFeatures():
            geom_linha = linha_feature.geometry()
            comprimento_total = geom_linha.length()
            bbox = geom_linha.boundingBox()

            comprimento_interseccao = 0
            for poligono_feature in layer_water.getFeatures(bbox):
                geom_poligono = poligono_feature.geometry()
                interseccao = geom_linha.intersection(geom_poligono)

                if interseccao:
                    comprimento_interseccao += interseccao.length()
            
            # Verificação se a condição de eliminação é atendida
            if remove_features and comprimento_interseccao > (percentage / 100 * comprimento_total):
                layer_cn.deleteFeature(linha_feature.id())

        layer_cn.commitChanges()

        return layer_cn
    
   
    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "Adequar curvas de nível com massa d'água"

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
        return self.tr("Adequar curvas de nível com massa d'água")

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return CorrecaoCurvaNivelAlgorithm()
    
    def shortHelpString(self):
        return self.tr("Este processing identifica e adequa as curvas de nível que interceptam vetores de massa d'água à Norma da Especificação Técnica para Aquisição de Dados Geoespaciais Vetoriais (ET-ADVG) versão 3.0 (EB80-N-72.005)")
    
    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'cn_agua.png'))

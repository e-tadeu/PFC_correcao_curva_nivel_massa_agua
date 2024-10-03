# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DsgTools
                                 A QGIS plugin
 Brazilian Army Cartographic Production Tools
                              -------------------
        begin                : 2018-08-13
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Philipe Borba - Cartographic Engineer @ Brazilian Army
        email                : borba.philipe@eb.mil.br
 ***************************************************************************/

Adapted from https://github.com/dsgoficial/DsgTools/blob/67c7bca45aa3ee1630e43fcf3a9d125a2807933b/DsgTools/core/DSGToolsProcessingAlgs/Algs/ValidationAlgs/identifyDanglesAlgorithm.py#L54

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from .algRunner import AlgRunner
from .layerHandler import LayerHandler
import concurrent.futures
from collections import defaultdict
from typing import DefaultDict, Dict, Tuple, Union
import concurrent.futures
import os
import processing

from PyQt5.QtCore import QVariant
from qgis.core import (
    QgsFeatureRequest,
    QgsField,
    QgsFields,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProcessing,
    QgsProcessingFeatureSourceDefinition,
    QgsProcessingFeedback,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterNumber,
    QgsProcessingParameterVectorLayer,
    QgsSpatialIndex,
    QgsVectorLayer,
    QgsWkbTypes,
)

def pontas_soltas(self, parameters, context, feedback, inputLyr, layer_moldura):
    self.layerHandler = LayerHandler()
    algRunner = AlgRunner()

    if inputLyr is None:
        return {self.FLAGS: self.flag_id}
    onlySelected = False
    searchRadius = 0.0001
    inputIsBoundaryLayer = True
    geographicBoundsLyr = layer_moldura

    crs = inputLyr.crs()
    fields = QgsFields()
    fields.append(QgsField('reason', QVariant.String))
    point_layer = QgsVectorLayer('Point?crs={}'.format(crs.authid()), 'Pontas Soltas', 'memory')
    point_layer.dataProvider().addAttributes(fields)
    point_layer.updateFields()

    feedbackTotal = 3
    feedbackTotal += 1 if not inputIsBoundaryLayer else 0

    multiStepFeedback = QgsProcessingMultiStepFeedback(feedbackTotal, feedback)
    currentStep = 0
    multiStepFeedback.setCurrentStep(currentStep)
    multiStepFeedback.pushInfo(self.tr("Building local cache..."))
    inputLyr = algRunner.runAddAutoIncrementalField(
        inputLyr=inputLyr
        if not onlySelected
        else QgsProcessingFeatureSourceDefinition(inputLyr.id(), True),
        context=context,
        feedback=multiStepFeedback,
        fieldName="AUTO",
    )
    onlySelected = False
    currentStep += 1

    multiStepFeedback.setCurrentStep(currentStep)
    algRunner.runCreateSpatialIndex(
        inputLyr=inputLyr,
        context=context,
        feedback=multiStepFeedback,
        is_child_algorithm=True,
    )
    currentStep += 1

    multiStepFeedback.setCurrentStep(currentStep)
    multiStepFeedback.pushInfo(self.tr("Building search structure..."))
    endVerticesDict = buildInitialAndEndPointDict(self,
        inputLyr,
        algRunner,
        context=context,
        geographicBoundsLyr=geographicBoundsLyr,
        feedback=multiStepFeedback,
    )

    currentStep += 1
    multiStepFeedback.setCurrentStep(currentStep)
    multiStepFeedback.pushInfo(self.tr("Looking for dangle candidates..."))
    pointSet = searchDanglesOnPointDict(self, endVerticesDict, multiStepFeedback)
    dangleSet = set()
    relatedDict = dict()
    currentStep += 1
    multiStepFeedback.setCurrentStep(currentStep)
    multiStepFeedback.pushInfo(
        self.tr("Filtering dangles candidates with input layer features...")
    )
    danglesOnInputLayerSet = getDanglesOnInputLayerFeatures(self,
        pointSet=pointSet,
        inputLyr=inputLyr,
        ignoreDanglesOnUnsegmentedLines=False,
        inputIsBoundaryLayer=inputIsBoundaryLayer,
        relatedDict=relatedDict,
        searchRadius=searchRadius,
        feedback=multiStepFeedback,
    )
    dangleSet = dangleSet.union(danglesOnInputLayerSet)

    currentStep += 1
    multiStepFeedback.setCurrentStep(currentStep)
    multiStepFeedback.pushInfo(self.tr("Raising flags..."))
    if dangleSet:

        currentTotal = 100 / len(dangleSet)
        for current, point in enumerate(dangleSet):
            if multiStepFeedback.isCanceled():
                break
            feicao = flagFeature(self,
                QgsGeometry.fromPointXY(point),
                self.tr("Dangle on {0}").format(inputLyr.name()),
            )
            point_layer.dataProvider().addFeatures([feicao])
            multiStepFeedback.setProgress(current * currentTotal)

    point_layer.updateExtents()

    return point_layer

def buildInitialAndEndPointDict(
    self, lyr, algRunner, context, feedback, geographicBoundsLyr=None
):
    pointDict = defaultdict(set)
    nSteps = 5 if geographicBoundsLyr is not None else 3
    currentStep = 0
    multiStepFeedback = QgsProcessingMultiStepFeedback(nSteps, feedback)
    multiStepFeedback.setCurrentStep(currentStep)
    # this process of extracting the boundary is intentionally without the feedback
    # to avoid the excessive amount of error messages that are generated due to closed lines.
    boundaryLyr = algRunner.runBoundary(inputLayer=lyr, context=context)
    currentStep += 1
    multiStepFeedback.setCurrentStep(currentStep)
    boundaryLyr = algRunner.runMultipartToSingleParts(
        inputLayer=boundaryLyr, context=context, feedback=multiStepFeedback
    )
    currentStep += 1
    multiStepFeedback.setCurrentStep(currentStep)
    if geographicBoundsLyr is not None:
        algRunner.runCreateSpatialIndex(
            inputLyr=boundaryLyr,
            context=context,
            feedback=multiStepFeedback,
            is_child_algorithm=True,
        )
        currentStep += 1
        multiStepFeedback.setCurrentStep(currentStep)
        boundaryLyr = algRunner.runExtractByLocation(
            inputLyr=boundaryLyr,
            intersectLyr=geographicBoundsLyr,
            context=context,
            feedback=multiStepFeedback,
        )
        currentStep += 1

    multiStepFeedback.setCurrentStep(currentStep)
    featCount = boundaryLyr.featureCount()
    if featCount == 0:
        return pointDict
    step = 100 / featCount
    for current, feat in enumerate(boundaryLyr.getFeatures()):
        if multiStepFeedback.isCanceled():
            break
        geom = feat.geometry()
        if geom is None or not geom.isGeosValid():
            continue
        id = feat["AUTO"]
        pointList = geom.asMultiPoint() if geom.isMultipart() else [geom.asPoint()]
        for point in pointList:
            pointDict[point].add(id)
        multiStepFeedback.setProgress(current * step)
    return pointDict

def searchDanglesOnPointDict(
    self, endVerticesDict: Dict, feedback: QgsProcessingFeedback
) -> set:
    """
    Counts the number of points on each endVerticesDict's key and returns a set of QgsPoint built from key candidate.
    """
    pointSet = set()
    nVertexes = len(endVerticesDict)
    if nVertexes == 0:
        return pointSet
    localTotal = 100 / nVertexes if nVertexes else 0
    # actual search for dangles
    for current, point in enumerate(endVerticesDict):
        if feedback.isCanceled():
            break
        # this means we only have one occurrence of point, therefore it is a dangle
        if len(endVerticesDict[point]) <= 1:
            pointSet.add(point)
        feedback.setProgress(localTotal * current)
    return pointSet

def makeBoundaries(self, lyr, context, feedback):
    parameters = {"INPUT": lyr, "OUTPUT": "memory:"}
    output = processing.run("native:boundary", parameters, context=context)
    return output["OUTPUT"]

def getDanglesOnInputLayerFeatures(
    self,
    pointSet: set,
    inputLyr: QgsVectorLayer,
    searchRadius: float,
    ignoreDanglesOnUnsegmentedLines: bool = False,
    inputIsBoundaryLayer: bool = False,
    relatedDict: dict = None,
    feedback: QgsProcessingMultiStepFeedback = None,
) -> set:
    inputLayerDangles = set()
    nPoints = len(pointSet)
    relatedDict = dict() if relatedDict is None else relatedDict
    if nPoints == 0:
        return inputLayerDangles
    localTotal = 100 / nPoints
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() - 1)
    futures = set()

    def evaluate(point) -> Union[QgsPointXY, None]:
        qgisPoint = QgsGeometry.fromPointXY(point)
        geomEngine = QgsGeometry.createGeometryEngine(qgisPoint.constGet())
        geomEngine.prepareGeometry()
        buffer = qgisPoint.buffer(searchRadius, -1)
        bufferBB = buffer.boundingBox()
        # search radius to narrow down candidates
        request = QgsFeatureRequest().setFilterRect(bufferBB)
        bufferCount, intersectCount = 0, 0
        point_relationship_lambda = (
            lambda x: geomEngine.intersects(x.constGet())
            or qgisPoint.distance(x) < 1e-8
            if ignoreDanglesOnUnsegmentedLines
            else geomEngine.touches(x.constGet())
        )
        for feat in inputLyr.getFeatures(request):
            geom = feat.geometry()
            if feedback is not None and feedback.isCanceled():
                return None
            if geom.intersects(buffer):
                bufferCount += 1
                if point_relationship_lambda(geom):
                    intersectCount += 1
        if intersectCount > 1:
            return None
        if inputIsBoundaryLayer and intersectCount == 1 and bufferCount == 1:
            if relatedDict == dict():
                return point
            if (
                point in relatedDict
                and relatedDict[point]["candidateCount"]
                == relatedDict[point]["bufferCount"]
                and relatedDict[point]["candidateCount"] > 0
            ):
                return None
            return point
        return point if bufferCount != intersectCount else None

    multiStepFeedback = (
        QgsProcessingMultiStepFeedback(2, feedback)
        if feedback is not None
        else None
    )
    multiStepFeedback.setCurrentStep(0)
    for current, point in enumerate(pointSet):
        if multiStepFeedback is not None and multiStepFeedback.isCanceled():
            break
        futures.add(pool.submit(evaluate, point))
        if multiStepFeedback is not None:
            multiStepFeedback.setProgress(current * localTotal)
    multiStepFeedback.setCurrentStep(1)
    for current, future in enumerate(concurrent.futures.as_completed(futures)):
        if multiStepFeedback is not None and multiStepFeedback.isCanceled():
            break
        output = future.result()
        if output is not None:
            inputLayerDangles.add(output)
        if multiStepFeedback is not None:
            multiStepFeedback.setProgress(current * localTotal)
    return inputLayerDangles

def getDanglesWithFilterLayers(
    self,
    pointSet: set,
    filterLayer: QgsVectorLayer,
    searchRadius: float,
    feedback: QgsProcessingMultiStepFeedback,
    ignoreNotSplit: bool = False,
) -> Tuple[set, Dict[QgsPointXY, dict]]:
    """
    Builds buffer areas from each point and evaluates the intersecting lines.
    If the number of candidates that intersect the buffer is different than the
    number of intersections of the point with the neighbors, it is a dangle.

    Returns the set containing the dangles.
    """
    nPoints = len(pointSet)
    danglesWithFilterLayers = set()
    relatedDict = dict()
    if nPoints == 0:
        return danglesWithFilterLayers, relatedDict
    localTotal = 100 / nPoints
    multiStepFeedback = QgsProcessingMultiStepFeedback(4, feedback)
    multiStepFeedback.setCurrentStep(0)
    spatialIdx, allFeatureDict = buildSpatialIndexAndIdDict(self,
        filterLayer, feedback=multiStepFeedback
    )
    multiStepFeedback.setCurrentStep(1)

    def evaluate(point: QgsPointXY) -> dict:
        candidateCount, bufferCount = 0, 0
        qgisPoint = QgsGeometry.fromPointXY(point)
        # search radius to narrow down candidates
        buffer = qgisPoint.buffer(searchRadius, -1)
        bufferBB = buffer.boundingBox()
        # if there is only one feat in candidateIds, that means that it is not a dangle
        for id in spatialIdx.intersects(bufferBB):
            candidateGeom = allFeatureDict[id].geometry()
            if multiStepFeedback.isCanceled():
                return None
            if buffer.intersects(candidateGeom):
                bufferCount += 1
                if qgisPoint.intersects(candidateGeom):
                    candidateCount += 1
        return point, {"candidateCount": candidateCount, "bufferCount": bufferCount}

    futures = set()
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() - 1)
    multiStepFeedback.setCurrentStep(2)
    for current, point in enumerate(pointSet):
        if multiStepFeedback.isCanceled():
            break
        futures.add(pool.submit(evaluate, point))
        multiStepFeedback.setProgress(localTotal * current)
    multiStepFeedback.setCurrentStep(3)
    for current, future in enumerate(concurrent.futures.as_completed(futures)):
        if multiStepFeedback.isCanceled():
            break
        dangle, dangleDict = future.result()
        relatedDict[dangle] = dangleDict
        if dangleDict["candidateCount"] != dangleDict["bufferCount"]:
            danglesWithFilterLayers.add(dangle)
        multiStepFeedback.setProgress(localTotal * current)

    return danglesWithFilterLayers, relatedDict

def buildSpatialIndexAndIdDict(self, inputLyr, feedback=None):
    """
    creates a spatial index for the centroid layer
    """
    spatialIdx = QgsSpatialIndex()
    idDict = {}
    for feat in inputLyr.getFeatures():
        if feedback is not None and feedback.isCanceled():
            break
        spatialIdx.addFeature(feat)
        idDict[feat.id()] = feat
    return spatialIdx, idDict

def flagFeature(self, flagGeom, flagText, featid=None, fromWkb=False, sink=None):
    """
    Creates and adds to flagSink a new flag with the reason.
    :param flagGeom: (QgsGeometry) geometry of the flag;
    :param flagText: (string) Text of the flag
    """
    newFeat = QgsFeature(getFlagFields(self, addFeatId=featid is not None))
    newFeat["reason"] = flagText
    if featid is not None:
        newFeat["featid"] = featid
    if fromWkb:
        geom = QgsGeometry()
        geom.fromWkb(flagGeom)
        newFeat.setGeometry(geom)
    else:
        newFeat.setGeometry(flagGeom)
    
    return newFeat

def getFlagFields(self, addFeatId=False):
    fields = QgsFields()
    fields.append(QgsField("reason", QVariant.String))
    if addFeatId:
        fields.append(QgsField("featid", QVariant.String))
    return fields
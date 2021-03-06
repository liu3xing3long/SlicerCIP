import os, sys
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from collections import OrderedDict
import time
import numpy as np
import SimpleITK as sitk
import math
import itertools

import scipy.optimize as scipy_opt
import vtk.util.numpy_support as nc
from CIP.logic.SlicerUtil import SlicerUtil

from CIP.logic import Util


#
# CIP_TracheaStentPlanningOptimized
#
class CIP_TracheaStentPlanningOptimized(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Trachea Stent Planning Optimized"
        self.parent.categories = SlicerUtil.CIP_ModulesCategory
        self.parent.dependencies = [SlicerUtil.CIP_ModuleName]
        self.parent.contributors = ["Applied Chest Imaging Laboratory", "Brigham and Women's Hospital"]
        self.parent.helpText = """Write here the description of your module"""
        self.parent.acknowledgementText = SlicerUtil.ACIL_AcknowledgementText


#
# CIP_TracheaStentPlanningOptimizedWidget
#

class CIP_TracheaStentPlanningOptimizedWidget(ScriptedLoadableModuleWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        self.executedSetup = False
        ScriptedLoadableModuleWidget.__init__(self, parent)

    @property
    def currentStentType(self):
        """ Key of the currently selected stent type (YStent, TStent)
        :return: Key of the currently selected stent type
        """
        return self.stentTypesRadioButtonGroup.checkedButton().text

    def setup(self):
        """This is called one time when the module GUI is initialized
        """
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = CIP_TracheaStentPlanningOptimizedLogic()

        # Create objects that can be used anywhere in the module. Example: in most cases there should be just one
        # object of the logic class
        self.removeInvisibleFiducialsTimer = qt.QTimer()
        self.removeInvisibleFiducialsTimer.setInterval(200)
        self.removeInvisibleFiducialsTimer.timeout.connect(self.__removeInvisibleMarkups__)

        self.__initModuleVars__()

        #### Layout selection
        self.layoutCollapsibleButton = ctk.ctkCollapsibleButton()
        self.layoutCollapsibleButton.text = "Layout Selection"
        self.layoutCollapsibleButton.setChecked(False)
        # self.layoutCollapsibleButton.setFixedSize(600,40)
        self.layout.addWidget(self.layoutCollapsibleButton)
        self.layoutFormLayout = qt.QGridLayout(self.layoutCollapsibleButton)
        # self.fiducialsFormLayout.setFormAlignment(4)

        #
        # Four-Up Button
        #
        self.fourUpButton = qt.QPushButton()
        self.fourUpButton.toolTip = "Four-up view."
        self.fourUpButton.enabled = True
        self.fourUpButton.setFixedSize(40, 40)
        fourUpIcon = qt.QIcon(":/Icons/LayoutFourUpView.png")
        self.fourUpButton.setIcon(fourUpIcon)
        self.layoutFormLayout.addWidget(self.fourUpButton, 0, 0)
        #
        # Red Slice Button
        #
        self.redViewButton = qt.QPushButton()
        self.redViewButton.toolTip = "Red slice only."
        self.redViewButton.enabled = True
        self.redViewButton.setFixedSize(40, 40)
        redIcon = qt.QIcon(":/Icons/LayoutOneUpRedSliceView.png")
        self.redViewButton.setIcon(redIcon)
        self.layoutFormLayout.addWidget(self.redViewButton, 0, 1)

        #
        # Yellow Slice Button
        #
        self.yellowViewButton = qt.QPushButton()
        self.yellowViewButton.toolTip = "Yellow slice only."
        self.yellowViewButton.enabled = True
        self.yellowViewButton.setFixedSize(40, 40)
        yellowIcon = qt.QIcon(":/Icons/LayoutOneUpYellowSliceView.png")
        self.yellowViewButton.setIcon(yellowIcon)
        self.layoutFormLayout.addWidget(self.yellowViewButton, 0, 2)

        #
        # Green Slice Button
        #
        self.greenViewButton = qt.QPushButton()
        self.greenViewButton.toolTip = "Yellow slice only."
        self.greenViewButton.enabled = True
        self.greenViewButton.setFixedSize(40, 40)
        greenIcon = qt.QIcon(":/Icons/LayoutOneUpGreenSliceView.png")
        self.greenViewButton.setIcon(greenIcon)
        self.layoutFormLayout.addWidget(self.greenViewButton, 0, 3)

        #
        # Buttons labels
        #
        # self.labelsGroupBox = qt.QFrame()
        # hBox = qt.QHBoxLayout()
        # hBox.setSpacing(10)
        # self.labelsGroupBox.setLayout(hBox)
        # self.labelsGroupBox.setFixedSize(450,26)
        # self.layoutGroupBox.layout().addWidget(self.labelsGroupBox,0,4)
        fourUpLabel = qt.QLabel("Four-up")
        # fourUpLabel.setFixedHeight(10)
        self.layoutFormLayout.addWidget(fourUpLabel, 1, 0)
        redLabel = qt.QLabel("  Axial")
        self.layoutFormLayout.addWidget(redLabel, 1, 1)
        yellowLabel = qt.QLabel("Saggital")
        self.layoutFormLayout.addWidget(yellowLabel, 1, 2)
        greenLabel = qt.QLabel("Coronal")
        self.layoutFormLayout.addWidget(greenLabel, 1, 3)

        ######
        # Main parameters
        mainAreaCollapsibleButton = ctk.ctkCollapsibleButton()
        mainAreaCollapsibleButton.text = "Main parameters"
        self.layout.addWidget(mainAreaCollapsibleButton)
        self.mainAreaLayout = qt.QGridLayout(mainAreaCollapsibleButton)

        # Main volume selector
        inputVolumeLabel = qt.QLabel("Volume")
        inputVolumeLabel.setStyleSheet("font-weight: bold; margin-left:5px")
        self.mainAreaLayout.addWidget(inputVolumeLabel, 0, 0)
        self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
        self.inputVolumeSelector.nodeTypes = ("vtkMRMLScalarVolumeNode", "")
        self.inputVolumeSelector.selectNodeUponCreation = True
        self.inputVolumeSelector.autoFillBackground = True
        self.inputVolumeSelector.addEnabled = False
        self.inputVolumeSelector.noneEnabled = False
        self.inputVolumeSelector.removeEnabled = False
        self.inputVolumeSelector.showHidden = False
        self.inputVolumeSelector.showChildNodeTypes = False
        self.inputVolumeSelector.setMRMLScene(slicer.mrmlScene)
        # self.inputVolumeSelector.setStyleSheet("margin:0px 0 0px 0; padding:2px 0 2px 5px")
        self.mainAreaLayout.addWidget(self.inputVolumeSelector, 0, 1)

        # Radio Buttons types
        stentTypesLabel = qt.QLabel("Stent type")
        stentTypesLabel.setStyleSheet("font-weight: bold; margin-left:5px")
        stentTypesLabel.setFixedWidth(130)
        self.mainAreaLayout.addWidget(stentTypesLabel, 1, 0)
        self.stentTypesFrame = qt.QFrame()
        self.stentTypesLayout = qt.QHBoxLayout(self.stentTypesFrame)
        self.mainAreaLayout.addWidget(self.stentTypesFrame)
        self.mainAreaLayout.addWidget(self.stentTypesFrame, 1, 1)
        #
        self.stentTypesRadioButtonGroup = qt.QButtonGroup()
        for stent in self.logic.stentTypes.keys():
            rbitem = qt.QRadioButton(stent)
            self.stentTypesRadioButtonGroup.addButton(rbitem)
            self.stentTypesLayout.addWidget(rbitem)
        self.stentTypesRadioButtonGroup.buttons()[0].setChecked(True)
        # FIXME: disable temporarily the T stent  because there is no implementation yet
        self.stentTypesRadioButtonGroup.buttons()[1].setEnabled(False)

        # Radio Buttons fiducial types
        typesLabel = qt.QLabel("Select fiducial type")
        typesLabel.setStyleSheet("font-weight: bold; margin-left:5px")
        typesLabel.setFixedWidth(130)
        self.mainAreaLayout.addWidget(typesLabel)
        self.fiducialTypesFrame = qt.QFrame()
        self.fiducialTypesLayout = qt.QHBoxLayout(self.fiducialTypesFrame)
        self.mainAreaLayout.addWidget(typesLabel, 2, 0)
        self.mainAreaLayout.addWidget(self.fiducialTypesFrame, 2, 1)
        self.segmentTypesRadioButtonGroup = qt.QButtonGroup()
        st = self.stentTypesRadioButtonGroup.checkedButton().text
        for id, key in enumerate(self.logic.getFiducialList(st)):
            rbitem = qt.QRadioButton(key)
            self.segmentTypesRadioButtonGroup.addButton(rbitem, id)
            self.fiducialTypesLayout.addWidget(rbitem)
            if key == "Middle":
                rbitem.visible = False

        self.segmentTypesRadioButtonGroup.buttons()[0].setChecked(True)

        #
        # Apply Button
        #
        self.segmentTracheaButton = ctk.ctkPushButton()
        self.segmentTracheaButton.text = "Segment trachea"
        self.segmentTracheaButton.toolTip = "Run the trachea segmentation algorithm."
        currentpath = os.path.dirname(os.path.realpath(__file__))
        self.iconsPath = os.path.join(currentpath, "Resources", "Icons")
        iconPath = os.path.join(self.iconsPath, "TracheaModel.png")
        self.segmentTracheaButton.setIcon(qt.QIcon(iconPath))
        self.segmentTracheaButton.setIconSize(qt.QSize(24, 24))
        self.segmentTracheaButton.iconAlignment = 0x0001  # Align the icon to the right. See http://qt-project.org/doc/qt-4.8/qt.html#AlignmentFlag-enum for a complete list
        self.segmentTracheaButton.buttonTextAlignment = (0x0081)  # Aling the text to the left and vertical center
        self.segmentTracheaButton.setFixedSize(140, 40)
        self.segmentTracheaButton.setStyleSheet("background-color: #3067FF; color:white; font-weight:bold;")
        self.mainAreaLayout.addWidget(self.segmentTracheaButton, 3, 0, 1, 3, 0x0004)
        self.mainAreaLayout.setRowMinimumHeight(3, 70)

        # Threshold
        self.thresholdLevelLabel = qt.QLabel("Segmentation fine tuning")
        self.thresholdLevelLabel.toolTip = "Fine tune the trachea segmentation in case it is not properly adjusted"
        self.mainAreaLayout.addWidget(self.thresholdLevelLabel, 5, 0)
        self.thresholdLevelSlider = qt.QSlider()
        self.thresholdLevelSlider.orientation = 1  # Horizontal
        # self.thresholdLevelSlider.setTickInterval(1)
        self.thresholdLevelSlider.setTickPosition(2)
        self.thresholdLevelSlider.minimum = 1
        self.thresholdLevelSlider.maximum = 200
        self.thresholdLevelSlider.setValue(150)
        self.thresholdLevelSlider.setSingleStep(1)
        self.thresholdLevelSlider.enabled = True
        self.thresholdLevelSlider.setTracking(False)
        self.thresholdLevelSlider.toolTip = "Fine tune the trachea segmentation in case it is not properly adjusted"
        self.mainAreaLayout.addWidget(self.thresholdLevelSlider, 5, 1, 1, 2)

        # Stent Radius
        self.radiusLabel1 = qt.QLabel("Radius 1")
        self.mainAreaLayout.addWidget(self.radiusLabel1, 6, 0)
        self.radiusLevelSlider1 = qt.QSlider()
        self.radiusLevelSlider1.orientation = 1  # Horizontal
        self.radiusLevelSlider1.setTickPosition(2)
        self.radiusLevelSlider1.minimum = 1
        self.radiusLevelSlider1.maximum = 100
        self.radiusLevelSlider1.setValue(50)
        self.radiusLevelSlider1.setSingleStep(1)
        self.radiusLevelSlider1.enabled = True
        self.mainAreaLayout.addWidget(self.radiusLevelSlider1, 6, 1, 1, 2)

        self.radiusLabel2 = qt.QLabel("Radius 2")
        self.mainAreaLayout.addWidget(self.radiusLabel2, 7, 0)
        self.radiusLevelSlider2 = qt.QSlider()
        self.radiusLevelSlider2.orientation = 1  # Horizontal
        self.radiusLevelSlider2.setTickPosition(2)
        self.radiusLevelSlider2.minimum = 1
        self.radiusLevelSlider2.maximum = 100
        self.radiusLevelSlider2.setValue(50)
        self.radiusLevelSlider2.setSingleStep(1)
        self.radiusLevelSlider2.enabled = True
        self.mainAreaLayout.addWidget(self.radiusLevelSlider2, 7, 1, 1, 2)

        self.radiusLabel3 = qt.QLabel("Radius 3")
        self.mainAreaLayout.addWidget(self.radiusLabel3, 8, 0)
        self.radiusLevelSlider3 = qt.QSlider()
        self.radiusLevelSlider3.orientation = 1  # Horizontal
        self.radiusLevelSlider3.setTickPosition(2)
        self.radiusLevelSlider3.minimum = 1
        self.radiusLevelSlider3.maximum = 200
        self.radiusLevelSlider3.setValue(50)
        self.radiusLevelSlider3.setSingleStep(1)
        self.radiusLevelSlider3.enabled = True
        self.mainAreaLayout.addWidget(self.radiusLevelSlider3, 8, 1, 1, 2)

        ## Measurements
        self.measurementsFrame = qt.QFrame()
        frameLayout = qt.QGridLayout(self.measurementsFrame)
        self.measurementsTableViews = dict()
        for key in self.logic.getStentKeys():
            label = qt.QLabel("{0} measurements".format(key))
            label.setStyleSheet("margin-top:15px; font-weight:bold")
            self.measurementsTableViews[key] = qt.QTableView()
            self.measurementsTableViews[key].sortingEnabled = True
            self.measurementsTableViews[key].setFixedSize(285, 120)

            # FIXME: hide temporarily the T stent table because there is no implementation yet
            if key == self.logic.STENT_Y:
                frameLayout.addWidget(label, 0, 0)
                frameLayout.addWidget(self.measurementsTableViews[key], 1, 0)
        # Angles
        self.anglesTableViews = dict()
        for key in self.logic.getStentKeys():
            self.anglesTableViews[key] = qt.QTableView()
            self.anglesTableViews[key].sortingEnabled = True
            self.anglesTableViews[key].setFixedSize(250, 100)

            # FIXME: hide temporarily the T stent table because there is no implementation yet
            if key == self.logic.STENT_Y:
                frameLayout.addWidget(self.anglesTableViews[key], 1, 1)


        self.mainAreaLayout.addWidget(self.measurementsFrame, 9, 0, 1, 3)
        self.__initMeasurementsTables__()

        self.layout.addStretch(1)

        ##### Connections
        self.fourUpButton.connect('clicked()', self.__onFourUpButton__)
        self.redViewButton.connect('clicked()', self.__onRedViewButton__)
        self.yellowViewButton.connect('clicked()', self.__onYellowViewButton__)
        self.greenViewButton.connect('clicked()', self.__onGreenViewButton__)

        self.inputVolumeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.__onCurrentVolumeNodeChanged__)
        self.stentTypesRadioButtonGroup.connect("buttonClicked (QAbstractButton*)",
                                                self.__onStentTypesRadioButtonClicked__)
        self.segmentTypesRadioButtonGroup.connect("buttonClicked (QAbstractButton*)",
                                                  self.__onSegmentRadioButtonClicked__)

        self.segmentTracheaButton.connect('clicked(bool)', self.__onRunSegmentationButton__)
        self.thresholdLevelSlider.connect('valueChanged(int)', self.__onApplyThreshold__)
        # self.thresholdLevelSlider.connect('sliderStepChanged()', self.__onApplyThreshold__)
        # self.generate3DModelButton.connect('clicked(bool)', self.__onGenerate3DModelButton__)
        self.radiusLevelSlider1.connect('valueChanged(int)', self.__onStentRadiusChange__)
        self.radiusLevelSlider2.connect('valueChanged(int)', self.__onStentRadiusChange__)
        self.radiusLevelSlider3.connect('valueChanged(int)', self.__onStentRadiusChange__)

        slicer.mrmlScene.AddObserver(slicer.vtkMRMLScene.EndCloseEvent, self.__onSceneClosed__)

        if self.inputVolumeSelector.currentNodeID != "":
            self.logic.setActiveVolume(self.inputVolumeSelector.currentNodeID, self.__onFiducialModified__,
                                       self.__onFiducialAdded__)
            self.logic.setActiveFiducialListNode(self.currentStentType, self.segmentTypesRadioButtonGroup.checkedId())
            SlicerUtil.setFiducialsCursorMode(True, keepFiducialsModeOn=True)
        self.executedSetup = True
        self.__refreshUI__()

    def cleanup(self):
        pass

    def enter(self):
        """Enter the module. If there was a previously active volume selected, make the volume (ant the possible labelmap)
        as active in the scene"""
        if not self.executedSetup:
            # enter is executed before setup, so the first time there's nothing to do
            return
        volumeId = self.inputVolumeSelector.currentNodeID
        if volumeId is not None:
            labelmapId = None
            if self.logic.currentLabelmapResults is not None:
                labelmapId = self.logic.currentLabelmapResults.GetID()
            SlicerUtil.setActiveVolumeIds(volumeId, labelmapId)
            SlicerUtil.centerAllVolumes()

    def exit(self):
        """This is invoked every time that we switch to another module (not only when Slicer is closed)."""
        # Remove stent model if persistent-mode is not check (
        self.removeInvisibleFiducialsTimer.stop()
        SlicerUtil.setFiducialsCursorMode(False)

    def cleanup(self):
        """This is invoked as a destructor of the GUI when the module is no longer going to be used"""
        self.removeInvisibleFiducialsTimer.stop()

    def __initModuleVars__(self):
        """ Initializes the state of the module
        """
        self.logic.reset()
        self.lastThreshold = -1
        self.isSegmentationExecuted = False
        self.removingInvisibleMarkpus = False
        self.removeInvisibleFiducialsTimer.stop()

    def __refreshUI__(self):
        """ Refresh the state of some controls in the UI
        """
        self.segmentTracheaButton.enabled = self.inputVolumeSelector.currentNodeID != ""

        self.thresholdLevelSlider.visible = self.thresholdLevelLabel.visible = \
            self.radiusLabel1.visible = self.radiusLevelSlider1.visible = \
            self.radiusLabel2.visible = self.radiusLevelSlider2.visible = \
            self.radiusLabel3.visible = self.radiusLevelSlider3.visible = \
            self.measurementsFrame.visible = \
            self.isSegmentationExecuted

    def __moveForwardStentType__(self):
        """ Move the fiducial type one step forward
        :return:
        """
        i = self.segmentTypesRadioButtonGroup.checkedId()
        if i < len(self.segmentTypesRadioButtonGroup.buttons()) - 1:
            self.segmentTypesRadioButtonGroup.buttons()[i + 1].setChecked(True)
        self.logic.setActiveFiducialListNode(self.currentStentType, self.segmentTypesRadioButtonGroup.checkedId())

    def __removeInvisibleMarkups__(self):
        """ Remove all the extra markups that are not visible right now
        :return:
        """
        modified = False
        for markupNodeList in self.logic.currentFiducialsListNodes.itervalues():
            for markupNode in markupNodeList:
                if markupNode.GetNumberOfMarkups() > 1:
                    self.removingInvisibleMarkpus = True
                    while markupNode.GetNumberOfMarkups() > 1:
                        markupNode.RemoveMarkup(0)
                        modified = True
        self.removingInvisibleMarkpus = False
        if self.isSegmentationExecuted and modified:
            # We changed the position of one of the previously placed fiducials.
            # Therefore, we need to redraw the stent cylinders
            self.logic.updateCylindersPositionFromFiducials(self.currentStentType)

    def __initMeasurementsTables__(self):
        """ Init the required structures for the tables of stent measurements (ratio and length) and angles
        """
        self.measurementsTableModels = dict()
        for key in self.logic.getStentKeys():
            self.measurementsTableModels[key] = qt.QStandardItemModel()
            self.measurementsTableViews[key].setModel(self.measurementsTableModels[key])

            # Horizontal header
            # tableModel.setHorizontalHeaderItem(0, qt.QStandardItem("Position"))
            self.measurementsTableModels[key].setHorizontalHeaderItem(0, qt.QStandardItem("Length (mm)"))
            self.measurementsTableModels[key].setHorizontalHeaderItem(1, qt.QStandardItem("Radius (mm)"))

            # Vertical header
            self.measurementsTableModels[key].setVerticalHeaderItem(0, qt.QStandardItem("Top"))
            label = "Bottom left" if key == self.logic.STENT_Y else "Bottom"
            self.measurementsTableModels[key].setVerticalHeaderItem(1, qt.QStandardItem(label))
            label = "Bottom right" if key == self.logic.STENT_Y else "Outside"
            self.measurementsTableModels[key].setVerticalHeaderItem(2, qt.QStandardItem(label))

            # Reset all items
            for row in range(3):
                for col in range(2):
                    item = qt.QStandardItem()
                    item.setData(0, qt.Qt.DisplayRole)
                    item.setEditable(False)
                    self.measurementsTableModels[key].setItem(row, col, item)

        ## Angles
        self.anglesTableModels = dict()
        for key in self.logic.getStentKeys():
            self.anglesTableModels[key] = qt.QStandardItemModel()
            self.anglesTableViews[key].setModel(self.anglesTableModels[key])

            # Horizontal header
            # self.anglesTableModels[key].setHorizontalHeaderItem(0, qt.QStandardItem("Position"))
            self.anglesTableModels[key].setHorizontalHeaderItem(0, qt.QStandardItem("Angle (degrees)"))

            # Vertical header
            if key == self.logic.STENT_Y:
                self.anglesTableModels[key].setVerticalHeaderItem(0, qt.QStandardItem("Trachea-Left branch"))
                self.anglesTableModels[key].setVerticalHeaderItem(1, qt.QStandardItem("Trachea-Right branch"))

            # Reset all items
            for row in range(2):
                item = qt.QStandardItem()
                item.setData(0, qt.Qt.DisplayRole)
                item.setEditable(False)
                self.anglesTableModels[key].setItem(row, 0, item)


    def __refreshMeasurementsTables__(self):
        """ Refresh the values in the measurements tables (GUI)
        """
        key = self.logic.currentStentType
        # for key in self.logic.getStentKeys():
        measures = self.logic.currentMeasurements[key]
        model = self.measurementsTableModels[key]
        for row in range(len(measures)):
            for col in range(2):
                item = qt.QStandardItem()
                item.setData(measures[row][col], qt.Qt.DisplayRole)
                item.setEditable(False)
                model.setItem(row, col, item)

        model2 = self.anglesTableModels[key]
        item = qt.QStandardItem()
        item.setData(self.logic.currentAngles[key][0], qt.Qt.DisplayRole)
        item.setEditable(False)
        model2.setItem(0, 0, item)

        item = qt.QStandardItem()
        item.setData(self.logic.currentAngles[key][1], qt.Qt.DisplayRole)
        item.setEditable(False)
        model2.setItem(1, 0, item)


    ############
    ##  Events
    ############
    def __onFiducialAdded__(self, fiducialsNode, event):
        """ Added a new fiducial markup.
        The fiducialTypesRadioButtonGroup will move one position forward.
        :param fiducialsNode:
        :param event:
        :return:
        """
        # self.__updateFiducialsState__(fiducialsNode)
        #self.__moveForwardStentType__()
        self.removeInvisibleFiducialsTimer.start()
        if self.isSegmentationExecuted:
            self.__refreshMeasurementsTables__()

    def __onFiducialModified__(self, fiducialsNode, event):
        if not self.removingInvisibleMarkpus:
            # while fiducialsNode.GetNumberOfMarkups() > 1:
            # for i in range(fiducialsNode.GetNumberOfMarkups() - 1):
            # Remove previously existing markup
            # fiducialsNode.RemoveMarkup(0)
            # fiducialsNode.SetNthMarkupVisibility(i, False)
            if self.isSegmentationExecuted:
                # Refresh just cylinders
                self.logic.updateCylindersPositionFromFiducials(self.currentStentType)
                self.__refreshMeasurementsTables__()

    def __onFourUpButton__(self):
        SlicerUtil.changeLayout(3)

    def __onRedViewButton__(self):
        SlicerUtil.changeLayout(6)

    def __onYellowViewButton__(self):
        SlicerUtil.changeLayout(7)

    def __onGreenViewButton__(self):
        SlicerUtil.changeLayout(8)

    def __onCurrentVolumeNodeChanged__(self, node):
        """ Active volume node changes. If there was a previously loaded volume, the user will be asked
        to confirm that all the previously existing nodes will be removed
        :param node: scalar node that has been selected
        """
        # Block the signals for the volume selector because otherwise duplicated events are triggered for an unknown reason! (yes, it happened once again...)
        self.inputVolumeSelector.blockSignals(True)
        if node is not None and self.logic.currentVolumeId is not None and node.GetID() != self.logic.currentVolumeId:
            # There was a previously active volume
            currentVolumeName = slicer.mrmlScene.GetNodeByID(self.logic.currentVolumeId).GetName()
            # Ask the user (all the structures will be reset)
            if qt.QMessageBox.question(slicer.util.mainWindow(), "Reset volume?",
                                       "All the elements for the current volume ({0}) will be removed. Are you sure?".format(
                                           currentVolumeName),
                                       qt.QMessageBox.Yes | qt.QMessageBox.No) == qt.QMessageBox.Yes:
                self.__initModuleVars__()
            else:
                # Abort the operation
                self.inputVolumeSelector.setCurrentNodeID(self.logic.currentVolumeId)
                # Activate the signals again (regular behaviour)
                self.inputVolumeSelector.blockSignals(False)
                return
        if node is not None:
            self.logic.setActiveVolume(node.GetID(), self.__onFiducialModified__, self.__onFiducialAdded__)
            SlicerUtil.setActiveVolumeIds(node.GetID())
            SlicerUtil.setFiducialsCursorMode(True, keepFiducialsModeOn=True)
            self.logic.setActiveFiducialListNode(self.currentStentType, self.segmentTypesRadioButtonGroup.checkedId())
            self.stentTypesRadioButtonGroup.buttons()[0].setChecked(True)
        self.__refreshUI__()
        # Activate the signals again (regular behaviour)
        self.inputVolumeSelector.blockSignals(False)

    def __onStentTypesRadioButtonClicked__(self, button):
        # Remove all the existing buttons in TypesGroup
        for b in self.segmentTypesRadioButtonGroup.buttons():
            b.hide()
            b.delete()

        # Get the selected button key
        # key = self.logic.stentTypes[self.stentTypesRadioButtonGroup.checked
        # Add all the subtypes with the full description
        for item in self.logic.getFiducialList(self.currentStentType):
            rbitem = qt.QRadioButton(item)
            self.segmentTypesRadioButtonGroup.addButton(rbitem)
            self.fiducialTypesLayout.addWidget(rbitem)
        self.segmentTypesRadioButtonGroup.buttons()[0].setChecked(True)

        #self.__initMeasurementsTables__()
        self.logic.setActiveFiducialListNode(self.currentStentType, 0)
        self.logic.currentStentType = self.currentStentType

    def __onSegmentRadioButtonClicked__(self, button):
        """ One of the radio buttons has been pressed
        :param button:
        :return:
        """
        SlicerUtil.setFiducialsCursorMode(True, keepFiducialsModeOn=True)
        self.logic.setActiveFiducialListNode(self.currentStentType, self.segmentTypesRadioButtonGroup.checkedId())

    def __onRunSegmentationButton__(self):
        self.thresholdLevelSlider.setValue(100)
        self.logic.runSegmentationPipeline(self.currentStentType)


        self.isSegmentationExecuted = True

        self.updateSliders()

        self.__refreshMeasurementsTables__()
        self.__refreshUI__()
        # Change to conventional layout if 3D view is not visible to show the 3D model
        # if not SlicerUtil.is3DViewVisible():
        #     SlicerUtil.changeLayout(1)

    def updateSliders(self):

        self.radiusLevelSlider1.blockSignals(True)
        self.radiusLevelSlider1.setValue(self.logic.optim_params[1][0]*10)
        self.radiusLevelSlider1.blockSignals(False)

        self.radiusLevelSlider2.blockSignals(True)
        self.radiusLevelSlider2.setValue(self.logic.optim_params[1][1]*10)
        self.radiusLevelSlider2.blockSignals(False)

        self.radiusLevelSlider3.blockSignals(True)
        self.radiusLevelSlider3.setValue(self.logic.optim_params[1][2]*10)
        self.radiusLevelSlider3.blockSignals(False)

    def __onApplyThreshold__(self, val):
        """ Fine tuning of the segmentation
        :return:
        """
        if val != self.lastThreshold:
            self.lastThreshold = val
            self.logic.tracheaLabelmapThreshold(val / 100.0)

    def __onStentRadiusChange__(self):

        self.logic.updateCylindersRadius(self.currentStentType,
                                         self.radiusLevelSlider1.value / 10.0,
                                         self.radiusLevelSlider2.value / 10.0,
                                         self.radiusLevelSlider3.value / 10.0)
        self.__refreshMeasurementsTables__()

    def __onSceneClosed__(self, arg1, arg2):
        self.__initModuleVars__()
        self.__initMeasurementsTables__()
        self.__refreshUI__()



# CIP_TracheaStentPlanningOptimizedLogic
#
class CIP_TracheaStentPlanningOptimizedLogic(ScriptedLoadableModuleLogic):
    STENT_Y = "Y Stent"
    STENT_T = "T Stent"

    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        self.line = dict()
        self.tube = dict()

        for tag in ['cl1', 'cl2', 'cl3']:
            self.line[tag] = vtk.vtkLineSource()
            self.tube[tag] = vtk.vtkTubeFilter()
            self.tube[tag].SetNumberOfSides(15)
            self.tube[tag].CappingOff()
            self.tube[tag].SidesShareVerticesOff()
            self.tube[tag].SetInputData(self.line[tag].GetOutput())

        # Stent types and associated structures:
        # [Fiducials list, Fiducials Color, 3D Model Color, 3D Model Opacity]
        self.stentTypes = OrderedDict()
        self.stentTypes = {
            self.STENT_Y: (("Upper", "Middle", "Bottom_Left", "Bottom_Right"), (1, 0, 0), (0, 1, 0), 1),
            self.STENT_T: (("Bottom ", "Lower", "Middle", "Outside"), (0, 1, 0), (0, 0, 1), 0.8)
        }
        # self.fiducialList = {
        #     "YStent": ["Upper", "Middle", "Bottom_Left", "Bottom_Right"],
        #     "TStent": ["Bottom ", "Lower", "Middle", "Outside"]
        # }
        self.__initVars__()
        self.markupsLogic = slicer.modules.markups.logic()
        self.modelsLogic = slicer.modules.models.logic()

        # Variables needed by the optimization algorithm
        self.isup2 = 1
        self.isup3 = 0
        self.optim_params=dict()
        self.currentCentroids=dict()

        # initialize Progress Bar
        self.progressBar = qt.QProgressDialog(slicer.util.mainWindow())
        self.progressBar.minimumDuration = 0

        self.thresholdFilter = None


    def __initVars__(self):
        """ Init all the variables that are going to be used to perform all the operations
        :return:
        """
        self.currentVolumeId = None  # Active volume
        self.currentStentType = self.STENT_Y


        # Fiducial nodes
        self.currentFiducialsListNodes = {self.STENT_Y: None, self.STENT_T: None}  # Dictionary of fiducial nodes

        # Results of the segmentation
        self.currentResultsNode = None
        self.currentResultsArray = None
        self.currentLabelmapResults = None
        self.currentLabelmapResultsArray = None
        self.currentDistanceMean = 0  # Current base threshold that will be used to increase/decrease the scope of the segmentation

        # 3D structures (replicated for every structure except in the case of the trachea)
        self.currentTracheaModel = None
        self.currentCylindersVtkFilters = dict()
        self.currentLines = dict()
        self.currentCylindersModel = dict()
        self.cylindersVtkAppendPolyDataFilter = dict()

        # Length and radius measurements. Every entry matches with a stent type.
        # Every stent type will have a 3x2 list with the length and radius measurements
        self.currentMeasurements = dict()
        for key in self.getStentKeys():
            self.currentMeasurements[key] = [(0, 0)] * 3
        # Every stent will have 2 angles
        self.currentAngles = dict()
        for key in self.getStentKeys():
            self.currentAngles[key] = (0, 0)

    def getStentKeys(self):
        return self.stentTypes.keys()

    def getFiducialList(self, stentType):
        return self.stentTypes[stentType][0]

    def getFiducialListColor(self, stentType):
        return self.stentTypes[stentType][1]

    def get3DModelColor(self, stentType):
        return self.stentTypes[stentType][2]

    def get3DModelOpacity(self, stentType):
        return self.stentTypes[stentType][3]

    def getMRML3DModel(self, stentType, polyData=None):
        """ Get a MRMML model associated to this stent type. The model will be created if it doesn't exist yet
        :param stentType: stent type key
        :param polyData: polydata associated to the model
        :return: MRML model added to the scene
        """
        name = stentType + " Model"
        model = slicer.util.getNode(name)
        if model is None:
            # The model has to be created
            if polyData is None:
                raise Exception(
                    "The 3D model for {0} does not exist. A vtkPolyData object is required to create the model".format(
                        stentType))
            model = self.modelsLogic.AddModel(polyData)
            model.SetName(name)

            # Create a DisplayNode and associate it to the model, in order that transformations can work properly
            displayNode = model.GetDisplayNode()
            displayNode.SetColor(self.get3DModelColor(stentType))
            displayNode.SetOpacity(self.get3DModelOpacity(stentType))
            displayNode.SetSliceIntersectionVisibility(True)

        elif polyData is not None:
            # Connect the model with a different polydata
            model.SetAndObservePolyData(polyData)

        return model

    def setActiveVolume(self, volumeId, onNodeModifiedCallback, onMarkupAddedCallback):
        """ Set the current input volume and init the fiducials when needed
        :param volumeId: Volume id
        :param onNodeModifiedCallback: function that will be invoked when a fiducial is modified
        :param onMarkupAddedCallback: function that will be invoked when a new fiducial is added
        """
        self.currentVolumeId = volumeId
        self.__initFiducialsList__(onNodeModifiedCallback, onMarkupAddedCallback)

    def __initFiducialsList__(self, onNodeModifiedCallback, onMarkupAddedCallback):
        """ Init the fiducial list for the current volume (see "setActiveVolume")
        :param onNodeModifiedCallback:
        :param onMarkupAddedCallback:
        """
        if self.currentVolumeId is None:
            raise Exception("There is no volume loaded")

        for stentType in self.stentTypes.keys():
            basename = "TracheaSegmentation_fiducialList_{0}".format(stentType)
            nodes = []
            for fiducialType in self.getFiducialList(stentType):
                name = "{0}_{1}".format(basename, fiducialType)
                fiducialsNode = slicer.util.getNode(name)
                if fiducialsNode is None:
                    fiducialListNodeID = self.markupsLogic.AddNewFiducialNode(name, slicer.mrmlScene)
                    fiducialsNode = slicer.util.getNode(fiducialListNodeID)
                    # Hide any text from all the fiducials
                    fiducialsNode.SetMarkupLabelFormat('')
                    # Set color and shape
                    displayNode = fiducialsNode.GetDisplayNode()
                    displayNode.SetSelectedColor(self.getFiducialListColor(stentType))
                    displayNode.SetGlyphScale(2)

                    if fiducialType == "Middle":
                        fiducialsNode.AddFiducial(0,0,0)
                        displayNode.SetOpacity(0)


                    fiducialsNode.AddObserver("ModifiedEvent", onNodeModifiedCallback)
                    fiducialsNode.AddObserver(fiducialsNode.MarkupAddedEvent, onMarkupAddedCallback)
                # else:
                #     fiducialsNode.RemoveAllMarkups()
                nodes.append(fiducialsNode)
            self.currentFiducialsListNodes[stentType] = nodes

    def setActiveFiducialListNode(self, stentType, fiducialIndex):
        """ Set the active fiducials list node based on the stent type and the index of the stent segment.
        It reset all the previous structures!
        :param stentType:
        :param fiducialIndex: int index
        """
        if self.currentVolumeId is None:
            return
        nodes = self.currentFiducialsListNodes[stentType]
        self.markupsLogic.SetActiveListID(nodes[fiducialIndex])

    def runSegmentationPipeline(self, stentTypeKey):
        """ Run the segmentation algorithm for the selected stent type
        :param stentTypeKey: T Sent or Y Stent
        """
        # Check that we have all the required fiducials for the selected stent type
        # visibleFiducialsIndexes = self.getVisibleFiducialsIndexes(stentTypeKey)
        #
        # if len(visibleFiducialsIndexes) < len(self.getFiducialList(stentTypeKey)):
        #     qt.QMessageBox.warning(slicer.util.mainWindow(), "Missing fiducials",
        #             "Please make sure that you have added all the required points for the selected stent type")
        #     return
        # TODO: allow segmentation with T stent?
        self.progressBar.show()
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(6)
        self.progressBar.labelText = "Initializing optimization, please wait"
        if self.__segmentTracheaFromYStentPoints__():

            self.drawTrachea()
            self.drawYStent()

            SlicerUtil.setFiducialsCursorMode(False)

            # # Align the model with the segmented labelmap applying a transformation
            # transformMatrix = vtk.vtkMatrix4x4()
            # self.currentLabelmapResults.GetIJKToRASMatrix(transformMatrix)
            # self.currentTracheaModel.ApplyTransformMatrix(transformMatrix)

            # Center the 3D view
            layoutManager = slicer.app.layoutManager()
            threeDWidget = layoutManager.threeDWidget(0)
            threeDView = threeDWidget.threeDView()
            threeDView.resetFocalPoint()
        self.__calculateMeasurements__()

    def __segmentTracheaFromYStentPoints__(self):
        """ Run the Y trachea segmentation.
        """
        start = time.time()
        # Get the three fiducials for the Y Stent points that are needed to segment the trachea (top, bottom left and bottom right)
        nodes = self.currentFiducialsListNodes[self.STENT_Y]
        coords = []
        for i in [0, 2, 3]:
            if nodes[i].GetNumberOfFiducials() == 0:
                qt.QMessageBox.warning(slicer.util.mainWindow(), "Missing fiducials",
                                       "Please make sure that you have added all the required points for the selected stent type")
                return False
            f = [0, 0, 0]
            nodes[i].GetNthFiducialPosition(0, f)
            coords.append(f)
        f0 = coords[0]
        f1 = coords[1]
        f2 = coords[2]

        activeNode = slicer.util.getNode(self.currentVolumeId)
        spacing = activeNode.GetSpacing()

        pos0 = Util.ras_to_ijk(activeNode, f0, convert_to_int=True)
        pos1 = Util.ras_to_ijk(activeNode, f1, convert_to_int=True)
        pos2 = Util.ras_to_ijk(activeNode, f2, convert_to_int=True)
        # Get distance (use RAS coordinates to have in mind spacing)
        dd01 = 1.5*(
                   (f0[0] - f1[0]) ** 2
                   + (f0[1] - f1[1]) ** 2
                   + (f0[2] - f1[2]) ** 2
               ) ** (1.0 / 2)
        dd02 = 1.5*(
                   (f0[0] - f2[0]) ** 2
                   + (f0[1] - f2[1]) ** 2
                   + (f0[2] - f2[2]) ** 2
               ) ** (1.0 / 2)
        dd12 = 1.5*(
                   (f2[0] - f1[0]) ** 2
                   + (f2[1] - f1[1]) ** 2
                   + (f2[2] - f1[2]) ** 2
               ) ** (1.0 / 2)

        self.currentDistanceMean = (dd01 + dd02 + dd12) / 3
        if SlicerUtil.IsDevelopment: print("DEBUG: preprocessing:", time.time() - start)
        # Build the speed map for Fast Marching thresholding the original volume
        activeVolumeArray = slicer.util.array(activeNode.GetID())
        speedTest = (activeVolumeArray < -800).astype(np.int32)

        # Create all the auxiliary nodes for results
        t1 = time.time()
        # lm01 = SlicerUtil.cloneVolume(activeNode, activeNode.GetName() + "_lm01")
        # a01 = slicer.util.array(lm01.GetID())
        # lm02 = SlicerUtil.cloneVolume(activeNode, activeNode.GetName() + "_lm02")
        # a02 = slicer.util.array(lm02.GetID())
        # lm12 = SlicerUtil.cloneVolume(activeNode, activeNode.GetName() + "_lm12")
        # a12 = slicer.util.array(lm12.GetID())
        dim = activeNode.GetImageData().GetDimensions()
        shape = [dim[2], dim[1], dim[0]]
        a01 = np.zeros(shape, np.int32)
        a02 = np.zeros(shape, np.int32)
        a12 = np.zeros(shape, np.int32)
        # Results of the algorithm
        self.currentResultsNode = SlicerUtil.cloneVolume(activeNode, activeNode.GetName() + "_result", addToScene=True)
        self.currentResultsArray = slicer.util.array(self.currentResultsNode.GetID())
        self.currentLabelmapResults = SlicerUtil.getLabelmapFromScalar(self.currentResultsNode,
                                                                       activeNode.GetName() + "_results_lm")
        if SlicerUtil.IsDevelopment: print("DEBUG: create aux nodes:", time.time() - t1)
        # Create SimpleITK FastMarching filter with the thresholded original image as a speed map
        sitkImage = sitk.GetImageFromArray(speedTest)
        fastMarchingFilter = sitk.FastMarchingImageFilter()
        sitkImage.SetSpacing(spacing)

        # Run the fast marching filters from the 3 points.
        # Every result array will contain the "distance inverted" value (distance - value) because we will add all the arrays
        # Filter 01
        t1 = time.time()
        d = dd01
        fastMarchingFilter.SetStoppingValue(d)
        seeds = [pos0]
        fastMarchingFilter.SetTrialPoints(seeds)
        output = fastMarchingFilter.Execute(sitkImage)
        outputArray = sitk.GetArrayFromImage(output)
        # a01[:] = 0
        temp = outputArray <= d
        a01[temp] = d - outputArray[temp]
        # lm01.GetImageData().Modified()
        if SlicerUtil.IsDevelopment: print("DEBUG: filter 01:", time.time() - t1)

        # Filter 02
        t1 = time.time()
        d = dd02
        fastMarchingFilter.SetStoppingValue(d)
        seeds = [pos2]
        fastMarchingFilter.SetTrialPoints(seeds)
        output = fastMarchingFilter.Execute(sitkImage)
        outputArray = sitk.GetArrayFromImage(output)
        # a02[:] = 0
        temp = outputArray <= d
        a02[temp] = d - outputArray[temp]
        # lm02.GetImageData().Modified()
        if SlicerUtil.IsDevelopment: print("DEBUG: filter 02:", time.time() - t1)

        # Filter 12
        t1 = time.time()
        d = dd12
        fastMarchingFilter.SetStoppingValue(d)
        seeds = [pos1]
        fastMarchingFilter.SetTrialPoints(seeds)
        output = fastMarchingFilter.Execute(sitkImage)
        outputArray = sitk.GetArrayFromImage(output)
        # a12[:] = 0
        temp = outputArray <= d
        a12[temp] = d - outputArray[temp]
        # lm12.GetImageData().Modified()
        if SlicerUtil.IsDevelopment: print("DEBUG: filter 12:", time.time() - t1)

        t1 = time.time()
        # Sum the results of the 3 filters
        self.currentResultsArray[:] = a01 + a02 + a12
        self.currentResultsNode.GetImageData().Modified()
        if SlicerUtil.IsDevelopment: print("DEBUG: processing results:", time.time() - t1)

        # Threshold to get the final labelmap
        t1 = time.time()
        self.thresholdFilter = vtk.vtkImageThreshold()
        self.thresholdFilter.SetInputData(self.currentResultsNode.GetImageData())
        self.thresholdFilter.SetReplaceOut(True)
        self.thresholdFilter.SetOutValue(0)  # Value of the background
        self.thresholdFilter.SetInValue(1)  # Value of the segmented nodule
        self.thresholdFilter.ThresholdByUpper(self.currentDistanceMean)
        self.thresholdFilter.SetOutput(self.currentLabelmapResults.GetImageData())
        self.thresholdFilter.Update()
        if SlicerUtil.IsDevelopment: print("DEBUG: thresholding:", time.time() - t1)

        # Show the result in slicer
        appLogic = slicer.app.applicationLogic()
        selectionNode = appLogic.GetSelectionNode()
        selectionNode.SetActiveLabelVolumeID(self.currentLabelmapResults.GetID())
        appLogic.PropagateLabelVolumeSelection()

        if SlicerUtil.IsDevelopment: print("DEBUG: total time: ", time.time() - start)
        return True

    def tracheaLabelmapThreshold(self, thresholdFactor):
        """ Update the threshold used to generate the segmentation (when the thresholdFactor is bigger, "more trachea"
        will be displayed
        :param thresholdFactor: value between 0.01 and 2
        """
        if self.thresholdFilter:
            threshold = self.currentDistanceMean / thresholdFactor
            self.thresholdFilter.ThresholdByUpper(threshold)
            self.thresholdFilter.Update()
            self.currentTracheaModel.GetDisplayNode().Modified()
            SlicerUtil.refreshActiveWindows()

    def drawTrachea(self):
        """ Draw the trachea 3D model
        :return:
        """
        modelsLogic = slicer.modules.models.logic()
        marchingCubesFilter = vtk.vtkMarchingCubes()
        marchingCubesFilter.SetInputData(self.currentLabelmapResults.GetImageData())
        marchingCubesFilter.SetValue(0, 1)
        self.currentTracheaModel = modelsLogic.AddModel(marchingCubesFilter.GetOutputPort())
        self.currentTracheaModel.SetName("Trachea Model")
        displayNode = self.currentTracheaModel.GetDisplayNode()
        displayNode.SetOpacity(0.5)
        displayNode.SetColor((1, 0, 0))
        marchingCubesFilter.Update()
        self.updateProgressBar(1)

    def drawYStent(self):
        """ Create a labelmap with the Y stent based on the user points
        :param
        :return:
        """
        self.cylindersVtkAppendPolyDataFilter[self.STENT_Y] = vtk.vtkAppendPolyData()
        defaultRadius = 5

        # Get the position of the points (RAS)
        top = [0, 0, 0]
        middle = [0, 0, 0]
        left = [0, 0, 0]
        right = [0, 0, 0]
        fiducialNodes = self.currentFiducialsListNodes[self.STENT_Y]
        fiducialNodes[0].GetNthFiducialPosition(0, top)
        fiducialNodes[1].GetNthFiducialPosition(0, middle)
        fiducialNodes[2].GetNthFiducialPosition(0, left)
        fiducialNodes[3].GetNthFiducialPosition(0, right)



        # Cylinder 0 (vertical)
        line_top_middle = vtk.vtkLineSource()
        line_top_middle.SetPoint1(top)
        line_top_middle.SetPoint2(middle)
        cylinder_top_middle = vtk.vtkTubeFilter()
        cylinder_top_middle.SetNumberOfSides(30)
        cylinder_top_middle.SetRadius(defaultRadius)
        cylinder_top_middle.CappingOff()
        cylinder_top_middle.SidesShareVerticesOff()
        cylinder_top_middle.SetInputConnection(line_top_middle.GetOutputPort())
        self.cylindersVtkAppendPolyDataFilter[self.STENT_Y].AddInputConnection(cylinder_top_middle.GetOutputPort())

        # Cylinder 1 (left)
        line_middle_left = vtk.vtkLineSource()
        line_middle_left.SetPoint1(middle)
        line_middle_left.SetPoint2(left)
        cylinder_middle_left = vtk.vtkTubeFilter()
        cylinder_middle_left.SetNumberOfSides(30)
        cylinder_middle_left.SetRadius(defaultRadius)
        cylinder_middle_left.CappingOff()
        cylinder_middle_left.SidesShareVerticesOff()
        cylinder_middle_left.SetInputConnection(line_middle_left.GetOutputPort())
        self.cylindersVtkAppendPolyDataFilter[self.STENT_Y].AddInputConnection(cylinder_middle_left.GetOutputPort())

        # Cylinder 2 (right)
        line_middle_right = vtk.vtkLineSource()
        line_middle_right.SetPoint1(middle)
        line_middle_right.SetPoint2(right)
        cylinder_middle_right = vtk.vtkTubeFilter()
        cylinder_middle_right.SetNumberOfSides(30)
        cylinder_middle_right.SetRadius(defaultRadius)
        cylinder_middle_right.CappingOff()
        cylinder_middle_right.SidesShareVerticesOff()
        cylinder_middle_right.SetInputConnection(line_middle_right.GetOutputPort())
        self.cylindersVtkAppendPolyDataFilter[self.STENT_Y].AddInputConnection(cylinder_middle_right.GetOutputPort())

        # model = slicer.util.getNode("Y stent Model")
        # self.currentCylindersModel[self.STENT_Y] = self.modelsLogic.AddModel(self.cylindersVtkAppendPolyDataFilter.GetOutputPort())
        self.currentCylindersModel[self.STENT_Y] = self.getMRML3DModel(self.STENT_Y,
                                                                       self.cylindersVtkAppendPolyDataFilter[
                                                                           self.STENT_Y].GetOutputPort())
        self.cylindersVtkAppendPolyDataFilter[self.STENT_Y].Update()

        self.currentLines[self.STENT_Y] = [line_top_middle, line_middle_left, line_middle_right]
        self.currentCylindersVtkFilters[self.STENT_Y] = [cylinder_top_middle, cylinder_middle_left, cylinder_middle_right]

        # Align the model with the segmented labelmap applying a transformation
        transformMatrix = vtk.vtkMatrix4x4()
        self.currentLabelmapResults.GetIJKToRASMatrix(transformMatrix)
        self.currentTracheaModel.ApplyTransformMatrix(transformMatrix)

        layoutManager = slicer.app.layoutManager()
        threeDWidget = layoutManager.threeDWidget(0)
        threeDView = threeDWidget.threeDView()
        threeDView.resetFocalPoint()
        # Automatic optimization
        self.optim_params = self.automaticOptimizationYStent(top, left, right)
        self.updateCylindersFromOptimizationParameters(self.STENT_Y,self.optim_params[0],self.optim_params[1])



    def automaticOptimizationYStent(self,p1, p2,p3):
        """
        Calculate optimal points and radius for the Y Stent
        :param p1: seed top
        :param p2: seed bottom left (x,y,z)
        :param p3: seed bottom right (x,y,z)
        :return: 2-Tuple:
            Vector with 5 points (each position will contain x,y,z coordinates)
            Vector with 3 radius (top, left and right cylinders)
        """
        print ("DEBUG: automaticOptimizationYStent")
        trachea = self.buildTracheaButterflySubdivisionFilter(self.currentTracheaModel)
        # First call. Start in user seed



        points = [p1, p2, p3]
        # 3 values for each list (corresponding to the 3 cylinders)
        centroids = []
        norms = []
        rads = []
        i=1
        for point in points:
            i=i+1
            norm = [1, 0, 1]
            cons = ({'type': 'eq', 'fun': lambda n: np.array(np.sqrt(sum((n[0:3]) ** 2)) - 1),
                     'jac': lambda n: np.array(n[0:3] / np.sqrt(sum((n[0:3]) ** 2)))})
            print ("DEBUG: automaticOptimizationYStent. Calling optimize with: ", point)
            normal_vector = scipy_opt.minimize(self.cylinderSurfaceArea, norm, args=(point, trachea), constraints=cons,
                                               method='SLSQP',
                                               options={'disp': True})
            inter = self.intersection(trachea, self.plane(normal_vector.x, point), point)
            print ("DEBUG: automaticOptimizationYStent. Intersection: ", inter)
            centr = self.centroide(self.polygon(inter))
            print ("DEBUG: automaticOptimizationYStent. Centroid: ", centr)
            rad = self.radius(centr, inter)
            #rad = self.radius2(self.cylinderSurfaceArea(normal_vector.x, centr, trachea))
            print ("DEBUG: automaticOptimizationYStent. Radius: ", rad)
            norm = (normal_vector.x)
            centroids.append(centr)
            norms.append(norm)
            rads.append(rad)
            self.updateProgressBar(i)

        # Second call. Calculate a plane close to the first one

        p12 = p1[0] - 15 * norms[0][0], p1[1] - 15 * norms[0][1], p1[2] - 15 * norms[0][2]
        p22 = p2[0] + 8 * norms[1][0], p2[1] + 8 * norms[1][1], p2[2] + 8 * norms[1][2]
        p32 = p3[0] + 8 * norms[2][0], p3[1] + 8 * norms[2][1], p3[2] + 8 * norms[2][2]

        points2 = [p12, p22, p32]
        for point in points2:
            i=i+1
            norm = [1, 0, 1]
            cons = ({'type': 'eq', 'fun': lambda n: np.array(np.sqrt(sum((n[0:3]) ** 2)) - 1),
                     'jac': lambda n: np.array(n[0:3] / np.sqrt(sum((n[0:3]) ** 2)))})
            print ("DEBUG: automaticOptimizationYStent. Calling optimize with: ", point)
            normal_vector = scipy_opt.minimize(self.cylinderSurfaceArea, norm, args=(point, trachea), constraints=cons,
                                               method='SLSQP',
                                               options={'disp': True})
            inter = self.intersection(trachea, self.plane(normal_vector.x, point), point)
            print ("DEBUG: automaticOptimizationYStent. Intersection: ", inter)
            centr = self.centroide(self.polygon(inter))
            print ("DEBUG: automaticOptimizationYStent. Centroid: ", centr)
            rad = self.radius(centr, inter)
            #rad = self.radius2(self.cylinderSurfaceArea(normal_vector.x,centr, trachea))
            print ("DEBUG: automaticOptimizationYStent. Radius: ", rad)
            norm = (normal_vector.x)
            centroids.append(centr)
            norms.append(norm)
            rads.append(rad)
            self.updateProgressBar(i)

        mediumPoints = self.dist_ort(centroids)
        print "DEBUG: radios"
        print rads
        mediumrads=np.zeros(3)
        mediumrads[0]=(rads[0]+rads[3])/2
        mediumrads[1] = (rads[1] + rads[4]) / 2
        mediumrads[2] = (rads[2] + rads[5]) / 2
        print "DEBUG: medium rads"
        print mediumrads

        parameters = self.init_values(mediumPoints, mediumrads)
        c1 = centroids[0]
        c2 = centroids[1]
        c3 = centroids[2]
        arguments = c1, c2, c3, trachea
        self.currentCentroids=c1,c2,c3
        self.progressBar.close()
        #self.progressBar = None
        cons2 = ({'type': 'eq',
                  'fun': lambda parameters: np.array(
                      (c2[0] - c1[0]) * (parameters[2] - c1[1]) * (parameters[7] - c2[2]) + (c2[1] - c1[1]) * (
                      parameters[3] - c1[2]) * (parameters[5] - c2[0]) + (c2[2] - c1[2]) * (parameters[1] - c1[0]) * (
                      parameters[6] - c2[1]) - (c2[2] - c1[2]) * (parameters[2] - c1[1]) * (parameters[5] - c2[0]) - (
                      c2[1] - c1[1]) * (parameters[1] - c1[0]) * (parameters[7] - c2[2]) - (c2[0] - c1[0]) * (
                      parameters[3] - c1[2]) * (parameters[6] - c2[1])),
                  'jac': lambda parameters: np.array(
                      [0, (c2[2] - c1[2]) * (parameters[6] - c2[1]) - (c2[1] - c1[1]) * (parameters[7] - c2[2]),
                       (c2[0] - c1[0]) * (parameters[7] - c2[2]) - (c2[2] - c1[2]) * (parameters[5] - c2[0]),
                       (c2[1] - c1[1]) * (parameters[5] - c2[0]) - (c2[0] - c1[0]) * (parameters[6] - c2[1]), 0,
                       (c2[1] - c1[1]) * (parameters[3] - c1[2]) - (c2[2] - c1[2]) * (parameters[2] - c1[1]),
                       (c2[2] - c1[2]) * (parameters[1] - c1[0]) - (c2[0] - c1[0]) * (parameters[3] - c1[2]),
                       (c2[0] - c1[0]) * (parameters[2] - c1[1]) - (c2[1] - c1[1]) * (parameters[1] - c1[0]), 0, 0, 0,
                       0])},
                 {'type': 'eq',
                  'fun': lambda parameters: np.array(
                      (c3[0] - c1[0]) * (parameters[2] - c1[1]) * (parameters[11] - c3[2]) + (c3[1] - c1[1]) * (
                      parameters[3] - c1[2]) * (
                          parameters[9] - c3[0]) + (c3[2] - c1[2]) * (parameters[1] - c1[0]) * (
                      parameters[10] - c3[1]) - (c3[2] - c1[2]) * (
                          parameters[2] - c1[1]) * (parameters[9] - c3[0]) - (c3[1] - c1[1]) * (
                      parameters[1] - c1[0]) * (parameters[11] - c3[2]) - (
                          c3[0] - c1[0]) * (parameters[3] - c1[2]) * (parameters[10] - c3[1])),
                  'jac': lambda parameters: np.array(
                      [0, (c3[2] - c1[2]) * (parameters[10] - c3[1]) - (c3[1] - c1[1]) * (parameters[11] - c3[2]),
                       (c3[0] - c1[0]) * (parameters[11] - c3[2]) - (c3[2] - c1[2]) * (parameters[9] - c3[0]),
                       (c3[1] - c1[1]) * (parameters[9] - c3[0]) - (c3[0] - c1[0]) * (parameters[10] - c3[1]), 0, 0, 0,
                       0, 0,
                       (c3[1] - c1[1]) * (parameters[3] - c1[2]) - (c3[2] - c1[2]) * (parameters[2] - c1[1]),
                       (c3[2] - c1[2]) * (parameters[1] - c1[0]) - (c3[0] - c1[0]) * (parameters[3] - c1[2]),
                       (c3[0] - c1[0]) * (parameters[2] - c1[1]) - (c3[1] - c1[1]) * (parameters[1] - c1[0])])},
                 {'type': 'ineq',
                  'fun': lambda parameters: np.array([parameters[0]]),
                  'jac': lambda parameters: np.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])},
                 {'type': 'ineq',
                  'fun': lambda parameters: np.array([parameters[4]]),
                  'jac': lambda parameters: np.array([0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0])},
                 {'type': 'ineq',
                  'fun': lambda parameters: np.array([parameters[8]]),
                  'jac': lambda parameters: np.array([0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0])},
                 {'type': 'eq',
                  'fun': lambda parameters: np.array(
                      [parameters[1]] - self.isup2 * parameters[5] - self.isup3 * parameters[9]),
                  'jac': lambda parameters: np.array([0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0])},
                 {'type': 'eq',
                  'fun': lambda parameters: np.array(
                      [parameters[2]] - self.isup2 * parameters[6] - self.isup3 * parameters[10]),
                  'jac': lambda parameters: np.array([0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0])},
                 {'type': 'eq',
                  'fun': lambda parameters: np.array(
                      [parameters[3]] - self.isup2 * parameters[7] - self.isup3 * parameters[11]),
                  'jac': lambda parameters: np.array([0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0])}
                 )

        res2 = scipy_opt.minimize(self.minimum, parameters, args=(arguments), constraints=cons2, method='SLSQP',
                                  options={'disp': True, 'ftol': 0.01, 'maxiter': 150}, callback=self.myfunc)


        pm1=[res2.x[1], res2.x[2], res2.x[3]]
        pm2=[res2.x[5], res2.x[6], res2.x[7]]
        pm3=[res2.x[9], res2.x[10],res2.x[11]]
        pointsVector=[c1,pm1,c2,pm2,c3,pm3]
        radiusVector=[res2.x[0], res2.x[4], res2.x[8]]
        self.updateCylindersRadius(self.STENT_Y, radiusVector[0],radiusVector[1],radiusVector[2])
        qt.QMessageBox.information(slicer.util.mainWindow(), "The optimization is completed", "The optimization is completed, You can now change the stent position and radius.")
        return pointsVector, radiusVector

    def myfunc(self, params):
        """
        Updates Cylinder values during the optimization process
        Args:
            params: Cylinder parameters (points and radius)

        Returns:

        """
        pm1 = [params[1], params[2], params[3]]
        pm2 = [params[5], params[6], params[7]]
        pm3 = [params[9], params[10], params[11]]
        radiusVector = [params[0], params[4], params[8]]
        pointsVector=[self.currentCentroids[0], pm1, self.currentCentroids[1],pm2, self.currentCentroids[2], pm3]
        self.updateCylindersFromOptimizationParameters(self.STENT_Y, pointsVector, radiusVector)
        slicer.app.processEvents()
        SlicerUtil.refreshActiveWindows()

    def cylinderSurfaceArea(self, norm_vector, point, tracheaFilter):
        """
        Calculate area of a cylinder based on a normal vector, a point and a butterfly subdivision filter
        based on the current trachea model
        :param norm_vector:
        :param point:
        :param tracheaFilter:
        :return: area
        """
        plane = self.plane(norm_vector, point)
        intersection = self.intersection(tracheaFilter, plane, point)
        result = vtk.vtkPolyData()
        result.SetPoints(intersection.GetOutput().GetPoints())
        result.SetLines(intersection.GetOutput().GetCells())
        return self.area(result, norm_vector)


    def buildTracheaButterflySubdivisionFilter(self, tracheaModel):
        """
        adds more points to the trachea segmentation
        :param tracheaModel: traquea segmentation model
        :return: filter
        """
        triangles = vtk.vtkTriangleFilter()
        triangles.SetInputConnection(tracheaModel.GetPolyDataConnection())
        triangles.Update()
        tr2 = vtk.vtkLinearSubdivisionFilter()
        tr2.SetInputConnection(triangles.GetOutputPort())
        tr2.Update()
        return tr2

    def plane(self, N, p):
        """
        calculates the plane with N normal vector and point P
        :param N: Normal vector
        :param p: Point
        :return: Plane
        """
        pp = vtk.vtkPlane()
        pp.SetOrigin(p)
        denominator = np.sqrt(sum((N[:]) ** 2))
        v = np.zeros(3)
        v[:] = (N[:] / denominator)
        pp.SetNormal(v[0], v[1], v[2])
        return pp

    def intersection(self, tr, pp, p):
        """
        calculates the intersection between a plane and the trachea
        :param tr: trachea
        :param pp: plane
        :param p: point
        :return: intersection
        """

        ii = vtk.vtkCutter()
        ii.SetCutFunction(pp)
        ii.SetInputConnection(tr.GetOutputPort())

        ii.Update()
        n=ii.GetOutput().GetNumberOfPoints()

        cc = vtk.vtkConnectivityFilter()
        cc.SetInputConnection(ii.GetOutputPort())
        cc.SetExtractionModeToClosestPointRegion()
        cc.SetClosestPoint(p)
        cc.Update()
        return cc

    def area(self, poly, n):
        """
        calculates the area of a polygon
        :param poly: polygon
        :param n: normal vector of the polygon
        :return: area
        """
        aa = poly.GetLines()
        aa.InitTraversal()
        total = np.zeros(3, )
        if poly.GetNumberOfPoints() == 0:
            return 1000
        for i in range(aa.GetNumberOfCells()):
            p_idx = vtk.vtkIdList()
            aa.GetNextCell(p_idx)
            p1_idx = p_idx.GetId(0)
            p2_idx = p_idx.GetId(1)
            p1 = np.array(poly.GetPoints().GetPoint(p1_idx))
            p2 = np.array(poly.GetPoints().GetPoint(p2_idx))
            total = total + np.cross(p1, p2)
        result = np.dot(total, n / np.linalg.norm(n))
        Result = abs(result / 2)
        return Result

    def centroide(self, intersection):
        """
        calculates the centroid of the intersection
        :param intersection
        :return: centroid
        """
        centroid = (sum(intersection[:]) / len(intersection))
        return centroid

    def radius(self, centroid, curve):
        """
        calculates the radius of the biggest circle inside a curve
        :param centroid:
        :param curve:
        :return: radius
        """
        loc = vtk.vtkPointLocator()
        loc.SetDataSet(curve.GetOutput())
        loc.BuildLocator()
        Idclosest = loc.FindClosestPoint(centroid)
        closest = np.array(curve.GetOutput().GetPoints().GetPoint(Idclosest))
        radius = np.sqrt(np.sum((closest[0:3] - centroid[0:3]) ** 2))
        return radius
    def radius2(self, area):
        """
        Not used. Calculates the equivalent radius of a determined area.
        Args:
            area: Area value

        Returns:

        """
        return np.sqrt(area/np.pi)

    def polygon(self, intersection):
        """
        creates a polygon with the data of an intersection
        :param intersection:
        :return: polygon
        """

        polygon = np.zeros([intersection.GetOutput().GetNumberOfPoints(), 3])
        for i in xrange(intersection.GetOutput().GetNumberOfPoints()):
            polygon[i] = intersection.GetOutput().GetPoints().GetPoint(i)
        return polygon


    def dist_ort(self, centroids):
        """
        calculates the medium points of the 3 cylinders
        :param centroids
        :return: medium points
        """
        zi = centroids[0][2]
        zf1 = centroids[1][2]
        zf2 = centroids[2][2]
        if zf1 < zf2:
            zf = zf1
        else:
            zf = zf2
        values_range = np.linspace(zi, zf, 200)

        pm2 = [0, 0, 0]
        pm3 = [0, 0, 0]

        x1 = (
        (((centroids[3][0] - centroids[0][0]) * (values_range - centroids[0][2])) / (centroids[3][2] - centroids[0][2])) +
        centroids[0][0])
        y1 = (
        (((centroids[3][1] - centroids[0][1]) * (values_range - centroids[0][2])) / (centroids[3][2] - centroids[0][2])) +
        centroids[0][1])

        x2 = (
        (((centroids[4][0] - centroids[1][0]) * (values_range - centroids[1][2])) / (centroids[4][2] - centroids[1][2])) +
        centroids[1][0])
        y2 = (
        (((centroids[4][1] - centroids[1][1]) * (values_range - centroids[1][2])) / (centroids[4][2] - centroids[1][2])) +
        centroids[1][1])

        x3 = (
        (((centroids[5][0] - centroids[2][0]) * (values_range - centroids[2][2])) / (centroids[5][2] - centroids[2][2])) +
        centroids[2][0])
        y3 = (
        (((centroids[5][1] - centroids[2][1]) * (values_range - centroids[2][2])) / (centroids[5][2] - centroids[2][2])) +
        centroids[2][1])

        xa = x2 - x1
        ya = y2 - y1
        xb = x3 - x1
        yb = y3 - y1

        dist1 = np.sqrt(xa ** 2 + ya ** 2)
        index = 0
        for i in range(len(dist1)-1):
            if dist1[i] < dist1[i + 1]:
                break
            index = index + 1
        pm2[0] = ((((centroids[3][0] - centroids[0][0]) * (values_range[index] - centroids[0][2])) / (
        centroids[3][2] - centroids[0][2])) + centroids[0][0])
        pm2[1] = ((((centroids[3][1] - centroids[0][1]) * (values_range[index] - centroids[0][2])) / (
        centroids[3][2] - centroids[0][2])) + centroids[0][1])
        pm2[2] = values_range[index]

        dist2 = np.sqrt(xb ** 2 + yb ** 2)
        index = 0
        for i in range(len(dist2) - 1):
            if dist2[i] < dist2[i + 1]:
                break
            index = index + 1
        pm3[0] = ((((centroids[3][0] - centroids[0][0]) * (values_range[index] - centroids[0][2])) / (
        centroids[3][2] - centroids[0][2])) + centroids[0][0])
        pm3[1] = ((((centroids[3][1] - centroids[0][1]) * (values_range[index] - centroids[0][2])) / (
        centroids[3][2] - centroids[0][2])) + centroids[0][1])
        pm3[2] = values_range[index]

        d2 = np.sqrt(np.sum(((centroids[0][0:2] - pm2[0:2]) ** 2)))
        d3 = np.sqrt(np.sum(((centroids[0][0:2] - pm3[0:2]) ** 2)))
        if d2 < d3:
            pm1 = pm2
        else:
            pm1 = pm3

        return pm1, pm2, pm3

    def cylinder(self, Pi, Pf, Radius, Lambda, Fi):
        """
        Calculates cilinder surface points given initial an final axis points and radius
        Args:
            Pi: Initial axis point
            Pf: Final axis point
            Radius: Cilinder radius
            Lambda: Ecuation parameter. distance
            Fi: Ecuation parameter. Angle

        Returns:

        """
        Alpha1 = np.arctan2((np.sqrt(np.sum(((Pf[0:2] - Pi[0:2]) ** 2)))), (Pf[2] - Pi[2]))
        Alpha2 = np.arctan2((Pf[0] - Pi[0]), (Pf[1] - Pi[1]))
        X = np.zeros([len(Lambda), 3])
        X[:, 0] = np.cos(Alpha2) * Radius * np.cos(Fi) + Radius * np.sin(Fi) * np.cos(Alpha1) * np.sin(
            Alpha2) + Lambda * np.sin(Alpha1) * np.sin(Alpha2) + Pi[0]
        X[:, 1] = (-1) * Radius * np.cos(Fi) * np.sin(Alpha2) + Radius * np.sin(Fi) * np.cos(Alpha1) * np.cos(
            Alpha2) + Lambda * np.sin(Alpha1) * np.cos(Alpha2) + Pi[1]
        X[:, 2] = -Radius * np.sin(Fi) * np.sin(Alpha1) + Lambda * np.cos(Alpha1) + Pi[2]
        return X

    def init_values(self, mediumPoints, rads):
        """
        returns an array with initial values for the optimization
        :param mediumPoints:
        :param rads: radius
        :return: initial values array
        """
        variables = np.zeros([12])
        variables[0] = rads[0]
        variables[1] = mediumPoints[0][0]
        variables[2] = mediumPoints[0][1]
        variables[3] = mediumPoints[0][2]
        variables[4] = rads[1]
        variables[5] = mediumPoints[1][0]
        variables[6] = mediumPoints[1][1]
        variables[7] = mediumPoints[1][2]
        variables[8] = rads[2]
        variables[9] = mediumPoints[2][0]
        variables[10] = mediumPoints[2][1]
        variables[11] = mediumPoints[2][2]
        return variables

    def homologous(self, traq, p_cil):
        """
        calculates the points of the trachea that correspond to the given points of the cylinder
        :param traq: trachuea
        :param p_cil: cylinder points
        :return: trachea points
        """
        loc = vtk.vtkPointLocator()
        loc.SetDataSet(traq.GetOutput())
        loc.BuildLocator()
        vector = vtk.vtkPoints()
        for i in range(len(p_cil)):
            d = loc.FindClosestPoint(p_cil[i])
            res = traq.GetOutput().GetPoints().GetPoint(d)
            vector.InsertNextPoint(res)
        return vector

    def functional(self, cil1, cil2, cil3, hom1, hom2, hom3):
        """
        calculates the sum of the distances between cylinder points and trachea equivalent points
        :param cil1:trachea cilynder points
        :param cil2: left bronchi cylinder point
        :param cil3: right bronchi cylinder point
        :param hom1: trachea points
        :param hom2: left bronchi points
        :param hom3: right bronchi points
        :return: distances
        """
        suma = 0
        for i in range(len(cil1)):
            punto = hom1.GetPoint(i)
            cilind = cil1[i]
            suma = suma + (np.sqrt(np.sum((punto[0:2] - cilind[0:2]) ** 2)))
        for i in range(len(cil2)):
            punto = hom2.GetPoint(i)
            cilind = cil2[i]
            suma = suma + (np.sqrt(np.sum((punto[0:2] - cilind[0:2]) ** 2)))
        for i in range(len(cil3)):
            punto = hom3.GetPoint(i)
            cilind = cil3[i]
            suma = suma + (np.sqrt(np.sum((punto[0:2] - cilind[0:2]) ** 2)))
        return suma

    def minimum(self, parameters, centroid1, centroid2, centroid3, traq):
        """
        calculates the medium square error of the distances between cylinder and trachea
        :param parameters: initial parameters (points and radius)
        :param centroids: centroids
        :return: error
        """
        pm2 = [0, 0, 0]
        pm3 = [0, 0, 0]
        rad1 = parameters[0]
        rad2 = parameters[4]
        pm2[0] = parameters[5]
        pm2[1] = parameters[6]
        pm2[2] = parameters[7]
        rad3 = parameters[8]
        pm3[0] = parameters[9]
        pm3[1] = parameters[10]
        pm3[2] = parameters[11]
        d2 = np.sqrt(np.sum(((centroid1[0:2] - pm2[0:2]) ** 2)))
        d3 = np.sqrt(np.sum(((centroid1[0:2] - pm3[0:2]) ** 2)))
        if d2 < d3:
            pm1 = pm2
            self.isup2 = 1
            self.isup3 = 0
        else:
            pm1 = pm3
            self.isup2 = 0
            self.isup3 = 1
        longitud1 = np.sqrt(np.sum((pm1[0:3] - centroid1[0:3]) ** 2))
        ll1 = np.linspace(0, longitud1, 50)
        ff = np.linspace(0, 200 * np.pi, 50)
        longitud2 = np.sqrt(np.sum((pm2[0:3] - centroid2[0:3]) ** 2))
        ll2 = np.linspace(0, longitud2, 50)
        longitud3 = np.sqrt(np.sum((pm3[0:3] - centroid3[0:3]) ** 2))
        ll3 = np.linspace(0, longitud3, 50)
        points_cil1 = self.cylinder(centroid1, pm1, rad1, ll1, ff)
        points_cil2 = self.cylinder(centroid2, pm2, rad2, ll2, ff)
        points_cil3 = self.cylinder(centroid3, pm3, rad3, ll3, ff)
        hom1 = self.homologous(traq, points_cil1)
        hom2 = self.homologous(traq, points_cil2)
        hom3 = self.homologous(traq, points_cil3)
        error = self.functional(points_cil1, points_cil2, points_cil3, hom1, hom2, hom3)
        return error

    def updateCylindersRadius(self, stentKey, newRadius1, newRadius2, newRadius3):
        """ Update the radius of the cylinders of stent "stentType"
        :param stentKey: type of stent (Y or T)
        :param newRadius1: radius of the first cylinder
        :param newRadius2: radius of the second cylinder
        :param newRadius3: radius of the third cylinder
        """
        self.currentCylindersVtkFilters[stentKey][0].SetRadius(newRadius1)
        self.currentCylindersVtkFilters[stentKey][1].SetRadius(newRadius2)
        self.currentCylindersVtkFilters[stentKey][2].SetRadius(newRadius3)
        self.cylindersVtkAppendPolyDataFilter[stentKey].Update()


        self.getMRML3DModel(stentKey).GetDisplayNode().Modified()
        self.__calculateMeasurements__()

    def updateCylindersPositionFromFiducials(self, stentType):
        """ Refresh the 3D cylinders model
        :param stentType:
        """
        # Get the position of the fiducials (RAS)
        p0 = [0, 0, 0]
        p1 = [0, 0, 0]
        p2 = [0, 0, 0]
        p3 = [0, 0, 0]

        fiducialNodes = self.currentFiducialsListNodes[stentType]
        fiducialNodes[0].GetNthFiducialPosition(0, p0)
        fiducialNodes[1].GetNthFiducialPosition(0, p1)
        fiducialNodes[2].GetNthFiducialPosition(0, p2)
        fiducialNodes[3].GetNthFiducialPosition(0, p3)


        # Cylinder 0 (vertical, top)
        line_top_middle = self.currentLines[stentType][0]
        line_top_middle.SetPoint1(p0)
        line_top_middle.SetPoint2(p1)

        # Cylinder 1 (left, exterior)
        line_middle_left = self.currentLines[stentType][1]
        line_middle_left.SetPoint1(p1)
        line_middle_left.SetPoint2(p2)
        # line_middle_left.Update()

        # Cylinder 2 (right, bottom)
        line_middle_right = self.currentLines[stentType][2]
        line_middle_right.SetPoint1(p1)
        line_middle_right.SetPoint2(p3)
        # line_middle_right.Update()

        self.cylindersVtkAppendPolyDataFilter[stentType].Update()
        self.__calculateMeasurements__()

    def updateCylindersFromOptimizationParameters(self, stentType, pointsVector, radiusVector):
        """ Refresh the 3D cylinders model
        :param stentType:
        """
        # Get the position of the fiducials (RAS)

        # Cylinder 0 (vertical, top)
        line_top_middle = self.currentLines[stentType][0]
        line_top_middle.SetPoint1(pointsVector[0])
        line_top_middle.SetPoint2(pointsVector[1])

        # Cylinder 1 (left, exterior)
        line_middle_left = self.currentLines[stentType][1]
        line_middle_left.SetPoint1(pointsVector[2])
        line_middle_left.SetPoint2(pointsVector[3])
        # line_middle_left.Update()

        # Cylinder 2 (right, bottom)
        line_middle_right = self.currentLines[stentType][2]
        line_middle_right.SetPoint1(pointsVector[4])
        line_middle_right.SetPoint2(pointsVector[5])
        # line_middle_right.Update()

        self.currentCylindersVtkFilters[stentType][0].SetRadius(radiusVector[0])
        self.currentCylindersVtkFilters[stentType][1].SetRadius(radiusVector[1])
        self.currentCylindersVtkFilters[stentType][2].SetRadius(radiusVector[2])
        self.cylindersVtkAppendPolyDataFilter[stentType].Update()
        middlePoint=np.zeros(3)
        middlePoint[0]=(pointsVector[5][0]+pointsVector[3][0])/2
        middlePoint[1] = (pointsVector[5][1] + pointsVector[3][1])/2
        middlePoint[2] = (pointsVector[5][2] + pointsVector[3][2])/2

        fiducialNodes = self.currentFiducialsListNodes[stentType]


        fiducialNodes[0].SetNthFiducialPosition(0, pointsVector[0][0],pointsVector[0][1],pointsVector[0][2])
        #fiducialNodes[1].SetNthFiducialPosition(0, middlePoint[0], middlePoint[1], middlePoint[2])
        fiducialNodes[1].SetNthFiducialPosition(0, pointsVector[1][0], pointsVector[1][1], pointsVector[1][2])
        fiducialNodes[2].SetNthFiducialPosition(0, pointsVector[2][0],pointsVector[2][1],pointsVector[2][2])
        fiducialNodes[3].SetNthFiducialPosition(0, pointsVector[4][0],pointsVector[4][1],pointsVector[4][2])

        fiducialNodes[1].GetDisplayNode().SetOpacity(1)
        self.updateCylindersPositionFromFiducials(self.STENT_Y)


        # self.currentCylindersModel[stentKey].GetDisplayNode().Modified()
        self.getMRML3DModel(stentType).GetDisplayNode().Modified()
        self.__calculateMeasurements__()

    def __calculateMeasurements__(self):
        """ Calculate the current measures of radius and length of the current stent.
        Also calculate the required angles.
        All the results will be stored in the variables self.currentMeasurements and self.currentMeasurementsAngles"""
        stentType = self.currentStentType
        # One measurement per cylinder
        measurements = [0] * len(self.currentLines[stentType])

        for i in range(len(self.currentLines[stentType])):
            segment = self.currentLines[stentType][i]
            p1 = segment.GetPoint1()
            p2 = segment.GetPoint2()
            # Calculate the distance of the 2 points in 3D (length of the cylinder)
            distance = math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2)
            # Save the distance and the radius of the cylinder
            measurements[i] = (distance, self.currentCylindersVtkFilters[stentType][i].GetRadius())
        self.currentMeasurements[stentType] = measurements

        # Angles
        if stentType == self.STENT_T:
            raise NotImplementedError()
        p_upper = np.array(self.currentLines[stentType][0].GetPoint1())
        p_middle = np.array(self.currentLines[stentType][0].GetPoint2())
        p_left = np.array(self.currentLines[stentType][1].GetPoint2())
        p_right = np.array(self.currentLines[stentType][2].GetPoint2())

        # v1 = (p_upper - p_middle) / np.linalg.norm(p_upper - p_middle)
        # v_left =( p_left - p_middle ) / np.linalg.norm(p_left - p_middle)
        # v_right = (p_right - p_middle) / np.linalg.norm(p_right - p_middle)
        # alpha_left = 180 / np.pi * np.arccos( np.abs(np.dot(v_left, v1)) )
        # alpha_right = 180 / np.pi * np.arccos( np.abs(np.dot(v_right, v1)) )
        # self.currentAngles[stentType] = (alpha_left, alpha_right)

        v1 = (p_middle - p_upper) / np.linalg.norm(p_upper - p_middle)
        v_left =( p_left - p_middle ) / np.linalg.norm(p_left - p_middle)
        v_right = (p_right - p_middle) / np.linalg.norm(p_right - p_middle)
        alpha_left = 180 / np.pi * np.arccos(np.dot(v_left, v1))
        alpha_right = 180 / np.pi * np.arccos(np.dot(v_right, v1))
        self.currentAngles[stentType] = (alpha_left, alpha_right)

    def updateProgressBar(self, value):
        """
        Updates progress bar
        Args:
            value: Percentage of execution

        """
        self.checkStopProcess()
        self.progressBar.setValue(value)
        slicer.app.processEvents()

    def checkStopProcess(self):
        """
        Checks if the process is stopped

        """
        slicer.app.processEvents()
        if self.progressBar.wasCanceled:
            self.progressBar.deleteLater()
            raise StopIteration("Progress cancelled!!!")
    def reset(self):
        """ Delete all the posible objects that have been used and init them back
        """
        nodesToRemove = []
        if self.currentVolumeId is not None:
            nodesToRemove.append(slicer.mrmlScene.GetNodeByID(self.currentVolumeId))
        if self.currentResultsNode is not None:
            nodesToRemove.append(self.currentResultsNode)
        if self.currentLabelmapResults is not None:
            nodesToRemove.append(self.currentLabelmapResults)

        if self.currentTracheaModel is not None:
            nodesToRemove.append(self.currentTracheaModel)
        # Remove all the cylinder models for every possible stent
        for node in self.currentCylindersModel.itervalues():
            if node is not None:
                nodesToRemove.append(node)

        #for node in itertools.chain.from_iterable(self.currentFiducialsListNodes.itervalues()):
        for value in self.currentFiducialsListNodes.itervalues():
            if value is not None:
                for node in value:
                    nodesToRemove.append(node)

        for node in nodesToRemove:
            slicer.mrmlScene.RemoveNode(node)

        self.__initVars__()


class CIP_TracheaStentPlanningOptimizedTest(ScriptedLoadableModuleTest):
    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
        """
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        """Run as few or as many tests as needed here.
        """
        self.setUp()
        self.test_CIP_TracheaStentPlanningOptimized_PrintMessage()

    def test_CIP_TracheaStentPlanningOptimized_PrintMessage(self):
        self.fail("Test not implemented!")

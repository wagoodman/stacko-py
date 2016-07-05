# -*- coding: utf-8 -*-
import os
import shutil

import classDb
import error

import subwrap

class Point(object):

    def __init__(self, name, imageHistory, currentImage):
        self.name = name
        self.imageHistory = imageHistory
        self.currentImage = currentImage

# Manages image relations and can spawn instances of images
class PointManager(classDb.ClassDb):

    dbFilename = "points.json"

    mountDir = None

    def __init__(self, *args, **kwargs):
        super(PointManager, self).__init__(*args, **kwargs)
        self.mountDir = kwargs['mountDir']
        if len(self.mountDir.strip()) <= 5:
            raise RuntimeError("Unexpected dirname: %s" % repr(self.mountDir))

        self.imageManager = kwargs['imageManager']

    def getMountPointDir(self, obj):
        if isinstance(obj, str):
            instanceDir = os.path.join(self.mountDir, obj)
        elif isinstance(obj, Image):
            instanceDir = os.path.join(self.mountDir, obj.name)
        elif isinstance(obj, Point):
            instanceDir = os.path.join(self.mountDir, obj.currentImage)
        else:
            raise RuntimeError("Invalid input given: %s" % repr(obj))
        return instanceDir

    def newPoint(self, pointName, imageName):
        # validate input against the manifest
        if pointName in self.db:
            raise error.StacksException("Point already exists: %s" % str(pointName))
        if imageName not in self.imageManager.db.keys():
            raise error.StacksException("Image does not exist: %s" % str(imageName))

        # check if the instance dir is already taken (for some reason)
        instanceDir = self.imageManager.getInstancesDir(imageName, pointName)
        if os.path.exists(instanceDir):
            raise error.StacksException("Manifest mismatch. Instance directory already exists: %s" % str(instanceDir))

        # ensure the mount point does not already exist
        mountPointDir = self.getMountPointDir(pointName)
        if os.path.exists(mountPointDir):
            raise error.StacksException("Manifest mismatch. Mount point already exists: %s" % str(mountPointDir))

        # create a new mount point directory
        os.mkdir(mountPointDir)
        # create an instance of the given image and associate with the point
        self.imageManager.newImageInstance(imageName, pointName)
        # update the manifest
        self.db[pointName] = Point(pointName, [imageName], imageName)

    def deletePoint(self, pointName):
        pass
        # TODO...
        # very destructive, kinda complicated, let's do this later

    def setPointInstance(self, pointName, imageName):
        # validate input against the manifest
        if pointName not in self.db:
            raise error.StacksException("Point does not exist: %s" % str(pointName))

        pointObj = self.db[pointName]

        if imageName not in pointObj.imageHistory:
            raise error.StacksException("Point instance does not exist: %s" % str(imageName))

        # ensure the image instance directory exists?
        # TODO... maybe?

        pointObj.currentImage = imageName

    def newPointInstance(self, pointName, imageName):
        # validate input against the manifest
        if pointName not in self.db:
            raise error.StacksException("Point does not exist: %s" % str(pointName))

        pointObj = self.db[pointName]

        # create an instance of the given image and associate with the point
        self.imageManager.newImageInstance(imageName, pointName)
        if imageName in pointObj.imageHistory:
            pointObj.imageHistory.remove(imageName)
        pointObj.imageHistory.append(imageName)

    def deletePointInstance(self, pointName, imageName):
        # validate input against the manifest
        if pointName not in self.db:
            raise error.StacksException("Point does not exist: %s" % str(pointName))

        pointObj = self.db[pointName]

        # If this is the current image instance, then there must be another to
        # fallback to, otherwise this point will have no instances, which should
        # not be possible. A simplification of this is to ensure that the
        # current image instance cannot be deleted
        if imageName == pointObj.currentImage:
            raise error.StacksException("Cannot delete the Point's main instance, cutover to another instance before deleting: point=%s image=%s" % (pointName,imageName))

        # delete the instance of the given image and associate with the point
        # and remove from operational history (otherwise fallbacks will fail)
        self.imageManager.deleteImageInstance(imageName, pointName)
        if imageName in pointObj.imageHistory:
            pointObj.imageHistory.remove(imageName)

    def mount(self, pointName):
        # validate input against the manifest
        if pointName not in self.db:
            raise error.StacksException("Point does not exist: %s" % str(pointName))

        pointObj = self.db[pointName]
        imageName = pointObj.currentImage

        pointDir = self.getMountPointDir(pointName)
        pointDir = os.path.abspath(pointDir)

        # TEMP TEMP TEMP: for the meantime, lets be verbose about mount/bind actions
        topMountDir = self.imageManager.mountInstance(imageName, pointName, writable=True, verbose=True)

        # if there was a successful mount, then bind the point dir to the
        # top mount dir
        if topMountDir:
            topMountDir = os.path.abspath(topMountDir)

            subwrap.run(['mount', '--bind','-o','rw', topMountDir, pointDir ])

        return pointDir

    def umount(self, pointName):
        # validate input against the manifest
        if pointName not in self.db:
            raise error.StacksException("Point does not exist: %s" % str(pointName))

        pointObj = self.db[pointName]
        imageName = pointObj.currentImage

        self.imageManager.umountInstance(imageName, pointName)

        # unbind the point dir
        pointDir = self.getMountPointDir(pointName)
        pointDir = os.path.abspath(pointDir)
        subwrap.run(['umount', pointDir ])

    def listPoints(self, pointName=None):

        def showPoint(name):
            pointObj = self.db[name]
            print("%s:"%name)
            imagesWithThisPointInstance = self.imageManager.getImagesWithInstanceName(name)
            for idx, imageObj in enumerate(sorted(imagesWithThisPointInstance)):
                isLast = idx == len(imagesWithThisPointInstance) - 1

                status = ""
                if pointObj.currentImage == imageObj.name:
                    status = " <--- current"

                if isLast:
                    print(' └── ' + imageObj.name + status)
                else:
                    print(' ├── ' + imageObj.name + status)

            if len(imagesWithThisPointInstance) == 0:
                print('    <no instances>')

        if pointName:
            showPoint(pointName)
        else:
            for name in sorted(self.db.keys()):
                showPoint(name)

# cutover-point: image-name
# fallback-point

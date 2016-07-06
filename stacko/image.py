# -*- coding: utf-8 -*-
import os
import shutil
import platform

import overlayUtils

import classDb
import error

class Image(object):

    def __init__(self, name, parent, version, instances):
        self.name = name
        self.parent = parent
        self.version = version
        self.instances = instances

    def __lt__(self, other):
        return self.name < other.name

# Manages image relations and can spawn instances of images
class ImageManager(classDb.ClassDb):

    dbFilename = "images.json"

    # image dir paths
    imageDir = None
    imageContentDir = "content"
    #imageInstancesDir = "instances"  # the image directory now serves as the instance dir,

    # reserved for internal use
    ownInstance = ".self"

    legacy = None


    def __init__(self, *args, **kwargs):
        super(ImageManager, self).__init__(*args, **kwargs)
        self.imagesDir = kwargs['imagesDir']

        if len(self.imagesDir.strip()) <= 5:
            raise RuntimeError("Unexpected dirname: {0!s}".format(repr(self.imagesDir)))

        if 'legacy' in kwargs:
            # allow forcing legacy behavior (for testing and general compatibility)
            self.legacy = kwargs['legacy']
        else:
            # detect legacy behavior from environment
            versions = platform.release().split(".")
            if int(versions[0]) < 3 or (int(versions[0]) == 3 and int(versions[1]) < 19 ) :
                self.legacy = True
            else:

                self.legacy = False


    def newImage(self, name, parent):
        # validate input against the manifest
        if name in self.db:
            raise error.StacksException("Image name already exists: {0!s}".format(str(name)))
        if parent is not None and parent not in self.db:
            raise error.StacksException("Parent does not exist: {0!s}".format(str(parent)))

        # check if the image dirs exist for the parent node
        if parent is not None:
            parentDir = self.getImageDir(parent)
            if not os.path.exists(parentDir):
                raise error.StacksException("Parent image directory does not exist: {0!s}".format(str(parentDir)))

        # ensure the node path does not exist already (for some reason)
        imageDir = self.getImageDir(name)
        if os.path.exists(imageDir):
            raise error.StacksException("Manifest mismatch. Image directory already exists: {0!s}".format(str(imageDir)))

        # create a new node directories and update the manifest
        os.mkdir(imageDir)

        self.db[name] = Image(name, parent, None, [])
        self.newImageInstance(name, self.ownInstance, force=True)


    def deleteImage(self, name):
        # validate input against the manifest
        if name not in self.db:
            raise error.StacksException("Image does not exist: {0!s}".format(str(name)))

        imageObj = self.db[name]
        children = self.getChildImages(name)

        # check if the image dirs exist for the parent node
        if len(children) > 0:
            childrenStr = ", ".join([ obj.name for obj in children ])
            raise error.StacksException("Image is supporting other images: {0!s}".format(childrenStr))

        # ensure there are no instantiations of this image
        if len(imageObj.instances) > 0:
            instancesStr = ", ".join(imageObj.instances)
            raise error.StacksException("Cannot delete an image that supports other instances: {0!s}".format(instancesStr))
        else:
            # double check to see the instance dir is really empty
            instancesDirLs = os.listdir(self.getInstancesDir(name))
            if self.ownInstance in instancesDirLs:
                instancesDirLs.remove(self.ownInstance)
            if len(instancesDirLs) > 0:
                raise error.StacksException("Manifest mismatch. Image may be supporting instances.")

        # ensure there are no instances being supported by this image currently mounted
        instancesInUse = []
        for instance in list(imageObj.instances):
            instanceMountDir = os.path.join( self.getInstancesDir(imageObj, instance),
                                             "mount")
            if overlayUtils.isMounted(instanceMountDir):
                instancesInUse.append(instance)

        if len(instancesInUse) > 0:
            instanceStr = ", ".join(instancesInUse)
            raise error.StacksException("Cannot delete an image that supports other mounted instances: {0!s}".format(instanceStr))

        instanceMountDir = os.path.join( self.getInstancesDir(imageObj, self.ownInstance),
                                         "mount")

        if overlayUtils.isMounted(instanceMountDir):
            raise error.StacksException("Cannot delete an image that is being edited. Use 'close-image' before deleting")

        # remove the image directory
        shutil.rmtree(self.getImageDir(name))
        del self.db[name]

    def mountImage(self, name, writable=False, verbose=False):
        return self.mountInstance(name, self.ownInstance, writable, verbose)

    def umountImage(self, name):
        return self.umountInstance(name, self.ownInstance)

    def newImageInstance(self, name, instanceName, force=False):
        # validate input against the manifest
        if name not in self.db:
            raise error.StacksException("Image name does not exist: {0!s}".format(str(name)))

        imageObj = self.db[name]

        # ensure the manifest does not already have that instance instantiated
        if instanceName in imageObj.instances:
            raise error.StacksException("Image instance already exists: {0!s}".format(str(instanceName)))

        # special case, don't allow creating a new "own" instance
        if force == False and instanceName == self.ownInstance:
            raise error.StacksException("Cannot modify internal instance: {0!s}".format(str(instanceName)))

        # ensure the node path does not exist already (for some reason)
        instanceDir = self.getInstancesDir(imageObj, instanceName)
        if os.path.exists(instanceDir):
            raise error.StacksException("Manifest mismatch. Image instance directory already exists: {0!s}".format(str(instanceDir)))

        # create a new instance directories and update the manifest
        os.mkdir(instanceDir)
        os.mkdir(os.path.join(instanceDir,"content"))
        os.mkdir(os.path.join(instanceDir,"mount"))
        os.mkdir(os.path.join(instanceDir,"working"))

        # we don't care about the .self instance in the manifest
        if instanceName != self.ownInstance:
            imageObj.instances.append(instanceName)

    def deleteImageInstance(self, name, instanceName, force=False):
        # validate input against the manifest
        if name not in self.db:
            raise error.StacksException("Image does not exist: {0!s}".format(str(name)))

        imageObj = self.db[name]

        # validate input against the manifest
        if instanceName not in imageObj.instances:
            raise error.StacksException("Image instance does not exist: {0!s}".format(str(instanceName)))

        # special case, don't allow deletion a new "own" instance
        if force == False and instanceName == self.ownInstance:
            raise error.StacksException("Cannot modify internal instance: {0!s}".format(str(instanceName)))

        instanceDir = self.getInstancesDir(name, instanceName)

        # Ensure there are no active mounts for this instance
        instanceMountDir = os.path.join( instanceDir, "mount")
        if overlayUtils.isMounted(instanceMountDir):
            raise error.StacksException("Cannot delete a mounted instances: {0!s}".format(instanceName))

        # remove the image directory
        shutil.rmtree(instanceDir)
        imageObj.instances.remove(instanceName)

    def mountInstance(self, name, instanceName, writable=False, verbose=False):

        # validate input against the manifest
        if name not in self.db:
            raise error.StacksException("Image does not exist: {0!s}".format(str(name)))

        imageObj = self.db[name]

        if instanceName not in imageObj.instances and instanceName != self.ownInstance:
            raise error.StacksException("Image instance does not exist: image={0!s} instance={1!s}".format(repr(name), repr(instanceName)))

        # two different strategies can be used based on the kernel version
        if self.legacy:
            depth = 0
            parent = imageObj.parent
            while parent is not None:
                depth += 1
                parent = self.db[name].parent

            # This number should include the instance to be mounted
            if depth > 2:
                raise error.StacksException("Image depth exceeds kernel maximum FS stacking depth (2).")

            return self._mountInstance_legacy(name, instanceName, writable, verbose)
        else:
            return self._mountInstance_standard(name, instanceName, writable, verbose)

    def umountInstance(self, name, instanceName):

        # validate input against the manifest
        if name not in self.db:
            raise error.StacksException("Image does not exist: {0!s}".format(str(name)))

        # two different strategies can be used based on the kernel version
        if self.legacy:
            return self._umountInstance_legacy(name, instanceName)
        else:
            return self._umountInstance_standard(name, instanceName)

    def _mountInstance_standard(self, name, instanceName, writable=False, verbose=False):
        """ [Image3]
                [.self]
                    [mount]     <not used>
                    [content]
                [instance1]
                    [mount]     upper=instnace1.content,
                                lower=Image1.self.content:Image2.self.content:Image3.self.content
                    [content]
            [Image2]
                [.self]
                    [mount]     <not used>
                    [content]
            [Image1]
                [.self]
                    [mount]     <not used>
                    [content]
        """
        imageObj = self.db[name]

        # ensure the image is not already mounted, if so, assume the remaining
        # parents are already mounted (as we will be unable to mount them
        # anyway if they are not already mounted)
        instanceDir = self.getInstancesDir(imageObj, instanceName)
        mountDir = os.path.join( instanceDir, "mount")
        if overlayUtils.isMounted(mountDir):
            return

        upperDir = os.path.join( instanceDir, "content")
        workingDir = os.path.join( instanceDir, "working")

        ownInstanceDir = self.getInstancesDir(imageObj, self.ownInstance)
        currentImageContent = os.path.join(ownInstanceDir, "content")
        lowerDir = [currentImageContent]

        parentName = imageObj.parent
        while parentName is not None:

            parentObj = self.db[parentName]
            parentInstanceDir = self.getInstancesDir(parentObj, self.ownInstance)
            lowerContentDir = os.path.join(parentInstanceDir, "content")
            lowerContentDir = os.path.abspath(lowerContentDir)
            lowerDir.append(lowerContentDir)

            # get the next parent to check
            parentName = parentObj.parent

        if verbose:
            print("Mounting:\n\tmount: {0!s}\n\tupper: {1!s}\n\tlower: {2!s}\n".format(os.path.abspath(mountDir),
                    os.path.abspath(upperDir),
                    repr(lowerDir)))

        overlayUtils.mount(directory=os.path.abspath(mountDir),
                           lower_dir=lowerDir,
                           upper_dir=os.path.abspath(upperDir),
                           working_dir=os.path.abspath(workingDir),
                           readonly=not writable)

        return mountDir


    def _umountInstance_standard(self, name, instanceName):

        imageObj = self.db[name]

        mountDir = os.path.join( self.getInstancesDir(imageObj, instanceName),
                                 "mount")
        if overlayUtils.isMounted(mountDir):
            overlayUtils.umount(mountDir)


    def _mountInstance_legacy(self, name, instanceName, writable=False, verbose=False):
        """ [Image3] <--- not possible due to overlayfs limitations with this kernel version!
            [Image2]
                [.self]
                    [mount]     upper=contents, lower=Image1:mount
                    [content]
                [instance1]
                    [mount]     upper=contents, lower=Image2.self:mount
                    [content]
            [Image1]
                [.self]
                    [mount]      bind mount to Image1.self.contents ----|
                    [content]         <---------------------------------|
        """
        imageObj = self.db[name]

        # ensure the image is not already mounted, if so, assume the remaining
        # parents are already mounted (as we will be unable to mount them
        # anyway if they are not already mounted)
        instanceDir = self.getInstancesDir(imageObj, instanceName)
        mountDir = os.path.join( instanceDir, "mount")
        if overlayUtils.isMounted(mountDir):
            return

        # Before mounting this instance, ensure the image is mounted as read-only.
        # This is done by mounting the ".self" instance of the current image.
        # After that, you can mount this [writable] instance
        if instanceName != self.ownInstance:
            self.mountImage(imageObj.name, writable=False)

        upperDir = os.path.join( instanceDir, "content")
        workingDir = os.path.join( instanceDir, "working")
        lowerDir = None

        # mount the necessary parent images, then mount the parent instance to .self
        if imageObj.parent is not None:
            if instanceName == self.ownInstance:
                self.mountImage(imageObj.parent, writable=False)

                parentInstanceDir = self.getInstancesDir(imageObj.parent,
                                                         self.ownInstance)
                lowerDir = os.path.join( parentInstanceDir, "mount")
            # ... or mount the non-.self instance
            else:
                ownInstanceDir = self.getInstancesDir(imageObj, self.ownInstance)
                lowerDir = os.path.join( ownInstanceDir, "mount")

            if verbose:
                print("Mounting:\n\tmount: {0!s}\n\tupper: {1!s}\n\tlower: {2!s}\n".format(os.path.abspath(mountDir),
                        os.path.abspath(upperDir),
                        os.path.abspath(lowerDir)))

            overlayUtils.mount(directory=os.path.abspath(mountDir),
                               lower_dir=os.path.abspath(lowerDir),
                               upper_dir=os.path.abspath(upperDir),
                               working_dir=os.path.abspath(workingDir),
                               readonly=not writable)

        # ... or this is the root, no need to mount parents
        else:
            import subwrap
            if writable:
                options="rw"
            else:
                options="ro"

            # This could be in use by other layers
            #subwrap.run(['umount', mountDir ])

            if verbose:
                print("Binding:\n\tmount: {0!s}\n\source: {1!s}\n".format(os.path.abspath(mountDir),
                        os.path.abspath(upperDir)))

            # perform a bind mount to the contents dir
            subwrap.run(['mount', '--bind','-o',options, upperDir, mountDir ])


        return mountDir

    def _umountInstance_legacy(self, name, instanceName):

        imageObj = self.db[name]

        if instanceName == self.ownInstance:

            # ensure there are no child images that are mounted
            children = self.getChildImages(name)
            childrenInUse = []
            for childObj in children:
                childMountDir = os.path.join( self.getInstancesDir(childObj, self.ownInstance),
                                              "mount")
                if overlayUtils.isMounted(childMountDir):
                    childrenInUse.append(childObj)

            if len(childrenInUse) > 0:
                childrenStr = ", ".join([ obj.name for obj in childrenInUse ])
                raise error.StacksException("Cannot unmount an image that supports other mounted images: {0!s}".format(childrenStr))

            # ensure there are no instances being supported by this image currently mounted
            instancesInUse = []
            for instance in imageObj.instances:
                instanceMountDir = os.path.join( self.getInstancesDir(imageObj, instance),
                                                 "mount")
                if overlayUtils.isMounted(instanceMountDir):
                    instancesInUse.append(instance)

            if len(instancesInUse) > 0:
                instanceStr = ", ".join(instancesInUse)
                raise error.StacksException("Cannot unmount an image that supports other mounted instances: {0!s}".format(instanceStr))

        # ensure the image is not already mounted, if so, assume the remaining
        # parents are already mounted (as we will be unable to mount them
        # anyway if they are not already mounted)
        mountDir = os.path.join( self.getInstancesDir(imageObj, instanceName),
                                 "mount")
        if overlayUtils.isMounted(mountDir):
            overlayUtils.umount(mountDir)

    def getImageDir(self, obj):
        if isinstance(obj, str):
            imageDir = os.path.join(self.imagesDir, obj)
        elif isinstance(obj, Image):
            imageDir = os.path.join(self.imagesDir, obj.name)
        else:
            raise RuntimeError("Invalid input given: {0!s}".format(repr(obj)))
        return imageDir

    def getContentDir(self, obj, instanceName=ownInstance):
        #return os.path.join(self.getImageDir(obj), self.imageContentDir)

        # the contents dir is now in the .self/contents instance dir
        return os.path.join( self.getInstancesDir(obj, instanceName),
                             self.imageContentDir)

    def getInstancesDir(self, obj, instanceName=None):
        # For the meantime, the instance dir is the image dir... this was different from
        # earlier, but this is an easy fix
        path = self.getImageDir(obj)

        #path = os.path.join(self.getImageDir(obj), self.imageInstancesDir)
        if instanceName:
            path = os.path.join(path, instanceName)

        return path

    def getChildImages(self, obj):
        if isinstance(obj, str):
            return [item for node, item in list(self.db.items()) if item.parent == obj]
        elif isinstance(obj, Image):
            return [item for node, item in list(self.db.items()) if item.parent == obj.name]
        raise RuntimeError("Invalid input given: {0!s}".format(repr(obj)))

    def getImagesWithInstanceName(self, instanceName):
        return [item for node, item in list(self.db.items()) if instanceName in item.instances]

    def listImages(self, tree=False):
        if tree:
            roots = [name for name, obj in list(self.db.items()) if obj.parent is None]
            parentNodes = set([obj.parent for name, obj in list(self.db.items()) if obj.parent is not None])

            def printTree(node, padding, isLast=False):

                if isLast:
                    print(padding + '└── ' + node)
                else:
                    print(padding + '├── ' + node)

                children = self.getChildImages(node)

                if isLast:
                    padding = padding + '    '
                else:
                    padding = padding + '│   '

                for i, child in enumerate(sorted(children)):
                    isLast = i == len(children) - 1

                    printTree(child.name, padding, isLast)

            for root in sorted(roots):
                print(root)
                children = self.getChildImages(root)
                for idx, child in enumerate(sorted(children)):
                    isLast = idx==len(children)-1
                    printTree(child.name, '', isLast)
                print()
        else:
            for imageName in sorted(self.db.keys()):
                print(imageName)


    def listInstances(self, imageName=None):

        def showInstances(name):
            imageObj = self.db[name]
            print("{0!s}:".format(name))
            for idx, instance in enumerate(imageObj.instances):
                isLast = idx == len(imageObj.instances) - 1
                if isLast:
                    print(' └── ' + instance)
                else:
                    print(' ├── ' + instance)

            if len(imageObj.instances) == 0:
                print('    <no instances>')

        if imageName:
            showInstances(imageName)
        else:
            for imageName in sorted(self.db.keys()):
                showInstances(imageName)



# mount image, name; (for editing)
# umount image, name; (close edits, make ro)
# import image, name, tarpath
# export image, name, tarpath

# rename image/instance? should this me allowed?

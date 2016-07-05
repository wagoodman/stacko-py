# -*- coding: utf-8 -*-
import platform
import argparse
import sys
import os

if platform.system() != "Linux":
    print("Unsupported platform")
    sys.exit(1)

class StacksOptions(object):

    def __init__(self, imageManager, pointManager):
        self.imageManager = imageManager
        self.pointManager = pointManager

        parser = argparse.ArgumentParser(
            description='Create and manage overlayFS stacks',
            usage='''stacko <command> [<args>]

Image commands:
    new-image     Create an image
    edit-image    Mount an image for editing
    close-image   Umount an image to stop editing
    delete-image
    list-images   Show the existing images
    import-image
    export-image

StackPoint commands:
    new-stackpoint
    delete-stackpoint

    # Nah... let wrappers do cutovers and fallbacks? then what is the point of a history??

    #cutover-stackpoint-instance: unmount a current instance, create a new instance of the given image (if it does not already exist), set the current instance, and mount the new current instance

    #fallback-stackpoint-instance: unmount a current instance, set the current instance to the last known image instance, and mount the new current instance

    new-stackpoint-instance

    set-stackpoint-instance: does not alter history, only the current image

    delete-stackpoint-instance

    mount-stackpoint
    umount-stackpoint
    get-stackpoint-dir
    is-stackpoint-mounted
''')
        parser.add_argument('command', help='Subcommand to run')
        # parse_args defaults to [1:] for args, but you need to
        # exclude the rest of the args too, or validation will fail
        args = parser.parse_args(sys.argv[1:2])
        command = args.command.replace("-","_")
        if not hasattr(self, command):
            print('Unrecognized command')
            parser.print_help()
            exit(1)
        # use dispatch pattern to invoke method with same name
        getattr(self, command)(startArg=2)


    # Point Commands
    def new_stackpoint(self, startArg=2):
        parser = argparse.ArgumentParser(description='Create a new point')
        parser.add_argument('pointname')
        parser.add_argument('imagename')
        args = parser.parse_args(sys.argv[startArg:])

        self.pointManager.newPoint(args.pointname, args.imagename)
        print('Created point: pointname=%s imagename=%s' % (repr(args.pointname), repr(args.imagename)))

    def list_stackpoints(self, startArg=2):
        parser = argparse.ArgumentParser(
            description='Show points')
        parser.add_argument('pointname',  nargs='?', default=None)
        args = parser.parse_args(sys.argv[2:])
        print('Running list-points')
        self.pointManager.listPoints(args.pointname)

    def mount_stackpoint(self, startArg=2):
        parser = argparse.ArgumentParser(
            description='Mount a stack points')
        parser.add_argument('pointname')
        args = parser.parse_args(sys.argv[2:])
        #print('Running mount-stackpoint')
        mountDir = self.pointManager.mount(args.pointname)
        if mountDir:
            mountDir = os.path.abspath(mountDir)
            print('Mounted stackpoint: name=%s\nmount-point=%s' % (repr(args.pointname), repr(mountDir)))

    def umount_stackpoint(self, startArg=2):
        parser = argparse.ArgumentParser(
            description='Mount a stack points')
        parser.add_argument('pointname')
        args = parser.parse_args(sys.argv[2:])
        #print('Running umount-stackpoint')
        self.pointManager.umount(args.pointname)

    # TEMP TEMP TEMP
    def new_stackpoint_instance(self, startArg=2):
        parser = argparse.ArgumentParser(description='Create a new point instance')
        parser.add_argument('pointname')
        parser.add_argument('imagename')
        args = parser.parse_args(sys.argv[startArg:])

        self.pointManager.newPointInstance(args.pointname, args.imagename)
        print('Created point instance: pointname=%s imagename=%s' % (repr(args.pointname), repr(args.imagename)))

    # TEMP TEMP TEMP
    def set_stackpoint_instance(self, startArg=2):
        parser = argparse.ArgumentParser(description='Set current point instance')
        parser.add_argument('pointname')
        parser.add_argument('imagename')
        args = parser.parse_args(sys.argv[startArg:])

        self.pointManager.setPointInstance(args.pointname, args.imagename)
        print('Set point instance: pointname=%s imagename=%s' % (repr(args.pointname), repr(args.imagename)))


    # TEMP TEMP TEMP
    def delete_stackpoint_instance(self, startArg=2):
        parser = argparse.ArgumentParser(description='Delete an existing point instance')
        parser.add_argument('pointname')
        parser.add_argument('imagename')
        args = parser.parse_args(sys.argv[startArg:])

        self.pointManager.deletePointInstance(args.pointname, args.imagename)
        print('Deleted point instance: pointname=%s imagename=%s' % (repr(args.pointname), repr(args.imagename)))


    # Image Commands
    def new_image(self, startArg=2):
        parser = argparse.ArgumentParser(description='Create a new image')
        parser.add_argument('name')
        parser.add_argument('parent',  nargs='?', default=None)
        args = parser.parse_args(sys.argv[startArg:])

        self.imageManager.newImage(args.name, args.parent)
        print('Added image: name=%s parent=%s' % (repr(args.name), repr(args.parent)))

    def delete_image(self, startArg=2):
        parser = argparse.ArgumentParser(description='Delete an existing image')
        parser.add_argument('name')
        args = parser.parse_args(sys.argv[startArg:])

        self.imageManager.deleteImage(args.name)
        print('Deleted image: name=%s ' % (repr(args.name),) )

    def edit_image(self, startArg=2):
        parser = argparse.ArgumentParser(description='Mount an image')
        parser.add_argument('name')
        parser.add_argument('--read-only', '-r', action='store_true')
        args = parser.parse_args(sys.argv[startArg:])

        if os.geteuid() != 0:
            print("You need to have root privileges to mount images.")
            sys.exit(1)

        mountDir = self.imageManager.mountImage(args.name, not args.read_only)
        mountDir = os.path.abspath(mountDir)
        print('Mount image: name=%s read-only=%s\nmount-point=%s' % (repr(args.name), repr(args.read_only), repr(mountDir)))

    def close_image(self, startArg=2):
        parser = argparse.ArgumentParser(description='Mount an image')
        parser.add_argument('name')
        args = parser.parse_args(sys.argv[startArg:])

        if os.geteuid() != 0:
            print("You need to have root privileges to mount images.")
            sys.exit(1)

        self.imageManager.umountImage(args.name)
        print('Umount image: name=%s ' % (repr(args.name), ))

    def list_images(self, startArg=2):
        parser = argparse.ArgumentParser(
            description='Show installed images')
        parser.add_argument('--tree', '-t', action='store_true')
        args = parser.parse_args(sys.argv[2:])
        print('Running list-images')
        self.imageManager.listImages(tree=args.tree)

    def list_instances(self, startArg=2):
        parser = argparse.ArgumentParser(
            description='Show instances generated')
        parser.add_argument('imagename',  nargs='?', default=None)
        args = parser.parse_args(sys.argv[2:])
        print('Running list-instances')
        self.imageManager.listInstances(args.imagename)



    # TEMP TEMP TEMP
    def new_instance(self, startArg=2):
        parser = argparse.ArgumentParser(description='Create a new image')
        parser.add_argument('imagename')
        parser.add_argument('pointname')
        args = parser.parse_args(sys.argv[startArg:])

        self.imageManager.newImageInstance(args.imagename, args.pointname)
        print('Added instnace: name=%s point=%s' % (repr(args.imagename), repr(args.pointname)))

    # TEMP TEMP TEMP
    def delete_instance(self, startArg=2):
        parser = argparse.ArgumentParser(description='Delete an existing image')
        parser.add_argument('imagename')
        parser.add_argument('pointname')
        args = parser.parse_args(sys.argv[startArg:])

        self.imageManager.deleteImageInstance(args.imagename, args.pointname)
        print('Deleted instance: name=%s point=%s' % (repr(args.imagename), repr(args.pointname)))


    """
    def new_image(self):
        parser = argparse.ArgumentParser(
            description='Create a new image')
        # prefixing the argument with -- means it's optional
        parser.add_argument('--amend', action='store_true')
        # now that we're inside a subcommand, ignore the first
        # TWO argvs, ie the command (git) and the subcommand (commit)
        args = parser.parse_args(sys.argv[2:])
        print 'Running git commit, amend=%s' % args.amend
    """

import image
import point
import error

import fasteners

# Only serial access should be allowed for modifying data structures. This should
# be true regarding general access, not just when writing the DB. This is because
# two concurrent instances of this application, even when the DB is valid, could
# result in the state of an image/instance/etc to be "forked" and one instance
# may be using a stale copy of what is in the DB --wrong decisions could be made.
@fasteners.interprocess_locked('/tmp/stacksDb.lock')
def main():
    imageManager = image.ImageManager.from_db(metadataDir="metadata",
                                              itemCls=image.Image,
                                              imagesDir="images")

    pointManager = point.PointManager.from_db(metadataDir="metadata",
                                              itemCls=point.Point,
                                              mountDir="mounts",
                                              imageManager=imageManager)

    try:
        StacksOptions(imageManager, pointManager)
        imageManager.to_db()
        pointManager.to_db()
    except error.StacksException as e:
        print("Error:\n\t%s"%str(e))

main()

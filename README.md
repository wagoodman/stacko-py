# Stacko
This is a overlayFS manager that provides 'stacking' functionalities similar
to Docker images, but not tied specifically to a container solution. With Stacko
you can create immutable "images" which stack together. You can create one or more
writable "instances" of a stack that have a thin Copy-On-Write layer. These
instances are usable at a named "stackpoint", which always points to an instance.
Eventually you can cutover a stackpoint to a new instance and fallback to a
previous instance without copying or destroying files.

<b><i>Note: this is a work in progress, so it is not stable or finished yet.</i></b>

## Dependencies
This package requires the following packages to function:
- https://github.com/wagoodman/overlayUtils
- subwrap (pip install subwrap)

## Example
A working concept of how Stacko works:
```
# create and populate a new image 'foundation-libs0.1'
stacko new-image foundation-libs0.1
stacko edit-image foundation-libs0.1
   ...<head to the mount directory and add/edit contents>
stacko close-image foundation-libs0.1

# create another image 'apps-1.0' which "stacks" on image 'foundation-libs0.1'
stacko new-image apps-1.0 foundation-libs0.1
stacko edit-image apps-1.0
   ...<head to the mount directory and add/edit contents>
stacko close-image apps-1.0

# create a stackpoint named 'system1fs'. This automatically creates a new instance
# of the 'apps-1.0' image
stacko new-stackpoint system1fs apps-1.0

# mount the 'system1fs' for usage...
stacko mount-stackpoint system1fs

<reboot>
# This is all you need to do to use this stack again!
stacko mount-stackpoint system1fs

...

# Time to upgrade to another version of the application
stacko new-image apps-2.0 foundation-libs0.1
<populate it as before>...

# Use this new image as a new instance for the 'system1fs' stackpoint:
stacko cutover-stackpoint system1fs apps-2.0

# Oh no! something is wrong and you need to go back to the previous instance used
# (this includes all changes made in the CoW layer)
stacko fallback-stackpoint system1fs
```

## Motivation
This came about when looking for a solution that provided the prescriptive-ness of
a Docker image, something that can be stacked and referenced, but not written to.
Though, using this solution implies that you will use Docker --the image/layer/storage
solution is closely coupled to the container engine. This means that you need to
run the Docker daemon to create images, even if you intend to export them for use
with systemd-nspawn instead. Secondly, exporting the image merges all of the layers
into a single directory! Though `docker save` keeps the layers in separate directories
you are now closely tied to the Docker image format.

What I really wanted (right or wrong) was the ability to manage this concept of
immutable "images" in layers, with the ability to fork off CoW instances on a whim,
and do all of this without being tied to a particular container engine.

## Usage
```
usage: stacko <command> [<args>]

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
    cutover-stackpoint-instance:    unmount a current instance, create a new
        instance of the given image (if it does not already exist), set the
        current instance, and mount the new current instance

    fallback-stackpoint-instance:   unmount a current instance, set the
        current instance to the last known image instance, and mount the
        new current instance
    new-stackpoint-instance
    set-stackpoint-instance
    delete-stackpoint-instance
    mount-stackpoint
    umount-stackpoint
    get-stackpoint-dir
    is-stackpoint-mounted
```

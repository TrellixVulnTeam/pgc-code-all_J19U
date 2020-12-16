

# Constants
rts_objects_p = r''
seg_img = r''
seg_params = r''
class_field = ''

# Params
buffer_size = r''

# Load image objects


# Create bounding box geometries for each RTS object


# Iterate each object, clipping to buffered bounding box
# and writing to new file
# Eventually make this a function that returns a temporary (vsimem) chip image
# that the segmentation can work on (if OTB can take vsimem paths)






import arcpy, os, sys, re
from datetime import date

def convertCoords(ddm):
    d,m = ddm.split(" ");
    if int(d)<0:
        dd = -1*(abs(int(d))+float(m)/60)
    else:
        dd = int(d)+float(m)/60
    return float(dd)

def convertDateForFilename(d):
    m,d,y = d.split("/")
    dt = date(int(y),int(m),int(d))
    return dt.strftime("%Y-%b-%d")

def convertDateForHeader(d):
    m,d,y = d.split("/")
    dt = date(int(y),int(m),int(d))
    return dt.strftime("%B %d, %Y")

## -- CHECK ARCGIS VERSION COMPATIBILITY -- ##
version_regex = "^10+\.+[6-9]"
version = arcpy.GetInstallInfo()["Version"]
if re.match(version_regex,version) is None:
    arcpy.AddError("Your ArcGIS version (%s) is not compatible with this script. Please upgrade to 10.6+"%(version))
    sys.exit(1)
else:
    arcpy.AddMessage("Version Check: Okay. (%s)"%version)


# -- GENERAL SETTINGS -- #
output_dpi = 150
output_quality = 95

# -- GET TOOL PARAMETERS -- #
arcpy.AddMessage("Reading input...")

traverse = arcpy.GetParameterAsText(0)
trip_num = arcpy.GetParameterAsText(1)
direction = arcpy.GetParameterAsText(2)
trav_date = arcpy.GetParameterAsText(3)
lat_ddm = arcpy.GetParameterAsText(4)
lon_ddm = arcpy.GetParameterAsText(5)
miles_acc = arcpy.GetParameterAsText(6)
miles_rem = arcpy.GetParameterAsText(7)
waypoint = arcpy.GetParameterAsText(8)
include_label = arcpy.GetParameterAsText(9)

if include_label == 'false':
    label_value = 0
else:
    label_value = 1

# -- ESTABLISH DIRECTORIES -- #
pathname = os.path.dirname(sys.argv[0])
base = pathname.replace(r"tools\scripts","")

spot=0
salsa_longhaul=0
salsa_shuttle=0
salsa=0
was_byrd=0
was_thwaites=0
was_traverse=0
raid=0

if traverse == "SALSA Longhaul":
    salsa_longhaul=1
    mxd = arcpy.mapping.MapDocument(os.path.join(base,"SALSA_Longhaul.mxd"))
elif traverse == "SALSA Shuttle":
    salsa_shuttle=1
    mxd = arcpy.mapping.MapDocument(os.path.join(base,"SALSA_Shuttle.mxd"))
elif traverse == "WAS Traverse WAIS to Byrd":
    was_byrd=1
    mxd = arcpy.mapping.MapDocument(os.path.join(base,"WAS_Traverse.mxd"))
elif traverse == "WAS Traverse Thwaites":
    was_thwaites=1
    mxd = arcpy.mapping.MapDocument(os.path.join(base,"WAS_Traverse.mxd"))
else:
    spot=1
    mxd = arcpy.mapping.MapDocument(os.path.join(base,"SPoT_McMurdo_to_Pole.mxd"))

was_traverse = was_byrd + was_thwaites
salsa = salsa_longhaul + salsa_shuttle

outJPEG = os.path.join(base,"deliverables","Traverse Daily Update %s Trip %s %s.jpg"%(traverse,trip_num,convertDateForFilename(trav_date)))
gdb = arcpy.env.workspace = os.path.join(base,"data","data.gdb")
pts = "traverse_actual_waypoints_201819"
pts_fields = ["traverse","direction","trip","sequence","lat_dd","lon_dd","lat_ddm","lon_ddm","trav_date","waypoint_name","comments","include_label","SHAPE@XY"]
lns = "traverse_actual_route_201819"
lns_fields = ["traverse","direction","trip","sequence","lat_start","lon_start","lat_end","lon_end","trav_date","SHAPE@"]

# -- CONVERT COORDINATES -- #
lat_dd = convertCoords(lat_ddm)
lon_dd = convertCoords(lon_ddm)

# -- SET ORIGIN AND DESTINATION -- #

# SPoT
if direction == "Outbound" and spot == 1:
    origin =  "McMurdo Station"
    destination = "South Pole"

if direction == "Inbound" and spot == 1:
    origin =  "McMurdo Station"
    destination = "South Pole"

# WAS Traverse
# WAIS - Byrd
if direction == "Outbound" and was_byrd == 1:
    origin =  "WAIS Divide Camp"
    destination = "Byrd Surface Camp"

if direction == "Inbound" and was_byrd == 1: 
    origin =  "Byrd Surface Camp"
    destination = "WAIS Divide Camp" 

 # WAIS - Thwaites
if direction == "Outbound" and was_thwaites == 1:
    origin =  "WAIS Divide Camp"
    destination = "LTG"

if direction == "Inbound" and was_thwaites == 1:
    origin =  "LTG"
    destination = "WAIS Divide Camp"

# SALSA
if direction == "Outbound" and salsa_longhaul == 1:
    origin =  "McMurdo Station"
    destination = "Camp 20"

if direction == "Inbound" and salsa_longhaul == 1:
    origin =  "Camp 20"
    destination = "McMurdo Station"

if direction == "Outbound" and salsa_shuttle == 1:
    origin =  "Camp 20"
    destination = "SLM"

if direction == "Inbound" and salsa_shuttle == 1:
    origin =  "SLM"
    destination = "Camp 20"

# -- READ/WRITE DATA -- #
# Retrieve Last Point and Sequence #
arcpy.AddMessage("Adding point...")
sql = "traverse = '%s' AND trip = %s AND direction = '%s'" % (traverse,trip_num,direction)
with arcpy.da.SearchCursor(pts,pts_fields,sql) as cursor:
    sequence = next_sequence = 1
    for row in cursor:
        if row[3] >= sequence:
            sequence = row[3]
            lat_start = row[4]
            lon_start = row[5]
            prev_pt = arcpy.Point(lon_start,lat_start)
            next_sequence = sequence+1
del cursor

# Add Point

with arcpy.da.InsertCursor(pts,pts_fields) as cursor:
    new_pt = arcpy.Point(lon_dd,lat_dd)
    row = (traverse,direction,trip_num,next_sequence,lat_dd,lon_dd,lat_ddm,lon_ddm,trav_date,waypoint,"NO COMMENTS",label_value,new_pt)
    cursor.insertRow(row)
del cursor

# Add Line
arcpy.AddMessage("Adding line...")
if next_sequence > 1:
    array = arcpy.Array([prev_pt,new_pt])
    line = arcpy.Polyline(array)
    with arcpy.da.InsertCursor(lns,lns_fields) as cursor:
        row = (traverse,direction,trip_num,next_sequence,lat_start,lon_start,lat_dd,lon_dd,trav_date,line)
        cursor.insertRow(row)
    del cursor

# -- EXPORT MAP -- #
# Update Map Document Text
arcpy.AddMessage("Updating map text...")
header_text = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "Header_Text")[0]

if salsa_longhaul > 0:
    route = "SALSA Longhaul"
    traverse_title = "SALSA Traverse"
if salsa_shuttle > 0:
    route = "SALSA Shuttle"
    traverse_title = "SALSA Traverse"
if was_byrd > 0: 
    route = "WAIS-Byrd"
    traverse_title = "West Antarctic Support (WAS) Traverse"
if was_thwaites > 0:
    route = "Thwaites" # Change to Dean's preference
    traverse_title = "West Antarctic Support (WAS) Traverse"
if spot > 0:
    route = traverse
    traverse_title = "South Pole Traverse (SPoT)"

header_text.text = "%s 2018-19 <BOL>%s - Trip %s</BOL>"%(traverse_title,route,trip_num)

date_text = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "Date_Text")[0]
date_text.text = "Daily Update: <BOL>%s</BOL>"%(convertDateForHeader(trav_date))

if was_thwaites == 1:
	miles_rem = "n/a"

route_details = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", "Route_Details")[0]
route_details.text = """Route: <BOL>%s</BOL>
Trip Number: <BOL>%s</BOL>
Direction: <BOL>%s</BOL>
Report Date: <BOL>%s</BOL>
Origin: <BOL>%s</BOL>
Destination: <BOL>%s</BOL>
Miles Advanced: <BOL>%s</BOL>
Miles Remaining: <BOL>%s</BOL>"""%(route,trip_num,direction,convertDateForFilename(trav_date),origin,destination,miles_acc,miles_rem)

# Update Layer Definition Query
df = arcpy.mapping.ListDataFrames(mxd)[0]
pt_lyr = arcpy.mapping.ListLayers(mxd, "Traverse Waypoints (Actual 2018-19)", df)[0]
pt_lyr.definitionQuery = sql

ln_lyr = arcpy.mapping.ListLayers(mxd, "Traverse Route (Actual 2018-19)", df)[0]
ln_lyr.definitionQuery = sql

arcpy.AddMessage("Exporting map...")
mxd.save()

# Export to JPEG
arcpy.mapping.ExportToJPEG(mxd,outJPEG, resolution=output_dpi,jpeg_quality=output_quality)
arcpy.AddMessage("Map exported: %s"%outJPEG)
del mxd

// Author: Tom Bisson
// Affiliation: Institute of Pathology, Charité-Universitätsmedizin Berlin, Berlin, Germany
// Date: January 17, 2024
// Instructions: First higlight the area of tissue that should be exported with an annotation tool

int patch_size = 224
def image_extension = ".png"
def image_data = getCurrentImageData()

def out_path = "INSERT PATH HERE e.g. C:\\Users\\example\\Documents\\images for windows"

tile_exporter = new TileExporter(image_data)
tile_exporter.imageExtension(image_extension)
tile_exporter.tileSize(patch_size)
tile_exporter.annotatedTilesOnly(true)
tile_exporter.writeTiles(out_path)

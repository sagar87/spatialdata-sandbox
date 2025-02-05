##
import shutil
from pathlib import Path
import spatialdata as sd
import anndata as ad
import imageio.v3 as iio

##
path = Path().resolve()
# luca's workaround for pycharm
if not str(path).endswith("mibitof"):
    path /= "mibitof"
    assert path.exists()
path_read = path / "data"
path_write = path / "data.zarr"

##
libraries = ["point8", "point16", "point23"]

table_list = []
for lib in libraries:
    table = ad.read(path_read / f"{lib}_table.h5ad")
    table.obs["library_id"] = f"/labels/{lib}"
    table_list.append(table)

table = ad.concat(
    table_list,
    keys=libraries,
)
table = sd.TableModel.parse(
    adata=table,
    region=[f"/labels/{lib}" for lib in libraries],
    region_key="library_id",
    instance_key="cell_id",
)

##
labels = {
    lib: sd.Labels2DModel.parse(iio.imread(path_read / f"{lib}_labels.png"), dims=("y", "x"))
    for lib in libraries
}
images = {
    lib: sd.Image2DModel.parse(
        iio.imread(path_read / f"{lib}_image.png"),
        dims=("y", "x", "c"),
    )
    for lib in libraries
}

##

sdata = sd.SpatialData(
    table=table,
    labels=labels,
    images=images,
    # transformations={(f"/images/{lib}", lib): None for lib in libraries}
    # | {(f"/labels/{lib}", lib): None for lib in libraries}
)
print(sdata)

##
if path_write.exists():
    shutil.rmtree(path_write)
sdata.write(path_write)
print("done")
print(f'view with "python -m spatialdata view data.zarr"')
##
sdata = sd.SpatialData.read(path_write)
print(sdata)
print("read")

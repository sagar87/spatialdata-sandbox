##
import numpy as np
import anndata as ad
import shutil
from pathlib import Path
import spatialdata as sd
import re
import os
from tqdm import tqdm
import xarray as xr
from spatialdata_io import (
    circles_anndata_from_coordinates,
    table_update_anndata,
)

##
path = Path().resolve()
# luca's workaround for pycharm
if not str(path).endswith("visium"):
    path /= "visium"
    assert path.exists()
path_read = path / "data"
path_write = path / "data.zarr"

libraries = [re.sub(".h5ad", "", i) for i in os.listdir(path_read / "tables")]

##
table_list = []
images = {}
points = {}
images_transforms = {}
for lib in tqdm(libraries, desc="loading visium libraries"):
    # prepare table
    table = ad.read(path_read / "tables" / f"{lib}.h5ad")
    table.var_names_make_unique()
    table.obs["library_id"] = f"/points/{lib}"
    table.obs["visium_spot_id"] = np.arange(len(table))
    table_list.append(table)

    # prepare image
    lib_keys = list(table.uns["spatial"].keys())
    assert len(lib_keys) == 1
    lib_key = lib_keys[0]
    img = table.uns["spatial"][lib_key]["images"]["hires"]
    images[lib] = xr.DataArray(img, dims=("y", "x", "c"))

    # prepare circles
    radius = table.uns["spatial"][lib_key]["scalefactors"]["spot_diameter_fullres"] / 2
    shape_regions = circles_anndata_from_coordinates(
        coordinates=table.obsm["spatial"],
        radii=radius,
        instance_key="visium_spot_id",
        instance_values=np.arange(len(table)),
    )
    points[lib] = shape_regions

    # prepare transformation
    scale_factors = np.array(
        [1.0]
        + [1 / table.uns["spatial"][lib_key]["scalefactors"]["tissue_hires_scalef"]] * 2
    )
    transform = sd.Scale(scale=scale_factors)
    images_transforms[lib] = transform

table = ad.concat(
    table_list,
    label="library",
    keys=libraries,
)

table_update_anndata(
    adata=table,
    regions=[f"/points/{lib}" for lib in libraries],
    regions_key="library_id",
    instance_key="visium_spot_id",
)

sdata = sd.SpatialData(
    table=table,
    images=images,
    points=points,
    transformations={
        (f"/images/{lib}", lib): images_transforms[lib] for lib in libraries
    }
    | {(f"/points/{lib}", lib): None for lib in libraries},
)
print(sdata)

##
if path_write.exists():
    shutil.rmtree(path_write)
sdata.write(path_write)
print("done")
print(f'view with "python -m spatialdata view data.zarr"')
sdata = sd.SpatialData.read(path_write)
print(sdata)
print("read")

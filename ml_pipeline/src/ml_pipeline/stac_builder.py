"""
ml_pipeline.stac_builder
~~~~~~~~~~~~~~~~~~~~~~~~
Build & load STAC Collections/Items from COGs stored in DigitalOcean Spaces.

Requires
--------
pip install boto3 pystac pypgstac rasterio python-dotenv
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import os
import calendar
import json
import tempfile
import subprocess
from typing import Iterable, Sequence

import boto3
import rasterio
from rasterio.warp import transform_bounds
from dotenv import load_dotenv
from pystac import (
    Item,
    Collection,
    Asset,
    MediaType,
    Link,
    Extent,
    SpatialExtent,
    TemporalExtent,
)

from .s3_utils import get_s3_client, list_files

# ---------------------------------------------------------------------
#  Configuration dataclass
# ---------------------------------------------------------------------


@dataclass
class STACBuilderConfig:
    # DigitalOcean Spaces
    bucket: str = "choco-forest-watch"

    # PgSTAC connection is handled through env vars
    pg_env_vars: dict[str, str] = field(
        default_factory=lambda: {
            "PGHOST": 'localhost',
            "PGPORT": os.getenv("DB_PORT"),
            "PGDATABASE": os.getenv("POSTGRES_DB"),
            "PGUSER": os.getenv("POSTGRES_USER"),
            "PGPASSWORD": os.getenv("POSTGRES_PASSWORD"),
        }
    )

# Set database connection environment variables needed by pypgstac
os.environ['PGHOST'] = 'localhost'
os.environ['PGPORT'] = os.getenv('DB_PORT')
os.environ['PGDATABASE'] = os.getenv('POSTGRES_DB')
os.environ['PGUSER'] = os.getenv('POSTGRES_USER')
os.environ['PGPASSWORD'] = os.getenv('POSTGRES_PASSWORD')


# ---------------------------------------------------------------------
#  STACBuilder class
# ---------------------------------------------------------------------


class STACBuilder:
    """
    Utility to scan a bucket prefix, build STAC Collection/Items, and upsert to pgSTAC.

    Parameters
    ----------
    cfg
        STACBuilderConfig with Spaces + pgSTAC settings.
    """

    def __init__(self, cfg: STACBuilderConfig = STACBuilderConfig()):
        load_dotenv()
        self.cfg = cfg
        self.s3, _ = get_s3_client(cfg.bucket)
        # ensure pypgstac can see DB creds
        os.environ.update(cfg.pg_env_vars)

    # ------------------------------------------------------------------
    #  Public helpers
    # ------------------------------------------------------------------

    def list_cogs(self, prefix: str) -> list[dict]:
        """Return every `.tif[f]` under a prefix with S3 URL + key."""
        return list_files(prefix, self.cfg.bucket)

    def build_collection(
        self,
        collection_id: str,
        year: str,
        month: str | None = None,
        description: str | None = None,
        license: str = "proprietary",
    ) -> Collection:
        """
        Build a STAC Collection for either monthly or annual data.
        
        Parameters
        ----------
        collection_id : str
            The ID for the collection
        year : str
            The year of the data
        month : str | None, optional
            The month of the data. If None, creates an annual collection.
        description : str | None, optional
            Collection description. If None, generates one based on temporal extent.
        license : str, optional
            The license for the collection, by default "proprietary"
        """
        if month:
            first = datetime(int(year), int(month), 1)
            last = datetime(
                int(year), int(month), calendar.monthrange(int(year), int(month))[1]
            )
            desc = description or f"Monthly data for {year}-{month}"
        else:
            first = datetime(int(year), 1, 1)
            last = datetime(int(year), 12, 31)
            desc = description or f"Annual data for {year}"

        col = Collection(
            id=collection_id,
            description=desc,
            license=license,
            extent=Extent(
                SpatialExtent([[-180, -90, 180, 90]]),
                TemporalExtent([[first, last]]),
            ),
        )

        col.add_link(
            Link(
                rel="license",
                target="https://www.planet.com/nicfi/",
                media_type="text/html",
                title="NICFI License",
            )
        )
        return col

    def build_item(
        self,
        cog: dict,
        year: str,
        month: str | None = None,
        asset_key: str = "data",
        asset_roles: Sequence[str] = ("data",),
        asset_title: str | None = None,
        media_type: str = MediaType.COG,
        extra_asset_fields: dict | None = None,
        derived_from: str | None = None,
    ) -> Item:
        """Return a STAC Item (bounds derived from the COG itself)."""
        with rasterio.open(cog["url"]) as ds:
            wgs_bounds = transform_bounds(ds.crs, "EPSG:4326", *ds.bounds)

        if month:
            dt = datetime(int(year), int(month), 1)
        else:
            dt = datetime(int(year), 1, 1)
            
        item_id = Path(cog["key"]).stem

        itm = Item(
            id=item_id,
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [wgs_bounds[0], wgs_bounds[1]],
                        [wgs_bounds[2], wgs_bounds[1]],
                        [wgs_bounds[2], wgs_bounds[3]],
                        [wgs_bounds[0], wgs_bounds[3]],
                        [wgs_bounds[0], wgs_bounds[1]],
                    ]
                ],
            },
            bbox=list(wgs_bounds),
            datetime=dt,
            properties={},
        )

        asset_dict = {
            "href": cog["url"],
            "media_type": media_type,
            "roles": list(asset_roles),
            "title": asset_title or f"{asset_key} for {item_id}",
        }
        if extra_asset_fields:
            asset_dict.update(extra_asset_fields)

        itm.add_asset(asset_key, Asset.from_dict(asset_dict))

        # provenance link
        if derived_from:
            itm.add_link(
                Link(
                    rel="derived_from",
                    href=derived_from,
                    media_type="application/json",
                )
            )

        return itm

    def upsert_to_pgstac(self, collection: Collection, items: Iterable[Item]) -> None:
        """Write temp JSON / ndjson and call pypgstac CLI."""
        with tempfile.TemporaryDirectory() as tmp:
            col_path = Path(tmp) / "collection.json"
            items_path = Path(tmp) / "items.ndjson"

            collection.save_object(dest_href=str(col_path))
            with items_path.open("w") as f:
                for it in items:
                    f.write(json.dumps(it.to_dict()) + "\n")

            subprocess.run(
                ["pypgstac", "load", "collections", "--method", "upsert", str(col_path)],
                check=True,
            )
            subprocess.run(
                ["pypgstac", "load", "items", "--method", "upsert", str(items_path)],
                check=True,
            )
            print(f"✅ Upserted ⟨{collection.id}⟩ and {len(list(items))} items")

    def process_month(
        self,
        year: str,
        month: str,
        prefix_on_s3: str,
        collection_id: str,
        asset_key: str,
        asset_roles: Sequence[str],
        asset_title: str,
        *,
        extra_asset_fields: dict | None = None,
        derived_from_tpl: str | None = None,
    ) -> None:
        """
        Process monthly data and create STAC collection/items.
        
        Parameters
        ----------
        year : str
            The year of the data
        month : str
            The month of the data
        prefix_on_s3 : str
            The S3 prefix where the data is stored
        collection_id : str
            The ID for the STAC collection
        asset_key : str
            The key for the asset in the STAC item
        asset_roles : Sequence[str]
            The roles for the asset
        asset_title : str
            The title for the asset
        extra_asset_fields : dict | None, optional
            Additional fields to add to the asset
        derived_from_tpl : str | None, optional
            Template for the derived_from link
        """
        month_str = f"{int(month):02d}"
        year_str = str(year)
        s3_prefix = f"{prefix_on_s3}/{year_str}/{month_str}"

        cogs = self.list_cogs(s3_prefix)
        print(f"🔍 Found {len(cogs)} COGs under {s3_prefix}")

        col = self.build_collection(
            collection_id=collection_id,
            year=year_str,
            month=month_str,
            description=f"{asset_title} for {year_str}-{month_str}",
        )

        items: list[Item] = []
        for cg in cogs:
            derived_href = (
                derived_from_tpl.format(item_id=Path(cg["key"]).stem)
                if derived_from_tpl
                else None
            )
            it = self.build_item(
                cog=cg,
                year=year_str,
                month=month_str,
                asset_key=asset_key,
                asset_roles=asset_roles,
                asset_title=asset_title,
                extra_asset_fields=extra_asset_fields,
                derived_from=derived_href,
            )
            items.append(it)
            col.add_item(it)

        self.upsert_to_pgstac(col, items)

    def process_year(
        self,
        year: str,
        prefix_on_s3: str,
        collection_id: str,
        asset_key: str,
        asset_roles: Sequence[str],
        asset_title: str,
        *,
        extra_asset_fields: dict | None = None,
        derived_from_tpl: str | None = None,
    ) -> None:
        """
        Process annual data and create STAC collection/items.
        
        Parameters
        ----------
        year : str
            The year of the data
        prefix_on_s3 : str
            The S3 prefix where the data is stored
        collection_id : str
            The ID for the STAC collection
        asset_key : str
            The key for the asset in the STAC item
        asset_roles : Sequence[str]
            The roles for the asset
        asset_title : str
            The title for the asset
        extra_asset_fields : dict | None, optional
            Additional fields to add to the asset
        derived_from_tpl : str | None, optional
            Template for the derived_from link
        """
        year_str = str(year)
        s3_prefix = f"{prefix_on_s3}/{year_str}"

        cogs = self.list_cogs(s3_prefix)
        print(f"🔍 Found {len(cogs)} COGs under {s3_prefix}")

        col = self.build_collection(
            collection_id=collection_id,
            year=year_str,
            description=f"{asset_title} for {year_str}",
        )

        items: list[Item] = []
        for cg in cogs:
            derived_href = (
                derived_from_tpl.format(item_id=Path(cg["key"]).stem)
                if derived_from_tpl
                else None
            )
            it = self.build_item(
                cog=cg,
                year=year_str,
                asset_key=asset_key,
                asset_roles=asset_roles,
                asset_title=asset_title,
                extra_asset_fields=extra_asset_fields,
                derived_from=derived_href,
            )
            items.append(it)
            col.add_item(it)

        self.upsert_to_pgstac(col, items)
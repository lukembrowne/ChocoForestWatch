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

        # Spaces client
        self.s3 = boto3.session.Session().client(
            "s3",
            region_name=os.getenv("AWS_REGION"),
            endpoint_url= "https://" + os.getenv("AWS_S3_ENDPOINT"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

        # ensure pypgstac can see DB creds
        os.environ.update(cfg.pg_env_vars)

    # ------------------------------------------------------------------
    #  Public helpers
    # ------------------------------------------------------------------

    def list_cogs(self, prefix: str) -> list[dict]:
        """Return every `.tif[f]` under a prefix with S3 URL + key."""
        print(f"Listing COGs under {prefix}")
        resp = self.s3.list_objects_v2(Bucket=self.cfg.bucket, Prefix=prefix)
        return [
            {"key": o["Key"], "url": f"s3://{self.cfg.bucket}/{o['Key']}"}
            for o in resp.get("Contents", [])
            if o["Key"].lower().endswith((".tif", ".tiff"))
        ]

    # ..................................................................

    def build_collection(
        self,
        collection_id: str,
        year: str,
        month: str,
        description: str,
        license: str = "proprietary",
    ) -> Collection:
        first = datetime(int(year), int(month), 1)
        last = datetime(
            int(year), int(month), calendar.monthrange(int(year), int(month))[1]
        )

        col = Collection(
            id=collection_id,
            description=description,
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

    # ..................................................................

    def build_item(
        self,
        cog: dict,
        year: str,
        month: str,
        asset_key: str,
        asset_roles: Sequence[str],
        asset_title: str,
        media_type: str = MediaType.COG,
        extra_asset_fields: dict | None = None,
        derived_from: str | None = None,
    ) -> Item:
        """Return a STAC Item (bounds derived from the COG itself)."""
        with rasterio.open(cog["url"]) as ds:
            wgs_bounds = transform_bounds(ds.crs, "EPSG:4326", *ds.bounds)

        dt = datetime(int(year), int(month), 1)
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
            "title": asset_title,
        }
        if extra_asset_fields:
            asset_dict.update(extra_asset_fields)

        itm.add_asset(asset_key, Asset.from_dict(asset_dict))

        # provenance link
        if derived_from:
            itm.add_link(
                Link(
                    rel="derived_from",
                    href=derived_from,          # ← was “target=…”
                    media_type="application/json",
                )
            )

        return itm

    # ..................................................................

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

    # ------------------------------------------------------------------
    #  High‑level convenience: process one month
    # ------------------------------------------------------------------

    def process_month(
        self,
        year: str,
        month: str,
        prefix: str,
        collection_id: str,
        asset_key: str,
        asset_roles: Sequence[str],
        asset_title: str,
        *,
        extra_asset_fields: dict | None = None,
        derived_from_tpl: str | None = None,
    ) -> None:
        """
        Scan prefix/year/mo, build collection & items, push to pgSTAC.

        Parameters
        ----------
        prefix
            e.g. ``"NICFI Monthly Mosaics"`` or ``"predictions/rf-v1"``.
        asset_key / roles / title
            How the asset should appear in STAC (\"data\", \"pred\", …).
        derived_from_tpl
            Optional string template with ``{item_id}`` placeholder to build a
            provenance link (use for predictions that refer back to source).
        """
        month_str = f"{int(month):02d}"
        year_str = str(year)
        s3_prefix = f"{prefix}/{year_str}/{month_str}"

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
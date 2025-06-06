import yaml
import os
from typing import List, Optional
from sqlalchemy import create_engine, inspect
from ldproxy_api_scaffold.generators.api_service import ApiService
from ldproxy_api_scaffold.generators.sql_provider import SQLProvider
from ldproxy_api_scaffold.generators.tile_provider import TileProvider
from ldproxy_api_scaffold.utils.db import DatabaseClient

class LDProxyConfigGenerator():
    """
    Generates LDProxy-compatible configuration files for service, SQL provider, and tile provider.

    This class connects to a PostgreSQL/PostGIS database, analyzes table structures,
    and produces YAML configuration files required by LDProxy.

    Attributes:
        service_id (str): Identifier used for the LDProxy service.
        schema_name (str): Name of the schema in the database.
        db_conn_str (str): SQLAlchemy-compatible connection string to the database.
        target_tables (List[str], optional): Specific tables to include; if None, all tables in the schema are used.
        api_blocks (List[str], optional): List of enabled API features (e.g., QUERYABLES, CRS, FILTER).
        docker (bool): Flag indicating whether Docker-compatible paths should be used.
    """
    def __init__(self, service_id:str, schema_name:str, db_conn_str:str, target_tables:Optional[List[str]] = None,
                        api_blocks:Optional[List[str]] = None,
                        docker:bool = False):
        self.service_id = service_id
        self.schema_name = schema_name
        self.db_conn_str = db_conn_str
        self.target_tables = target_tables
        self.api_blocks = api_blocks or ["QUERYABLES", "CRS", "FILTER", "TILES", "STYLES", "PROJECTIONS"]
        self.docker = docker

        self.db_client = DatabaseClient(self.db_conn_str, self.schema_name)

        self._init_resources()

    def _init_resources(self):
        """
        Internal method to initialize resources by connecting to the database,
        fetching table metadata, and initializing provider objects.
        """
        if self.target_tables is None:
            self.target_tables = self.db_client.get_schema_tables()

        self.table_config = self.db_client.create_table_config(self.target_tables)

        self.service_obj = ApiService(self.service_id, self.table_config, self.api_blocks)
        self.sql_provider_obj = SQLProvider(self.service_id, force_axis_order="LON_LAT",
                                            table_config=self.table_config,
                                            engine=self.db_client.engine,
                                            db_config=None,
                                            docker=self.docker)
        self.tile_provider_obj = TileProvider(self.service_id, self.table_config)

    def generate_yaml_files(self, export_dir:str):
        """
        Generates and exports YAML files for LDProxy.

        Args:
            export_dir (str): Directory where the YAML files will be saved.
        """
        self.service_obj.create_yaml(export_dir)
        self.sql_provider_obj.create_yaml(export_dir)
        self.tile_provider_obj.create_yaml(export_dir)

    def dispose_engine(self):
        self.db_client.dispose_engine()

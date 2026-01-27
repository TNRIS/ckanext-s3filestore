# encoding: utf-8
import ckan.plugins as plugins
import ckantoolkit as toolkit

import ckanext.s3filestore.uploader
from ckanext.s3filestore.views import resource, uploads
from ckanext.s3filestore.click_commands import upload_resources, upload_assets

import logging
from .uploader import BaseS3Uploader
from ckanext.s3filestore.s3util import delete_prefix, join_s3, delete_matching_uuid
from ckan.types import Context
from typing import Any
from ckan.common import config
import os
import ckan.model as model

log = logging.getLogger(__name__)

class S3FileStorePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IUploader)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IClick)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.IOrganizationController, inherit=True)
    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        # We need to register the following templates dir in order
        # to fix downloading the HTML file instead of previewing when
        # 'webpage_view' is enabled
        toolkit.add_template_directory(config_, 'theme/templates')

    # IConfigurable

    def configure(self, config):
        # Certain config options must exists for the plugin to work. Raise an
        # exception if they're missing.
        missing_config = "{0} is not configured. Please amend your .ini file."
        config_options = (
            'ckanext.s3filestore.aws_bucket_name',
            'ckanext.s3filestore.region_name',
            'ckanext.s3filestore.signature_version'
        )

        if not config.get('ckanext.s3filestore.aws_use_ami_role'):
            config_options += ('ckanext.s3filestore.aws_access_key_id',
                               'ckanext.s3filestore.aws_secret_access_key')

        for option in config_options:
            if not config.get(option, None):
                raise RuntimeError(missing_config.format(option))

        # Check that options actually work, if not exceptions will be raised
        if toolkit.asbool(
                config.get('ckanext.s3filestore.check_access_on_startup',
                           True)):
            ckanext.s3filestore.uploader.BaseS3Uploader().get_s3_bucket(
                config.get('ckanext.s3filestore.aws_bucket_name'))

    # IUploader

    def get_resource_uploader(self, data_dict):
        '''Return an uploader object used to upload resource files.'''
        return ckanext.s3filestore.uploader.S3ResourceUploader(data_dict)

    def get_uploader(self, upload_to, old_filename=None):
        '''Return an uploader object used to upload general files.'''
        return ckanext.s3filestore.uploader.S3Uploader(upload_to,
                                                       old_filename)

    # IResourceController
    # Resource deletion
    def before_resource_delete(
            self, context: Context, resource: dict[str, Any],
            resources: list[dict[str, Any]]) -> None:
        try:
            s3 = BaseS3Uploader()
            storage_path = config.get('ckanext.s3filestore.aws_storage_path', '')
            storage_root = os.path.join(storage_path, 'resources') 
            prefix = join_s3(storage_root, resource['id'])
            delete_prefix(s3, prefix)
        except Exception as e:
            log.warning(f"Resource purge failed: {e}")

    # IOrganizationController
    # Group deletion

    def delete(self, entity: 'model.Group') -> None:
        """
        Called before commit inside group_delete.
        """
        try:
            s3 = BaseS3Uploader()

            storage_path = config.get('ckanext.s3filestore.aws_storage_path', '')

            base_prefix = os.path.join(storage_path, "storage", "uploads", "group")
            uuid_str = entity.name
            if uuid_str: 
                org_dict = toolkit.get_action('organization_show')({}, {'id': uuid_str})
                uuid_val= org_dict['id']
            
            if uuid_val:
                delete_matching_uuid(s3, base_prefix, uuid_val)

        except Exception as e:
            log.warning(
                f"Group/org purge failed for {getattr(entity, 'id', '?')}: {e}"
            )

    # IBlueprint

    def get_blueprint(self):
        blueprints = resource.get_blueprints() +\
                     uploads.get_blueprints()
        return blueprints

    # IClick

    def get_commands(self):
        return [upload_resources, upload_assets]


if toolkit.check_ckan_version(min_version="2.10"):
    S3FileStorePlugin = toolkit.blanket.config_declarations(S3FileStorePlugin)

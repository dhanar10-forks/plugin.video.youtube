# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import os

from .. import logger
from ..compatibility import parse_qsl, quote, to_str, urlencode, urlsplit
from ..constants import (
    PATHS,
    PLAY_FORCE_AUDIO,
    PLAY_PROMPT_QUALITY,
    PLAY_PROMPT_SUBTITLES,
    PLAY_WITH,
    VALUE_FROM_STR,
)
from ..json_store import AccessManager
from ..sql_store import (
    BookmarksList,
    DataCache,
    FeedHistory,
    FunctionCache,
    PlaybackHistory,
    SearchHistory,
    WatchLaterList,
)
from ..utils import current_system_version


class AbstractContext(object):
    _initialized = False
    _addon = None
    _settings = None

    _BOOL_PARAMS = {
        PLAY_FORCE_AUDIO,
        PLAY_PROMPT_SUBTITLES,
        PLAY_PROMPT_QUALITY,
        PLAY_WITH,
        'confirmed',
        'clip',
        'enable',
        'hide_folders',
        'hide_live',
        'hide_playlists',
        'hide_search',
        'incognito',
        'location',
        'logged_in',
        'play',
        'resume',
        'screensaver',
        'strm',
        'window_return',
    }
    _INT_PARAMS = {
        'fanart_type',
        'live',
        'next_page_token',
        'offset',
        'page',
        'refresh',
    }
    _INT_BOOL_PARAMS = {
        'refresh',
    }
    _FLOAT_PARAMS = {
        'end',
        'seek',
        'start',
    }
    _LIST_PARAMS = {
        'channel_ids',
        'playlist_ids',
    }
    _STRING_PARAMS = {
        'api_key',
        'action',
        'addon_id',
        'category_label',
        'channel_id',
        'channel_name',
        'client_id',
        'client_secret',
        'click_tracking',
        'event_type',
        'item',
        'item_id',
        'order',
        'page_token',
        'parent_id',
        'playlist',  # deprecated
        'playlist_id',
        'playlist_name',
        'q',
        'rating',
        'reload_path',
        'search_type',
        'subscription_id',
        'uri',
        'videoid',  # deprecated
        'video_id',
        'video_name',
        'visitor',
    }
    _STRING_BOOL_PARAMS = {
        'reload_path',
    }

    def __init__(self, path='/', params=None, plugin_id=''):
        self._access_manager = None
        self._uuid = None

        self._bookmarks_list = None
        self._data_cache = None
        self._feed_history = None
        self._function_cache = None
        self._playback_history = None
        self._search_history = None
        self._watch_later_list = None

        self._plugin_handle = -1
        self._plugin_id = plugin_id
        self._plugin_name = None
        self._plugin_icon = None
        self._version = 'UNKNOWN'

        self._path = self.create_path(path)
        self._params = params or {}
        self.parse_params(self._params)
        self._uri = self.create_uri(self._path, self._params)

    @staticmethod
    def format_date_short(date_obj, str_format=None):
        raise NotImplementedError()

    @staticmethod
    def format_time(time_obj, str_format=None):
        raise NotImplementedError()

    @staticmethod
    def get_language():
        raise NotImplementedError()

    def get_language_name(self, lang_id=None):
        raise NotImplementedError()

    def get_subtitle_language(self):
        raise NotImplementedError()

    def get_region(self):
        raise NotImplementedError()

    def get_playback_history(self):
        uuid = self.get_uuid()
        if not self._playback_history or self._playback_history.uuid != uuid:
            filepath = (self.get_data_path(), uuid, 'history.sqlite')
            self._playback_history = PlaybackHistory(filepath)
        return self._playback_history

    def get_feed_history(self):
        uuid = self.get_uuid()
        if not self._feed_history or self._feed_history.uuid != uuid:
            filepath = (self.get_data_path(), uuid, 'feeds.sqlite')
            self._feed_history = FeedHistory(filepath)
        return self._feed_history

    def get_data_cache(self):
        uuid = self.get_uuid()
        if not self._data_cache or self._data_cache.uuid != uuid:
            filepath = (self.get_data_path(), uuid, 'data_cache.sqlite')
            self._data_cache = DataCache(
                filepath,
                max_file_size_mb=self.get_settings().cache_size() / 2,
            )
        return self._data_cache

    def get_function_cache(self):
        uuid = self.get_uuid()
        if not self._function_cache or self._function_cache.uuid != uuid:
            filepath = (self.get_data_path(), uuid, 'cache.sqlite')
            self._function_cache = FunctionCache(
                filepath,
                max_file_size_mb=self.get_settings().cache_size() / 2,
            )
        return self._function_cache

    def get_search_history(self):
        uuid = self.get_uuid()
        if not self._search_history or self._search_history.uuid != uuid:
            filepath = (self.get_data_path(), uuid, 'search.sqlite')
            self._search_history = SearchHistory(
                filepath,
                max_item_count=self.get_settings().get_search_history_size(),
            )
        return self._search_history

    def get_bookmarks_list(self):
        uuid = self.get_uuid()
        if not self._bookmarks_list or self._bookmarks_list.uuid != uuid:
            filepath = (self.get_data_path(), uuid, 'bookmarks.sqlite')
            self._bookmarks_list = BookmarksList(filepath)
        return self._bookmarks_list

    def get_watch_later_list(self):
        uuid = self.get_uuid()
        if not self._watch_later_list or self._watch_later_list.uuid != uuid:
            filepath = (self.get_data_path(), uuid, 'watch_later.sqlite')
            self._watch_later_list = WatchLaterList(filepath)
        return self._watch_later_list

    def get_uuid(self):
        uuid = self._uuid
        if uuid:
            return uuid
        return self.reload_access_manager(get_uuid=True)

    def get_access_manager(self):
        access_manager = self._access_manager
        if access_manager:
            return access_manager
        return self.reload_access_manager()

    def reload_access_manager(self, get_uuid=False):
        access_manager = AccessManager(self)
        self._access_manager = access_manager
        uuid = access_manager.get_current_user_id()
        self._uuid = uuid
        if get_uuid:
            return uuid
        return access_manager

    def get_video_playlist(self):
        raise NotImplementedError()

    def get_audio_playlist(self):
        raise NotImplementedError()

    def get_video_player(self):
        raise NotImplementedError()

    def get_audio_player(self):
        raise NotImplementedError()

    def get_ui(self):
        raise NotImplementedError()

    @staticmethod
    def get_system_version():
        return current_system_version

    def create_uri(self, path=None, params=None):
        if isinstance(path, (list, tuple)):
            uri = self.create_path(*path, is_uri=True)
        elif path:
            uri = path
        else:
            uri = '/'

        uri = self._plugin_id.join(('plugin://', uri))

        if params:
            uri = '?'.join((uri, urlencode(params)))

        return uri

    @staticmethod
    def create_path(*args, **kwargs):
        path = '/'.join([
            part
            for part in [
                str(arg).strip('/').replace('\\', '/').replace('//', '/')
                for arg in args
            ] if part
        ])
        if path:
            path = path.join(('/', '/'))
        else:
            return '/'

        if kwargs.get('is_uri'):
            return quote(path)
        return path

    def get_path(self):
        return self._path

    def set_path(self, *path, **kwargs):
        if kwargs.get('force'):
            self._path = path[0]
        else:
            self._path = self.create_path(*path)

    def get_params(self):
        return self._params

    def get_param(self, name, default=None):
        return self._params.get(name, default)

    def parse_uri(self, uri):
        uri = urlsplit(uri)
        path = uri.path
        params = self.parse_params(dict(parse_qsl(uri.query)), update=False)
        return path, params

    def parse_params(self, params, update=True):
        to_delete = []
        output = self._params if update else {}

        for param, value in params.items():
            try:
                if param in self._BOOL_PARAMS:
                    parsed_value = VALUE_FROM_STR.get(str(value).lower(), False)
                elif param in self._INT_PARAMS:
                    parsed_value = None
                    if param in self._INT_BOOL_PARAMS:
                        parsed_value = VALUE_FROM_STR.get(str(value).lower())
                    if parsed_value is None:
                        parsed_value = int(value)
                    else:
                        parsed_value = int(parsed_value)
                elif param in self._FLOAT_PARAMS:
                    parsed_value = float(value)
                elif param in self._LIST_PARAMS:
                    parsed_value = [
                        val for val in value.split(',') if val
                    ]
                elif param in self._STRING_PARAMS:
                    parsed_value = to_str(value)
                    if param in self._STRING_BOOL_PARAMS:
                        parsed_value = VALUE_FROM_STR.get(
                            parsed_value.lower(), parsed_value
                        )
                    # process and translate deprecated parameters
                    elif param == 'action':
                        if parsed_value in {'play_all', 'play_video'}:
                            to_delete.append(param)
                            self.set_path(PATHS.PLAY)
                            continue
                    elif param == 'videoid':
                        to_delete.append(param)
                        param = 'video_id'
                    elif params == 'playlist':
                        to_delete.append(param)
                        param = 'playlist_id'
                else:
                    self.log_debug('Unknown parameter - |{0}: {1}|'.format(
                        param, value
                    ))
                    to_delete.append(param)
                    continue
            except (TypeError, ValueError):
                self.log_error('Invalid parameter value - |{0}: {1}|'.format(
                    param, value
                ))
                to_delete.append(param)
                continue

            output[param] = parsed_value

        for param in to_delete:
            del params[param]

        return output

    def set_param(self, name, value):
        self.parse_params({name: value})

    def get_data_path(self):
        """
        Returns the path for read/write access of files
        :return:
        """
        raise NotImplementedError()

    def get_addon_path(self):
        raise NotImplementedError()

    def get_icon(self):
        return self._plugin_icon

    def get_fanart(self):
        return self.create_resource_path('media/fanart.jpg')

    def create_resource_path(self, *args):
        path_comps = []
        for arg in args:
            path_comps.extend(arg.split('/'))
        path = os.path.join(self.get_addon_path(), 'resources', *path_comps)
        return path

    def get_uri(self):
        return self._uri

    def get_name(self):
        return self._plugin_name

    def get_version(self):
        return self._version

    def get_id(self):
        return self._plugin_id

    def get_handle(self):
        return self._plugin_handle

    def get_settings(self, refresh=False):
        raise NotImplementedError()

    def localize(self, text_id, default_text=None):
        raise NotImplementedError()

    def set_content(self, content_type, sub_type=None, category_label=None):
        raise NotImplementedError()

    def add_sort_method(self, *sort_methods):
        raise NotImplementedError()

    def log(self, text, log_level=logger.NOTICE):
        logger.log(text, log_level, self.get_id())

    def log_warning(self, text):
        self.log(text, logger.WARNING)

    def log_error(self, text):
        self.log(text, logger.ERROR)

    def log_notice(self, text):
        self.log(text, logger.NOTICE)

    def log_debug(self, text):
        self.log(text, logger.DEBUG)

    def log_info(self, text):
        self.log(text, logger.INFO)

    def clone(self, new_path=None, new_params=None):
        raise NotImplementedError()

    @staticmethod
    def execute(command):
        raise NotImplementedError()

    @staticmethod
    def sleep(timeout=None):
        raise NotImplementedError()

    @staticmethod
    def get_infobool(name):
        raise NotImplementedError()

    @staticmethod
    def get_infolabel(name):
        raise NotImplementedError()

    @staticmethod
    def get_listitem_property(detail_name):
        raise NotImplementedError()

    @staticmethod
    def get_listitem_info(detail_name):
        raise NotImplementedError()

    def tear_down(self):
        pass

    def wakeup(self):
        raise NotImplementedError()

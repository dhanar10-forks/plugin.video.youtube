# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import threading
import xml.etree.ElementTree as ET
from copy import deepcopy
from functools import partial
from itertools import chain, islice
from random import randint

from .login_client import LoginClient
from ..helper.video_info import VideoInfo
from ..youtube_exceptions import InvalidJSON, YouTubeException
from ...kodion.compatibility import cpu_count, string_type, to_str
from ...kodion.utils import (
    current_system_version,
    datetime_parser,
    strip_html_from_text,
    to_unicode,
)


class YouTube(LoginClient):
    CLIENTS = {
        1: {
            'url': 'https://www.youtube.com/youtubei/v1/{_endpoint}',
            'method': None,
            'json': {
                'context': {
                    'client': {
                        'clientName': 'WEB',
                        'clientVersion': '2.20240304.00.00',
                    },
                },
            },
            'headers': {
                'Host': 'www.youtube.com',
            },
            'params': {
                'key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',
            },
        },
        3: {
            'url': 'https://www.googleapis.com/youtube/v3/{_endpoint}',
            'method': None,
            'headers': {
                'Host': 'www.googleapis.com',
            },
        },
        'tv': {
            'url': 'https://www.youtube.com/youtubei/v1/{_endpoint}',
            'method': None,
            'json': {
                'context': {
                    'client': {
                        'clientName': 'TVHTML5',
                        'clientVersion': '7.20240304.10.00',
                    },
                },
            },
            'headers': {
                'Host': 'www.youtube.com',
            },
            'params': {
                'key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',
            },
        },
        'tv_embed': {
            'url': 'https://www.youtube.com/youtubei/v1/{_endpoint}',
            'method': None,
            'json': {
                'context': {
                    'client': {
                        'clientName': 'TVHTML5_SIMPLY_EMBEDDED_PLAYER',
                        'clientVersion': '2.0',
                    },
                },
            },
            'headers': {
                'Host': 'www.youtube.com',
            },
            'params': {
                'key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',
            },
        },
        '_common': {
            '_access_token': None,
            'json': {
                'context': {
                    'client': {
                        'gl': None,
                        'hl': None,
                        'utcOffsetMinutes': 0,
                    },
                    'request': {
                        'internalExperimentFlags': [],
                        'useSsl': True,
                    }
                },
                'user': {
                    'lockedSafetyMode': False
                },
            },
            'headers': {
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Authorization': 'Bearer {_access_token}',
                'DNT': '1',
                'User-Agent': ('Mozilla/5.0 (Linux; Android 10; SM-G981B)'
                               ' AppleWebKit/537.36 (KHTML, like Gecko)'
                               ' Chrome/80.0.3987.162 Mobile Safari/537.36'),
            },
            'params': {
                'key': None,
                'prettyPrint': 'false'
            },
        },
    }

    def __init__(self, context, **kwargs):
        self._context = context
        if 'items_per_page' in kwargs:
            self._max_results = kwargs.pop('items_per_page')

        super(YouTube, self).__init__(**kwargs)

    def get_max_results(self):
        return self._max_results

    def get_language(self):
        return self._language

    def get_region(self):
        return self._region

    def update_watch_history(self, context, video_id, url, status=None):
        if status is None:
            cmt = st = et = state = None
        else:
            cmt, st, et, state = status

        context.log_debug('Playback reported [{video_id}]:'
                          ' current time={cmt},'
                          ' segment start={st},'
                          ' segment end={et},'
                          ' state={state}'.format(
            video_id=video_id, cmt=cmt, st=st, et=et, state=state
        ))

        headers = {
            'Host': 's.youtube.com',
            'Connection': 'keep-alive',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Referer': 'https://www.youtube.com/watch?v={0}'.format(video_id),
            'User-Agent': ('Mozilla/5.0 (Linux; Android 10; SM-G981B)'
                           ' AppleWebKit/537.36 (KHTML, like Gecko)'
                           ' Chrome/80.0.3987.162 Mobile Safari/537.36'),
        }
        params = {
            'docid': video_id,
            'referrer': 'https://accounts.google.com/',
            'ns': 'yt',
            'el': 'detailpage',
            'ver': '2',
            'fs': '0',
            'volume': '100',
            'muted': '0',
        }
        if cmt is not None:
            params['cmt'] = format(cmt, '.3f')
        if st is not None:
            params['st'] = format(st, '.3f')
        if et is not None:
            params['et'] = format(et, '.3f')
        if state is not None:
            params['state'] = state
        if self._access_token:
            params['access_token'] = self._access_token

        self.request(url, params=params, headers=headers,
                     error_msg='Failed to update watch history')

    def get_video_streams(self, context, video_id):
        video_info = VideoInfo(context, access_token=self._access_token_tv,
                               language=self._language)

        video_streams = video_info.load_stream_infos(video_id)

        # update title
        for video_stream in video_streams:
            title = '%s (%s)' % (
                context.get_ui().bold(video_stream['title']),
                video_stream['container']
            )

            if 'audio' in video_stream and 'video' in video_stream:
                if (video_stream['audio']['bitrate'] > 0
                        and video_stream['video']['codec']
                        and video_stream['audio']['codec']):
                    title = '%s (%s; %s / %s@%d)' % (
                        context.get_ui().bold(video_stream['title']),
                        video_stream['container'],
                        video_stream['video']['codec'],
                        video_stream['audio']['codec'],
                        video_stream['audio']['bitrate']
                    )

                elif (video_stream['video']['codec']
                      and video_stream['audio']['codec']):
                    title = '%s (%s; %s / %s)' % (
                        context.get_ui().bold(video_stream['title']),
                        video_stream['container'],
                        video_stream['video']['codec'],
                        video_stream['audio']['codec']
                    )
            elif 'audio' in video_stream and 'video' not in video_stream:
                if (video_stream['audio']['codec']
                        and video_stream['audio']['bitrate'] > 0):
                    title = '%s (%s; %s@%d)' % (
                        context.get_ui().bold(video_stream['title']),
                        video_stream['container'],
                        video_stream['audio']['codec'],
                        video_stream['audio']['bitrate']
                    )

            elif 'audio' in video_stream or 'video' in video_stream:
                codec = video_stream.get('audio', {}).get('codec')
                if not codec:
                    codec = video_stream.get('video', {}).get('codec')
                if codec:
                    title = '%s (%s; %s)' % (
                        context.get_ui().bold(video_stream['title']),
                        video_stream['container'],
                        codec
                    )

            video_stream['title'] = title

        return video_streams

    def remove_playlist(self, playlist_id, **kwargs):
        params = {'id': playlist_id,
                  'mine': 'true'}
        return self.api_request(method='DELETE',
                                path='playlists',
                                params=params,
                                no_content=True,
                                **kwargs)

    def get_supported_languages(self, language=None, **kwargs):
        _language = language
        if not _language:
            _language = self._language
        _language = _language.replace('-', '_')
        params = {'part': 'snippet',
                  'hl': _language}
        return self.api_request(method='GET',
                                path='i18nLanguages',
                                params=params,
                                **kwargs)

    def get_supported_regions(self, language=None, **kwargs):
        _language = language
        if not _language:
            _language = self._language
        _language = _language.replace('-', '_')
        params = {'part': 'snippet',
                  'hl': _language}
        return self.api_request(method='GET',
                                path='i18nRegions',
                                params=params,
                                **kwargs)

    def rename_playlist(self,
                        playlist_id,
                        new_title,
                        privacy_status='private',
                        **kwargs):
        params = {'part': 'snippet,id,status'}
        post_data = {'kind': 'youtube#playlist',
                     'id': playlist_id,
                     'snippet': {'title': new_title},
                     'status': {'privacyStatus': privacy_status}}
        return self.api_request(method='PUT',
                                path='playlists',
                                params=params,
                                post_data=post_data,
                                **kwargs)

    def create_playlist(self, title, privacy_status='private', **kwargs):
        params = {'part': 'snippet,status'}
        post_data = {'kind': 'youtube#playlist',
                     'snippet': {'title': title},
                     'status': {'privacyStatus': privacy_status}}
        return self.api_request(method='POST',
                                path='playlists',
                                params=params,
                                post_data=post_data,
                                **kwargs)

    def get_video_rating(self, video_id, **kwargs):
        if not isinstance(video_id, string_type):
            video_id = ','.join(video_id)

        params = {'id': video_id}
        return self.api_request(method='GET',
                                path='videos/getRating',
                                params=params,
                                **kwargs)

    def rate_video(self, video_id, rating='like', **kwargs):
        """
        Rate a video
        :param video_id: if of the video
        :param rating: [like|dislike|none]
        :return:
        """
        params = {'id': video_id,
                  'rating': rating}
        return self.api_request(method='POST',
                                path='videos/rate',
                                params=params,
                                no_content=True,
                                **kwargs)

    def add_video_to_playlist(self, playlist_id, video_id, **kwargs):
        params = {'part': 'snippet',
                  'mine': 'true'}
        post_data = {'kind': 'youtube#playlistItem',
                     'snippet': {'playlistId': playlist_id,
                                 'resourceId': {'kind': 'youtube#video',
                                                'videoId': video_id}}}
        return self.api_request(method='POST',
                                path='playlistItems',
                                params=params,
                                post_data=post_data,
                                **kwargs)

    # noinspection PyUnusedLocal
    def remove_video_from_playlist(self,
                                   playlist_id,
                                   playlist_item_id,
                                   **kwargs):
        params = {'id': playlist_item_id}
        return self.api_request(method='DELETE',
                                path='playlistItems',
                                params=params,
                                no_content=True,
                                **kwargs)

    def unsubscribe(self, subscription_id, **kwargs):
        params = {'id': subscription_id}
        return self.api_request(method='DELETE',
                                path='subscriptions',
                                params=params,
                                no_content=True,
                                **kwargs)

    def unsubscribe_channel(self, channel_id, **kwargs):
        post_data = {'channelIds': [channel_id]}
        return self.api_request(version=1,
                                method='POST',
                                path='subscription/unsubscribe',
                                post_data=post_data,
                                **kwargs)

    def subscribe(self, channel_id, **kwargs):
        params = {'part': 'snippet'}
        post_data = {'kind': 'youtube#subscription',
                     'snippet': {'resourceId': {'kind': 'youtube#channel',
                                                'channelId': channel_id}}}
        return self.api_request(method='POST',
                                path='subscriptions',
                                params=params,
                                post_data=post_data,
                                **kwargs)

    def get_subscription(self,
                         channel_id,
                         order='alphabetical',
                         page_token='',
                         **kwargs):
        """

        :param channel_id: [channel-id|'mine']
        :param order: ['alphabetical'|'relevance'|'unread']
        :param page_token:
        :return:
        """
        params = {'part': 'snippet',
                  'maxResults': str(self._max_results),
                  'order': order}
        if channel_id == 'mine':
            params['mine'] = 'true'
        else:
            params['channelId'] = channel_id
        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET',
                                path='subscriptions',
                                params=params,
                                **kwargs)

    def get_guide_category(self, guide_category_id, page_token='', **kwargs):
        params = {'part': 'snippet,contentDetails,brandingSettings',
                  'maxResults': str(self._max_results),
                  'categoryId': guide_category_id,
                  'regionCode': self._region,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token
        return self.api_request(method='GET',
                                path='channels',
                                params=params,
                                **kwargs)

    def get_guide_categories(self, page_token='', **kwargs):
        params = {'part': 'snippet',
                  'maxResults': str(self._max_results),
                  'regionCode': self._region,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET',
                                path='guideCategories',
                                params=params,
                                **kwargs)

    def get_trending_videos(self, page_token='', **kwargs):
        params = {'part': 'snippet,status',
                  'maxResults': str(self._max_results),
                  'regionCode': self._region,
                  'hl': self._language,
                  'chart': 'mostPopular'}
        if page_token:
            params['pageToken'] = page_token
        return self.api_request(method='GET',
                                path='videos',
                                params=params,
                                **kwargs)

    def get_video_category(self, video_category_id, page_token='', **kwargs):
        params = {'part': 'snippet,contentDetails,status',
                  'maxResults': str(self._max_results),
                  'videoCategoryId': video_category_id,
                  'chart': 'mostPopular',
                  'regionCode': self._region,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token
        return self.api_request(method='GET',
                                path='videos',
                                params=params,
                                **kwargs)

    def get_video_categories(self, page_token='', **kwargs):
        params = {'part': 'snippet',
                  'maxResults': str(self._max_results),
                  'regionCode': self._region,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET',
                                path='videoCategories',
                                params=params,
                                **kwargs)

    def get_recommended_for_home(self,
                                 visitor='',
                                 page_token='',
                                 click_tracking=''):
        post_data = {'browseId': 'FEwhat_to_watch'}
        if page_token:
            post_data['continuation'] = page_token
        if click_tracking or visitor:
            context = {}
            if click_tracking:
                context['clickTracking'] = {
                    'clickTrackingParams': click_tracking,
                }
            if visitor:
                context['client'] = {
                    'visitorData': visitor,
                }
            post_data['context'] = context

        result = self.api_request(version=1,
                                  method='POST',
                                  path='browse',
                                  post_data=post_data)
        if not result:
            return None

        recommended_videos = self.json_traverse(
            result,
            path=(
                     (
                         (
                             'onResponseReceivedEndpoints',
                             'onResponseReceivedActions',
                         ),
                         0,
                         'appendContinuationItemsAction',
                         'continuationItems',
                     ) if page_token else (
                         'contents',
                         'twoColumnBrowseResultsRenderer',
                         'tabs',
                         0,
                         'tabRenderer',
                         'content',
                         'richGridRenderer',
                         'contents',
                     )
                 ) + (
                     slice(None),
                     (
                         (
                             'richItemRenderer',
                             'content',
                             'videoRenderer',
                             # 'videoId',
                         ),
                         (
                             'richSectionRenderer',
                             'content',
                             'richShelfRenderer',
                             'contents',
                             slice(None),
                             'richItemRenderer',
                             'content',
                             (
                                 'videoRenderer',
                                 'reelItemRenderer'
                             ),
                             # 'videoId',
                         ),
                         (
                             'continuationItemRenderer',
                             'continuationEndpoint',
                         ),
                     ),
                 )
        )
        if not recommended_videos:
            return None

        v3_response = {
            'kind': 'youtube#activityListResponse',
            'items': [
                {
                    'kind': 'youtube#video',
                    'id': video['videoId'],
                    '_partial': True,
                    'snippet': {
                        'title': self.json_traverse(video, (
                            ('title', 'runs', 0, 'text'),
                            ('headline', 'simpleText'),
                        )),
                        'thumbnails': video['thumbnail']['thumbnails'],
                        'channelId': self.json_traverse(video, (
                            ('longBylineText', 'shortBylineText'),
                            'runs',
                            0,
                            'navigationEndpoint',
                            'browseEndpoint',
                            'browseId',
                        )),
                    }
                }
                for videos in recommended_videos
                for video in
                (videos if isinstance(videos, list) else (videos,))
                if video and 'videoId' in video
            ]
        }

        last_item = recommended_videos[-1]
        if last_item and 'continuationCommand' in last_item:
            if 'clickTrackingParams' in last_item:
                v3_response['clickTracking'] = last_item['clickTrackingParams']
            token = last_item['continuationCommand'].get('token')
            if token:
                v3_response['nextPageToken'] = token
            visitor = self.json_traverse(result, (
                'responseContext',
                'visitorData',
            )) or visitor
            if visitor:
                v3_response['visitorData'] = visitor

        if not v3_response['items']:
            v3_response = None
        return v3_response

    def get_related_for_home(self, page_token='', refresh=False):
        """
        YouTube has deprecated this API, so we use history and related items to
        form a recommended set.
        We cache aggressively because searches can be slow.
        Note this is a naive implementation and can be refined a lot more.
        """

        payload = {
            'kind': 'youtube#activityListResponse',
            'items': []
        }

        # Related videos are retrieved for the following num_items from history
        num_items = 10
        local_history = self._context.get_settings().use_local_history()
        history_id = self._context.get_access_manager().get_watch_history_id()
        if not history_id:
            if local_history:
                history = self._context.get_playback_history()
                video_ids = history.get_items(limit=num_items)
            else:
                return payload
        else:
            history = self.get_playlist_items(history_id, max_results=num_items)
            if history and 'items' in history:
                history_items = history['items'] or []
                video_ids = []
            else:
                return payload

            for item in history_items:
                try:
                    video_ids.append(item['snippet']['resourceId']['videoId'])
                except KeyError:
                    continue

        # Fetch existing list of items, if any
        data_cache = self._context.get_data_cache()
        cache_items_key = 'get-activities-home-items-v2'
        if refresh:
            cached = []
        else:
            cached = data_cache.get_item(cache_items_key) or []

        # Increase value to recursively retrieve recommendations for the first
        # recommended video, up to the set maximum recursion depth
        max_depth = 2
        items_per_page = self._max_results
        diversity_limits = items_per_page // (num_items * max_depth)
        items = [[] for _ in range(max_depth * len(video_ids))]
        counts = {
            '_counter': 0,
            '_pages': {},
            '_related': {},
        }

        def index_items(items, index,
                        item_store=None,
                        original_ids=None,
                        group=None,
                        depth=1,
                        original_related=None,
                        original_channel=None):
            if original_ids is not None:
                original_ids = list(original_ids)

            running = 0
            threads = []

            for idx, item in enumerate(items):
                if original_related is not None:
                    related = item['_related_video_id'] = original_related
                else:
                    related = item['_related_video_id']
                if original_channel is not None:
                    channel = item['_related_channel_id'] = original_channel
                else:
                    channel = item['_related_channel_id']
                video_id = item['id']

                index['_related'].setdefault(related, 0)
                index['_related'][related] += 1

                if video_id in index:
                    item_count = index[video_id]
                    item_count['_related'].setdefault(related, 0)
                    item_count['_related'][related] += 1
                    item_count['_channels'].setdefault(channel, 0)
                    item_count['_channels'][channel] += 1
                    continue

                index[video_id] = {
                    '_related': {related: 1},
                    '_channels': {channel: 1}
                }

                if item_store is None:
                    if original_ids and related not in original_ids:
                        items[idx] = None
                    continue

                if group is not None:
                    pass
                elif original_ids and related in original_ids:
                    group = max_depth * original_ids.index(related)
                else:
                    group = 0

                num_stored = len(item_store[group])
                item['_order'] = items_per_page * group + num_stored
                item_store[group].append(item)

                if num_stored or depth <= 1:
                    continue

                running += 1
                thread = threading.Thread(
                    target=threaded_get_related,
                    args=(video_id, index_items, counts),
                    kwargs={'item_store': item_store,
                            'group': (group + 1),
                            'depth': (depth - 1),
                            'original_related': related,
                            'original_channel': channel},
                )
                thread.daemon = True
                threads.append(thread)
                thread.start()

            while running:
                for thread in threads:
                    thread.join(5)
                    if not thread.is_alive():
                        running -= 1

        index_items(cached, counts, original_ids=video_ids)

        # Fetch related videos. Use threads for faster execution.
        def threaded_get_related(video_id, func, *args, **kwargs):
            related = self.get_related_videos(video_id,
                                              max_results=items_per_page)
            if related and 'items' in related:
                func(related['items'][:items_per_page], *args, **kwargs)

        running = 0
        threads = []
        candidates = []
        for video_id in video_ids:
            if video_id in counts['_related']:
                continue
            running += 1
            thread = threading.Thread(
                target=threaded_get_related,
                args=(video_id, candidates.extend),
            )
            thread.daemon = True
            threads.append(thread)
            thread.start()

        while running:
            for thread in threads:
                thread.join(5)
                if not thread.is_alive():
                    running -= 1

        num_items = items_per_page * num_items * max_depth
        index_items(candidates[:num_items], counts,
                    item_store=items,
                    original_ids=video_ids,
                    depth=max_depth)

        # Truncate items to keep it manageable, and cache
        items = list(chain.from_iterable(items))
        counts['_counter'] = len(items)
        remaining = num_items - counts['_counter']
        if remaining > 0:
            items.extend(islice(filter(None, cached), remaining))
        elif remaining:
            items = items[:num_items]

        # Finally sort items per page by rank and date for a better distribution
        def rank_and_sort(item):
            if '_order' not in item:
                counts['_counter'] += 1
                item['_order'] = counts['_counter']

            page = 1 + item['_order'] // (items_per_page * max_depth)
            page_count = counts['_pages'].setdefault(page, {'_counter': 0})
            while page_count['_counter'] < items_per_page and page > 1:
                page -= 1
                page_count = counts['_pages'].setdefault(page, {'_counter': 0})

            related_video = item['_related_video_id']
            related_channel = item['_related_channel_id']
            channel_id = item.get('snippet', {}).get('channelId')
            """
            # Video channel and related channel can be the same which can double
            # up the channel count. Checking for this allows more similar videos
            # in the recommendation, ignoring it allows for more variety.
            # Currently prefer not to check for this to allow more variety.
            if channel_id == related_channel:
                channel_id = None
            """
            while (page_count['_counter'] >= items_per_page
                   or (related_video in page_count
                       and page_count[related_video] >= diversity_limits)
                   or (related_channel and related_channel in page_count
                       and page_count[related_channel] >= diversity_limits)
                   or (channel_id and channel_id in page_count
                       and page_count[channel_id] >= diversity_limits)):
                page += 1
                page_count = counts['_pages'].setdefault(page, {'_counter': 0})

            page_count.setdefault(related_video, 0)
            page_count[related_video] += 1
            if related_channel:
                page_count.setdefault(related_channel, 0)
                page_count[related_channel] += 1
            if channel_id:
                page_count.setdefault(channel_id, 0)
                page_count[channel_id] += 1
            page_count['_counter'] += 1
            item['_page'] = page

            item_count = counts[item['id']]
            item['_rank'] = (2 * sum(item_count['_channels'].values())
                             + sum(item_count['_related'].values()))

            return (
                -item['_page'],
                item['_rank'],
                -randint(0, item['_order'])
            )

        items.sort(key=rank_and_sort, reverse=True)

        # Finalize result
        payload['items'] = items
        """
        # TODO:
        # Enable pagination
        payload['pageInfo'] = {
            'resultsPerPage': 50,
            'totalResults': len(sorted_items)
        }
        """

        # Update cache
        data_cache.set_item(cache_items_key, items)

        return payload

    def get_activities(self, channel_id, page_token='', **kwargs):
        params = {'part': 'snippet,contentDetails',
                  'maxResults': str(self._max_results),
                  'regionCode': self._region,
                  'hl': self._language}

        if channel_id == 'home':
            params['home'] = 'true'
        elif channel_id == 'mine':
            params['mine'] = 'true'
        else:
            params['channelId'] = channel_id
        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET',
                                path='activities',
                                params=params,
                                **kwargs)

    def get_channel_sections(self, channel_id, **kwargs):
        params = {'part': 'snippet,contentDetails',
                  'regionCode': self._region,
                  'hl': self._language}
        if channel_id == 'mine':
            params['mine'] = 'true'
        else:
            params['channelId'] = channel_id
        return self.api_request(method='GET',
                                path='channelSections',
                                params=params,
                                **kwargs)

    def get_playlists_of_channel(self, channel_id, page_token='', **kwargs):
        params = {'part': 'snippet',
                  'maxResults': str(self._max_results)}
        if channel_id != 'mine':
            params['channelId'] = channel_id
        else:
            params['mine'] = 'true'
        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET',
                                path='playlists',
                                params=params,
                                **kwargs)

    def get_playlist_item_id_of_video_id(self,
                                         playlist_id,
                                         video_id,
                                         page_token=''):
        json_data = self.get_playlist_items(
            playlist_id=playlist_id,
            page_token=page_token,
            max_results=50,
        )
        if not json_data:
            return None

        for item in json_data.get('items', []):
            if (item.get('snippet', {}).get('resourceId', {}).get('videoId')
                    == video_id):
                return item['id']

        next_page_token = json_data.get('nextPageToken')
        if next_page_token:
            return self.get_playlist_item_id_of_video_id(
                playlist_id=playlist_id,
                video_id=video_id,
                page_token=next_page_token,
            )
        return None

    def get_playlist_items(self,
                           playlist_id,
                           page_token='',
                           max_results=None,
                           **kwargs):
        # prepare params
        if max_results is None:
            max_results = self._max_results
        params = {'part': 'snippet',
                  'maxResults': str(max_results),
                  'playlistId': playlist_id}
        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET',
                                path='playlistItems',
                                params=params,
                                **kwargs)

    def get_channel_by_identifier(self,
                                  identifier,
                                  mine=False,
                                  handle=False,
                                  **kwargs):
        """
        Returns a collection of zero or more channel resources that match the request criteria.
        :param str identifier: channel username to retrieve channel ID for
        :param bool mine: treat identifier as request for authenticated user
        :param bool handle: treat identifier as request for handle
        :return:
        """
        params = {'part': 'id'}
        if mine or identifier == 'mine':
            params['mine'] = True
        elif handle or identifier.startswith('@'):
            params['forHandle'] = identifier
        else:
            params['forUsername'] = identifier

        return self.api_request(method='GET',
                                path='channels',
                                params=params,
                                **kwargs)

    def get_channels(self, channel_id, **kwargs):
        """
        Returns a collection of zero or more channel resources that match the request criteria.
        :param channel_id: list or comma-separated list of the YouTube channel ID(s)
        :return:
        """
        if not isinstance(channel_id, string_type):
            channel_id = ','.join(channel_id)

        params = {'part': 'snippet,contentDetails,brandingSettings'}
        if channel_id != 'mine':
            params['id'] = channel_id
        else:
            params['mine'] = 'true'
        return self.api_request(method='GET',
                                path='channels',
                                params=params,
                                **kwargs)

    def get_disliked_videos(self, page_token='', **kwargs):
        # prepare page token
        if not page_token:
            page_token = ''

        # prepare params
        params = {'part': 'snippet,status',
                  'myRating': 'dislike',
                  'maxResults': str(self._max_results)}
        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET',
                                path='videos',
                                params=params,
                                **kwargs)

    def get_videos(self, video_id, live_details=False, **kwargs):
        """
        Returns a list of videos that match the API request parameters
        :param video_id: list of video ids
        :param live_details: also retrieve liveStreamingDetails
        :return:
        """
        if not isinstance(video_id, string_type):
            video_id = ','.join(video_id)

        parts = ['snippet', 'contentDetails', 'status', 'statistics']
        if live_details:
            parts.append('liveStreamingDetails')

        params = {'part': ','.join(parts),
                  'id': video_id}
        return self.api_request(method='GET',
                                path='videos',
                                params=params,
                                **kwargs)

    def get_playlists(self, playlist_id, **kwargs):
        if not isinstance(playlist_id, string_type):
            playlist_id = ','.join(playlist_id)

        params = {'part': 'snippet,contentDetails',
                  'id': playlist_id}
        return self.api_request(method='GET',
                                path='playlists',
                                params=params,
                                **kwargs)

    def get_live_events(self,
                        event_type='live',
                        order='date',
                        page_token='',
                        location=False,
                        after=None,
                        **kwargs):
        """
        :param event_type: one of: 'live', 'completed', 'upcoming'
        :param order: one of: 'date', 'rating', 'relevance', 'title', 'videoCount', 'viewCount'
        :param page_token:
        :param location: bool, use geolocation
        :param after: str, RFC 3339 formatted date-time value (1970-01-01T00:00:00Z)
        :return:
        """
        # prepare page token
        if not page_token:
            page_token = ''

        # prepare params
        params = {'part': 'snippet',
                  'type': 'video',
                  'order': order,
                  'eventType': event_type,
                  'regionCode': self._region,
                  'hl': self._language,
                  'relevanceLanguage': self._language,
                  'maxResults': str(self._max_results)}

        if location:
            settings = self._context.get_settings()
            location = settings.get_location()
            if location:
                params['location'] = location
                params['locationRadius'] = settings.get_location_radius()

        if page_token:
            params['pageToken'] = page_token

        if after:
            params['publishedAfter'] = after

        return self.api_request(method='GET',
                                path='search',
                                params=params,
                                **kwargs)

    def get_related_videos(self,
                           video_id,
                           page_token='',
                           max_results=0,
                           offset=0,
                           retry=0,
                           **kwargs):
        max_results = self._max_results if max_results <= 0 else max_results

        post_data = {'videoId': video_id}
        if page_token:
            post_data['continuation'] = page_token

        result = self.api_request(version=('tv' if retry == 1 else
                                           'tv_embed' if retry == 2 else 1),
                                  method='POST',
                                  path='next',
                                  post_data=post_data,
                                  no_login=True)
        if not result:
            return None

        related_videos = self.json_traverse(result, path=(
            (
                'onResponseReceivedEndpoints',
                0,
                'appendContinuationItemsAction',
                'continuationItems',
            ) if page_token else (
                'contents',
                'singleColumnWatchNextResults',
                'pivot',
                'pivot',
                'contents',
                slice(0, None, None),
                'pivotShelfRenderer',
                'content',
                'pivotHorizontalListRenderer',
                'items',
            ) if retry == 1 else (
               'contents',
               'singleColumnWatchNextResults',
               'results',
               'results',
               'contents',
               2,
               'shelfRenderer',
               'content',
               'horizontalListRenderer',
               'items',
            ) if retry == 2 else (
                'contents',
                'twoColumnWatchNextResults',
                'secondaryResults',
                'secondaryResults',
                'results',
            )
        ) + (
            slice(offset, None, None),
            (
                'pivotVideoRenderer',
                # 'videoId',
            ) if retry == 1 else (
                'compactVideoRenderer',
                # 'videoId',
            ) if retry == 2 else (
                (
                    'compactVideoRenderer',
                    # 'videoId',
                ),
                (
                    'continuationItemRenderer',
                    'continuationEndpoint',
                    'continuationCommand',
                    # 'token',
                ),
            ),
        ), default=[])
        if not related_videos or not any(related_videos):
            return {} if retry > 1 else self.get_related_videos(
                video_id,
                page_token=page_token,
                max_results=max_results,
                retry=(retry + 1),
                **kwargs
            )

        channel_id = self.json_traverse(result, path=(
            'contents',
            'singleColumnWatchNextResults',
            'results',
            'results',
            'contents',
            1,
            'itemSectionRenderer',
            'contents',
            0,
            'videoOwnerRenderer',
            'navigationEndpoint',
            'browseEndpoint',
            'browseId'
        ) if retry else (
            'contents',
            'twoColumnWatchNextResults',
            'results',
            'results',
            'contents',
            1,
            'videoSecondaryInfoRenderer',
            'owner',
            'videoOwnerRenderer',
            'title',
            'runs',
            0,
            'navigationEndpoint',
            'browseEndpoint',
            'browseId'
        ))

        if retry == 1:
            related_videos = chain.from_iterable(related_videos)

        items = [{
            'kind': 'youtube#video',
            'id': video['videoId'],
            '_related_video_id': video_id,
            '_related_channel_id': channel_id,
            '_partial': True,
            'snippet': {
                'title': self.json_traverse(video, path=(
                    'title',
                    (
                        (
                            'simpleText',
                        ),
                        (
                            'runs',
                            0,
                            'text'
                        ),
                    )
                )),
                'thumbnails': video['thumbnail']['thumbnails'],
                'channelId': self.json_traverse(video, path=(
                    ('longBylineText', 'shortBylineText'),
                    'runs',
                    0,
                    'navigationEndpoint',
                    'browseEndpoint',
                    'browseId',
                )),
            }
        } for video in related_videos if video and 'videoId' in video]

        v3_response = {
            'kind': 'youtube#videoListResponse',
            'items': [],
        }

        if not retry:
            last_item = related_videos[-1]
            if last_item and 'token' in last_item:
                page_token = last_item['token']

        while 1:
            remaining = max_results - len(items)
            if remaining < 0:
                items = items[:max_results]
                if page_token:
                    v3_response['nextPageToken'] = page_token
                v3_response['offset'] = remaining
                break

            if not page_token:
                break

            if not remaining:
                v3_response['nextPageToken'] = page_token
                break

            continuation = self.get_related_videos(
                video_id,
                page_token=page_token,
                max_results=remaining,
                **kwargs
            )
            if continuation and 'nextPageToken' in continuation:
                page_token = continuation['nextPageToken']
            else:
                page_token = ''
            if 'items' in continuation:
                items.extend(continuation['items'])

        if items:
            v3_response['items'] = items
        else:
            v3_response = None
        return v3_response

    def get_parent_comments(self,
                            video_id,
                            page_token='',
                            max_results=0,
                            **kwargs):
        max_results = self._max_results if max_results <= 0 else max_results

        # prepare params
        params = {'part': 'snippet',
                  'videoId': video_id,
                  'order': 'relevance',
                  'textFormat': 'plainText',
                  'maxResults': str(max_results)}
        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET',
                                path='commentThreads',
                                params=params,
                                no_login=True,
                                **kwargs)

    def get_child_comments(self,
                           parent_id,
                           page_token='',
                           max_results=0,
                           **kwargs):
        max_results = self._max_results if max_results <= 0 else max_results

        # prepare params
        params = {'part': 'snippet',
                  'parentId': parent_id,
                  'textFormat': 'plainText',
                  'maxResults': str(max_results)}
        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET',
                                path='comments',
                                params=params,
                                no_login=True,
                                **kwargs)

    def get_channel_videos(self, channel_id, page_token='', **kwargs):
        """
        Returns a collection of video search results for the specified channel_id
        """

        params = {'part': 'snippet',
                  'hl': self._language,
                  'maxResults': str(self._max_results),
                  'type': 'video',
                  'safeSearch': 'none',
                  'order': 'date'}

        if channel_id == 'mine':
            params['forMine'] = 'true'
        else:
            params['channelId'] = channel_id

        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET',
                                path='search',
                                params=params,
                                **kwargs)

    def search(self,
               q,
               search_type=None,
               event_type='',
               channel_id='',
               order='relevance',
               safe_search='moderate',
               page_token='',
               location=False,
               **kwargs):
        """
        Returns a collection of search results that match the query parameters specified in the API request. By default,
        a search result set identifies matching video, channel, and playlist resources, but you can also configure
        queries to only retrieve a specific type of resource.
        :param q:
        :param search_type: acceptable values are: 'video' | 'channel' | 'playlist'
        :param event_type: 'live', 'completed', 'upcoming'
        :param channel_id: limit search to channel id
        :param order: one of: 'date', 'rating', 'relevance', 'title', 'videoCount', 'viewCount'
        :param safe_search: one of: 'moderate', 'none', 'strict'
        :param page_token: can be ''
        :param location: bool, use geolocation
        :return:
        """

        if search_type is None:
            search_type = ['video', 'channel', 'playlist']

        # prepare search type
        if not search_type:
            search_type = ''
        if not isinstance(search_type, string_type):
            search_type = ','.join(search_type)

        # prepare page token
        if not page_token:
            page_token = ''

        # prepare params
        params = {'q': q,
                  'part': 'snippet',
                  'regionCode': self._region,
                  'hl': self._language,
                  'relevanceLanguage': self._language,
                  'maxResults': str(self._max_results)}

        if event_type and event_type in {'live', 'upcoming', 'completed'}:
            params['eventType'] = event_type
        if search_type:
            params['type'] = search_type
        if channel_id:
            params['channelId'] = channel_id
        if order:
            params['order'] = order
        if safe_search:
            params['safeSearch'] = safe_search
        if page_token:
            params['pageToken'] = page_token

        video_only_params = ['eventType', 'videoCaption', 'videoCategoryId', 'videoDefinition',
                             'videoDimension', 'videoDuration', 'videoEmbeddable', 'videoLicense',
                             'videoSyndicated', 'videoType', 'relatedToVideoId', 'forMine']
        for key in video_only_params:
            if params.get(key) is not None:
                params['type'] = 'video'
                break

        if params['type'] == 'video' and location:
            settings = self._context.get_settings()
            location = settings.get_location()
            if location:
                params['location'] = location
                params['locationRadius'] = settings.get_location_radius()

        return self.api_request(method='GET',
                                path='search',
                                params=params,
                                **kwargs)

    def get_my_subscriptions(self,
                             page_token=1,
                             logged_in=False,
                             do_filter=False,
                             refresh=False,
                             **kwargs):
        """
        modified by PureHemp, using YouTube RSS for fetching latest videos
        """

        v3_response = {
            'kind': 'youtube#videoListResponse',
            'items': [],
        }

        cache = self._context.get_feed_history()
        settings = self._context.get_settings()

        if do_filter:
            subscription_filters = {
                'blacklist': settings.get_bool(
                    'youtube.filter.my_subscriptions_filtered.blacklist', False
                ),
                'set': {
                    item.lower()
                    for item in settings.get_string(
                        'youtube.filter.my_subscriptions_filtered.list', ''
                    ).replace(', ', ',').split(',')
                },
            }
        else:
            subscription_filters = None

        page = page_token or 1
        totals = {
            'num': 0,
            'start': -self._max_results,
            'end': page * self._max_results,
            'video_ids': set(),
        }
        totals['start'] += totals['end']

        def _sort_by_date_time(item, limits):
            video_id = item['id']
            if video_id in limits['video_ids']:
                return -1
            limits['num'] += 1
            limits['video_ids'].add(video_id)
            return item['_timestamp']

        channel_ids = []
        params = {
            'part': 'snippet',
            'maxResults': '50',
            'order': 'alphabetical',
            'mine': 'true'
        }

        def _get_channels(_params=params):
            if not _params or 'complete' in _params:
                return None, None
            json_data = self.api_request(method='GET',
                                         path='subscriptions',
                                         params=_params,
                                         **kwargs)
            if not json_data:
                return None, None

            subs_page_token = json_data.get('nextPageToken')
            if subs_page_token:
                _params['pageToken'] = subs_page_token
            else:
                _params['complete'] = True

            return 'list_list', [{
                'channel_id': item['snippet']['resourceId']['channelId']
            } for item in json_data.get('items', [])]

        bookmarks = self._context.get_bookmarks_list().get_items()
        if bookmarks:
            channel_ids.extend([
                {'channel_id': item_id}
                for item_id, item in bookmarks.items()
                if (isinstance(item, float)
                    or getattr(item, 'get_channel_id', bool)())
            ])

        feeds = {}
        headers = {
            'Host': 'www.youtube.com',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                          ' AppleWebKit/537.36 (KHTML, like Gecko)'
                          ' Chrome/87.0.4280.66 Safari/537.36',
            'Accept': 'text/html,'
                      'application/xhtml+xml,'
                      'application/xml;q=0.9,'
                      'image/webp,*/*;q=0.8',
            'DNT': '1',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.7,de;q=0.3'
        }

        def _get_feed_cache(channel_id, _cache=cache, _refresh=refresh):
            cached = _cache.get_item(channel_id)
            if cached:
                feed_details = cached['value']
                _refresh = _refresh or cached['age'] > _cache.ONE_HOUR
            else:
                feed_details = {
                    'channel_name': None,
                    'cached_items': None,
                }
                _refresh = True

            if _refresh:
                feed_details['refresh'] = True

            return 'dict_dict_dict', (channel_id, feed_details)

        def _get_feed(channel_id, _headers=headers):
            return 'dict_dict_dict', (channel_id, {
                'content': self.request(
                    'https://www.youtube.com/feeds/videos.xml?channel_id='
                    + channel_id,
                    headers=_headers,
                ),
                'refresh': True,
            })

        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'yt': 'http://www.youtube.com/xml/schemas/2015',
            'media': 'http://search.yahoo.com/mrss/',
        }

        def _parse_feeds(feeds,
                         encode=not current_system_version.compatible(19, 0),
                         filters=subscription_filters,
                         _ns=namespaces,
                         _cache=cache):
            all_items = {}
            new_cache = {}
            for channel_id, feed in feeds.items():
                channel_name = feed.get('channel_name')
                cached_items = feed.get('cached_items')
                refresh_feed = feed.get('refresh')
                content = feed.get('content')

                if refresh_feed and content:
                    content.encoding = 'utf-8'
                    content = to_unicode(content.content).replace('\n', '')

                    root = ET.fromstring(to_str(content) if encode else content)
                    channel_name = (root.findtext('atom:title', '', _ns)
                                    .lower().replace(',', ''))
                    feed_items = [{
                        'kind': 'youtube#video',
                        'id': item.findtext('yt:videoId', '', _ns),
                        'snippet': {
                            'channelId': channel_id,
                        },
                        '_timestamp': datetime_parser.since_epoch(
                            datetime_parser.strptime(
                                item.findtext('atom:published', '', _ns)
                            )
                        ),
                        '_partial': True,
                    } for item in root.findall('atom:entry', _ns)]
                else:
                    feed_items = []

                if feed_items:
                    if cached_items:
                        feed_items.extend(cached_items)
                    feed_limits = {
                        'num': 0,
                        'video_ids': set(),
                    }
                    feed_items.sort(reverse=True,
                                    key=partial(_sort_by_date_time,
                                                limits=feed_limits))
                    feed_items = feed_items[:min(1000, feed_limits['num'])]
                    new_cache[channel_id] = {
                        'channel_name': channel_name,
                        'cached_items': feed_items,
                    }
                elif cached_items:
                    feed_items = cached_items
                else:
                    continue
                if filters:
                    filtered = channel_name and channel_name in filters['set']
                    if filters['blacklist']:
                        if not filtered:
                            all_items[channel_id] = feed_items
                    elif filtered:
                        all_items[channel_id] = feed_items
                else:
                    all_items[channel_id] = feed_items

            if new_cache:
                _cache.set_items(new_cache)
            return list(chain.from_iterable(all_items.values()))

        def _threaded_fetch(kwargs,
                            output,
                            worker,
                            threads,
                            pool_id,
                            dynamic,
                            input_wait,
                            **_kwargs):
            while not threads['balance'].is_set():
                if kwargs is True:
                    _kwargs = {}
                elif kwargs:
                    _kwargs = kwargs.pop()
                elif input_wait:
                    input_wait.acquire(True)
                    input_wait.release()
                    if kwargs:
                        continue
                    break
                else:
                    break

                try:
                    output_type, _output = worker(**_kwargs)
                except Exception as exc:
                    self._context.log_error('threaded_fetch error: |{exc}|'
                                            .format(exc=exc))
                    continue

                if not output_type:
                    break
                if output_type == 'value_dict':
                    output[_output[0]] = _output[1]
                elif output_type == 'dict_dict':
                    output.update(_output)
                elif output_type == 'value_list':
                    output.append(_output)
                elif output_type == 'list_list':
                    output.extend(_output)
                elif output_type == 'value_list_dict':
                    if _output[0] not in output:
                        output[_output[0]] = []
                    output[_output[0]].append(_output[1])
                elif output_type == 'list_list_dict':
                    if _output[0] not in output:
                        output[_output[0]] = []
                    output[_output[0]].extend(_output[1])
                elif output_type == 'dict_dict_dict':
                    if _output[0] not in output:
                        output[_output[0]] = {}
                    output[_output[0]].update(_output[1])
            else:
                threads['balance'].clear()

            thread = threading.current_thread()
            threads['available'].release()
            if dynamic:
                threads['pool_counts'][pool_id] -= 1
            threads['pool_counts']['all'] -= 1
            threads['current'].discard(thread)

        try:
            num_cores = cpu_count() or 1
        except NotImplementedError:
            num_cores = 1
        max_threads = min(32, 2 * (num_cores + 4))
        threads = {
            'max': max_threads,
            'available': threading.Semaphore(max_threads),
            'current': set(),
            'pool_counts': {
                'all': 0,
            },
            'balance': threading.Event(),
        }
        payloads = [
            {
                'pool_id': 1,
                'kwargs': True,
                'output': channel_ids,
                'worker': _get_channels,
                'threads': threads,
                'limit': 1,
                'dynamic': False,
                'input_wait': None,
            },
        ] if logged_in else []
        payloads.extend((
            {
                'pool_id': 2,
                'kwargs': channel_ids,
                'output': feeds,
                'worker': _get_feed_cache,
                'threads': threads,
                'limit': 1,
                'dynamic': False,
                'input_wait': threading.Lock(),
            },
            {
                'pool_id': 3,
                'kwargs': channel_ids,
                'output': feeds,
                'worker': _get_feed,
                'threads': threads,
                'limit': None,
                'dynamic': True,
                'input_wait': threading.Lock(),
            },
        ))
        while 1:
            for payload in payloads:
                pool_id = payload['pool_id']
                if pool_id in threads['pool_counts']:
                    current_num = threads['pool_counts'][pool_id]
                else:
                    current_num = threads['pool_counts'][pool_id] = 0

                input_wait = payload['input_wait']
                if payload['kwargs']:
                    if input_wait and input_wait.locked():
                        input_wait.release()
                else:
                    continue

                available = threads['max'] - threads['pool_counts']['all']
                limit = payload['limit']
                if limit:
                    if current_num >= limit:
                        continue
                    if not available:
                        threads['balance'].set()
                elif not available:
                    continue

                thread = threading.Thread(
                    target=_threaded_fetch,
                    kwargs=payload,
                )
                thread.daemon = True
                threads['current'].add(thread)
                threads['pool_counts'][pool_id] += 1
                threads['pool_counts']['all'] += 1
                threads['available'].acquire(True)
                thread.start()

            if not threads['current']:
                break

        for thread in threads['current']:
            if thread and thread.is_alive():
                thread.join(30)

        items = _parse_feeds(feeds)

        # filter, sorting by publish date and trim
        if items:
            items.sort(reverse=True,
                       key=partial(_sort_by_date_time,
                                   limits=totals))
        else:
            return None

        if totals['num'] > totals['end']:
            v3_response['nextPageToken'] = page + 1
        if totals['num'] > totals['start']:
            items = items[totals['start']:min(totals['num'], totals['end'])]
        else:
            return None

        v3_response['items'] = items
        return v3_response

    def get_saved_playlists(self, page_token, offset):
        if not page_token:
            page_token = ''

        result = {'items': [],
                  'next_page_token': page_token,
                  'offset': offset}

        def _perform(_playlist_idx, _page_token, _offset, _result):
            _post_data = {
                'context': {
                    'client': {
                        'clientName': 'TVHTML5',
                        'clientVersion': '5.20150304',
                        'theme': 'CLASSIC',
                        'acceptRegion': '%s' % self._region,
                        'acceptLanguage': '%s' % self._language.replace('_', '-')
                    },
                    'user': {
                        'enableSafetyMode': False
                    }
                }
            }
            if _page_token:
                _post_data['continuation'] = _page_token
            else:
                _post_data['browseId'] = 'FEmy_youtube'

            _json_data = self.api_request(version=1,
                                          method='POST',
                                          path='browse',
                                          post_data=_post_data)
            _data = {}
            if 'continuationContents' in _json_data:
                _data = (_json_data.get('continuationContents', {})
                         .get('horizontalListContinuation', {}))
            elif 'contents' in _json_data:
                _data = (_json_data.get('contents', {})
                         .get('sectionListRenderer', {})
                         .get('contents', [{}])[_playlist_idx]
                         .get('shelfRenderer', {})
                         .get('content', {})
                         .get('horizontalListRenderer', {}))

            _items = _data.get('items', [])
            if not _result:
                _result = {'items': []}

            _new_offset = self._max_results - len(_result['items']) + _offset
            if _offset > 0:
                _items = _items[_offset:]
            _result['offset'] = _new_offset

            for _item in _items:
                _item = _item.get('gridPlaylistRenderer', {})
                if _item:
                    _video_item = {
                        'id': _item['playlistId'],
                        'title': (_item.get('title', {})
                                  .get('runs', [{}])[0]
                                  .get('text', '')),
                        'channel': (_item.get('shortBylineText', {})
                                    .get('runs', [{}])[0]
                                    .get('text', '')),
                        'channel_id': (_item.get('shortBylineText', {})
                                       .get('runs', [{}])[0]
                                       .get('navigationEndpoint', {})
                                       .get('browseEndpoint', {})
                                       .get('browseId', '')),
                        'thumbnails': (_item.get('thumbnail', {})
                                       .get('thumbnails', [{}])),
                    }

                    _result['items'].append(_video_item)

            _continuations = (_data.get('continuations', [{}])[0]
                              .get('nextContinuationData', {})
                              .get('continuation', ''))
            if _continuations and len(_result['items']) <= self._max_results:
                _result['next_page_token'] = _continuations

                if len(_result['items']) < self._max_results:
                    _result = _perform(_playlist_idx=playlist_index,
                                       _page_token=_continuations,
                                       _offset=0,
                                       _result=_result)

            # trim result
            if len(_result['items']) > self._max_results:
                _items = _result['items']
                _items = _items[:self._max_results]
                _result['items'] = _items
                _result['continue'] = True

            if len(_result['items']) < self._max_results:
                if 'continue' in _result:
                    del _result['continue']

                if 'next_page_token' in _result:
                    del _result['next_page_token']

                if 'offset' in _result:
                    del _result['offset']

            return _result

        _en_post_data = {
            'context': {
                'client': {
                    'clientName': 'TVHTML5',
                    'clientVersion': '5.20150304',
                    'theme': 'CLASSIC',
                    'acceptRegion': 'US',
                    'acceptLanguage': 'en-US'
                },
                'user': {
                    'enableSafetyMode': False
                }
            },
            'browseId': 'FEmy_youtube'
        }

        playlist_index = None
        json_data = self.api_request(version=1,
                                     method='POST',
                                     path='browse',
                                     post_data=_en_post_data)
        contents = (json_data.get('contents', {})
                    .get('sectionListRenderer', {})
                    .get('contents', [{}]))

        for idx, shelf in enumerate(contents):
            title = (shelf.get('shelfRenderer', {})
                     .get('title', {})
                     .get('runs', [{}])[0]
                     .get('text', ''))
            if title.lower() == 'saved playlists':
                playlist_index = idx
                break

        if playlist_index is not None:
            contents = (json_data.get('contents', {})
                        .get('sectionListRenderer', {})
                        .get('contents', [{}]))
            if 0 <= playlist_index < len(contents):
                result = _perform(_playlist_idx=playlist_index,
                                  _page_token=page_token,
                                  _offset=offset,
                                  _result=result)

        return result

    def _response_hook(self, **kwargs):
        response = kwargs['response']
        self._context.log_debug('API response: |{0.status_code}|\n'
                                'headers: |{0.headers}|'.format(response))
        if response.status_code == 204 and 'no_content' in kwargs:
            return True
        try:
            json_data = response.json()
            if 'error' in json_data:
                kwargs.setdefault('pass_data', True)
                raise YouTubeException('"error" in response JSON data',
                                       json_data=json_data,
                                       **kwargs)
        except ValueError as exc:
            kwargs.setdefault('raise_exc', True)
            raise InvalidJSON(exc, **kwargs)
        response.raise_for_status()
        return json_data

    def _error_hook(self, **kwargs):
        exc = kwargs['exc']
        json_data = getattr(exc, 'json_data', None)
        if getattr(exc, 'pass_data', False):
            data = json_data
        else:
            data = None
        if getattr(exc, 'raise_exc', False):
            exception = YouTubeException
        else:
            exception = None

        if not json_data or 'error' not in json_data:
            return None, None, None, data, None, exception

        details = json_data['error']
        reason = details.get('errors', [{}])[0].get('reason', 'Unknown')
        message = strip_html_from_text(details.get('message', 'Unknown error'))

        if getattr(exc, 'notify', True):
            ok_dialog = False
            timeout = 5000
            if reason == 'accessNotConfigured':
                notification = self._context.localize('key.requirement')
                ok_dialog = True
            elif reason == 'keyInvalid' and message == 'Bad Request':
                notification = self._context.localize('api.key.incorrect')
                timeout = 7000
            elif reason in {'quotaExceeded', 'dailyLimitExceeded'}:
                notification = message
                timeout = 7000
            else:
                notification = message

            title = '{0}: {1}'.format(self._context.get_name(), reason)
            if ok_dialog:
                self._context.get_ui().on_ok(title, notification)
            else:
                self._context.get_ui().show_notification(notification,
                                                         title,
                                                         time_ms=timeout)

        info = ('API error: {reason}\n'
                'exc: |{exc}|\n'
                'message: |{message}|')
        details = {'reason': reason, 'message': message}
        return '', info, details, data, False, exception

    def api_request(self,
                    version=3,
                    method='GET',
                    path=None,
                    params=None,
                    post_data=None,
                    headers=None,
                    no_login=False,
                    **kwargs):
        client_data = {
            '_endpoint': path.strip('/'),
            'method': method,
        }
        if headers:
            client_data['headers'] = headers
        if method in {'POST', 'PUT'}:
            if post_data:
                client_data['json'] = post_data
            clear_data = False
        else:
            clear_data = True
        if params:
            client_data['params'] = params

        # a config can decide if a token is allowed
        if (not no_login and self._access_token
                and self._config.get('token-allowed', True)):
            client_data['_access_token'] = self._access_token

        client = self.build_client(version, client_data)

        if 'key' in client['params'] and not client['params']['key']:
            key = self._config.get('key') or self._config_tv.get('key')
            if key:
                client['params']['key'] = key
            else:
                del client['params']['key']

        if clear_data and 'json' in client:
            del client['json']

        params = client.get('params')
        if params:
            log_params = deepcopy(params)
            if 'location' in log_params:
                log_params['location'] = '|xx.xxxx,xx.xxxx|'
            if 'key' in log_params:
                key = log_params['key']
                log_params['key'] = '...'.join((key[:3], key[-3:]))
        else:
            log_params = None

        headers = client.get('headers')
        if headers:
            log_headers = deepcopy(headers)
            if 'Authorization' in log_headers:
                log_headers['Authorization'] = '|logged in|'
        else:
            log_headers = None

        self._context.log_debug('API request:\n'
                                'version: |{version}|\n'
                                'method: |{method}|\n'
                                'path: |{path}|\n'
                                'params: |{params}|\n'
                                'post_data: |{data}|\n'
                                'headers: |{headers}|'
                                .format(version=version,
                                        method=method,
                                        path=path,
                                        params=log_params,
                                        data=client.get('json'),
                                        headers=log_headers))
        response = self.request(response_hook=self._response_hook,
                                response_hook_kwargs=kwargs,
                                error_hook=self._error_hook,
                                **client)
        return response

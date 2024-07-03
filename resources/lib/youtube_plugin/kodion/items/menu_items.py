# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..constants import (
    PATHS,
    PLAY_FORCE_AUDIO,
    PLAY_PROMPT_QUALITY,
    PLAY_PROMPT_SUBTITLES,
    PLAY_WITH,
)


def more_for_video(context, video_id, logged_in=False, refresh=False):
    params = {
        'video_id': video_id,
        'logged_in': logged_in,
    }
    if refresh:
        params['refresh'] = context.get_param('refresh', 0) + 1
    return (
        context.localize('video.more'),
        'RunPlugin({0})'.format(context.create_uri(
            ('video', 'more',),
            params,
        ))
    )


def related_videos(context, video_id):
    return (
        context.localize('related_videos'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.ROUTE, 'special', 'related_videos',),
            {
                'video_id': video_id,
            },
        ))
    )


def video_comments(context, video_id):
    return (
        context.localize('video.comments'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.ROUTE, 'special', 'parent_comments',),
            {
                'video_id': video_id,
            },
        ))
    )


def content_from_description(context, video_id):
    return (
        context.localize('video.description.links'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.ROUTE, 'special', 'description_links',),
            {
                'video_id': video_id,
            },
        ))
    )


def play_with(context, video_id):
    return (
        context.localize('video.play.with'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.PLAY,),
            {
                'video_id': video_id,
                PLAY_WITH: True,
            },
        ))
    )


def refresh(context):
    params = context.get_params()
    return (
        context.localize('refresh'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.ROUTE, context.get_path(),),
            dict(params, refresh=params.get('refresh', 0) + 1),
        ))
    )


def queue_video(context):
    return (
        context.localize('video.queue'),
        'Action(Queue)'
    )


def play_all_from_playlist(context, playlist_id, video_id=''):
    if video_id:
        return (
            context.localize('playlist.play.from_here'),
            'RunPlugin({0})'.format(context.create_uri(
                (PATHS.PLAY,),
                {
                    'playlist_id': playlist_id,
                    'video_id': video_id,
                    'play': True,
                },
            ))
        )
    return (
        context.localize('playlist.play.all'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.PLAY,),
            {
                'playlist_id': playlist_id,
                'play': True,
            },
        ))
    )


def add_video_to_playlist(context, video_id):
    return (
        context.localize('video.add_to_playlist'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'select', 'playlist',),
            {
                'video_id': video_id,
            },
        ))
    )


def remove_video_from_playlist(context, playlist_id, video_id, video_name):
    return (
        context.localize('remove'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'remove', 'video',),
            dict(
                context.get_params(),
                playlist_id=playlist_id,
                video_id=video_id,
                video_name=video_name,
                reload_path=context.get_path(),
            ),
        ))
    )


def rename_playlist(context, playlist_id, playlist_name):
    return (
        context.localize('rename'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'rename', 'playlist',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
        ))
    )


def delete_playlist(context, playlist_id, playlist_name):
    return (
        context.localize('delete'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'remove', 'playlist',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
        ))
    )


def remove_as_watch_later(context, playlist_id, playlist_name):
    return (
        context.localize('watch_later.list.remove'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'remove', 'watch_later',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
        ))
    )


def set_as_watch_later(context, playlist_id, playlist_name):
    return (
        context.localize('watch_later.list.set'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'set', 'watch_later',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
        ))
    )


def remove_as_history(context, playlist_id, playlist_name):
    return (
        context.localize('history.list.remove'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'remove', 'history',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
        ))
    )


def set_as_history(context, playlist_id, playlist_name):
    return (
        context.localize('history.list.set'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'set', 'history',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
        ))
    )


def remove_my_subscriptions_filter(context, channel_name):
    return (
        context.localize('my_subscriptions.filter.remove'),
        'RunPlugin({0})'.format(context.create_uri(
            ('my_subscriptions', 'filter',),
            {
                'channel_name': channel_name,
                'action': 'remove'
            },
        ))
    )


def add_my_subscriptions_filter(context, channel_name):
    return (
        context.localize('my_subscriptions.filter.add'),
        'RunPlugin({0})'.format(context.create_uri(
            ('my_subscriptions', 'filter',),
            {
                'channel_name': channel_name,
                'action': 'add',
            },
        ))
    )


def rate_video(context, video_id, refresh=False):
    params = {
        'video_id': video_id,
    }
    if refresh:
        params['refresh'] = context.get_param('refresh', 0) + 1
    return (
        context.localize('video.rate'),
        'RunPlugin({0})'.format(context.create_uri(
            ('video', 'rate',),
            params,
        ))
    )


def watch_later_add(context, playlist_id, video_id):
    return (
        context.localize('watch_later.add'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'add', 'video',),
            {
                'playlist_id': playlist_id,
                'video_id': video_id,
            },
        ))
    )


def watch_later_local_add(context, item):
    return (
        context.localize('watch_later.add'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.WATCH_LATER, 'add',),
            {
                'video_id': item.video_id,
                'item': repr(item),
            },
        ))
    )


def watch_later_local_remove(context, video_id):
    return (
        context.localize('watch_later.remove'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.WATCH_LATER, 'remove',),
            {
                'video_id': video_id,
            },
        ))
    )


def watch_later_local_clear(context):
    return (
        context.localize('watch_later.clear'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.WATCH_LATER, 'clear',),
        ))
    )


def go_to_channel(context, channel_id, channel_name):
    return (
        context.localize('go_to_channel') % context.get_ui().bold(channel_name),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.ROUTE, 'channel', channel_id,),
        ))
    )


def subscribe_to_channel(context, channel_id, channel_name=''):
    return (
        context.localize('subscribe_to') % context.get_ui().bold(channel_name)
        if channel_name else
        context.localize('subscribe'),
        'RunPlugin({0})'.format(context.create_uri(
            ('subscriptions', 'add',),
            {
                'subscription_id': channel_id,
            },
        ))
    )


def unsubscribe_from_channel(context, channel_id=None, subscription_id=None):
    return (
        context.localize('unsubscribe'),
        'RunPlugin({0})'.format(context.create_uri(
            ('subscriptions', 'remove',),
            {
                'subscription_id': subscription_id,
            },
        )) if subscription_id else
        'RunPlugin({0})'.format(context.create_uri(
            ('subscriptions', 'remove',),
            {
                'channel_id': channel_id,
            },
        ))
    )


def play_with_subtitles(context, video_id):
    return (
        context.localize('video.play.with_subtitles'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.PLAY,),
            {
                'video_id': video_id,
                PLAY_PROMPT_SUBTITLES: True,
            },
        ))
    )


def play_audio_only(context, video_id):
    return (
        context.localize('video.play.audio_only'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.PLAY,),
            {
                'video_id': video_id,
                PLAY_FORCE_AUDIO: True,
            },
        ))
    )


def play_ask_for_quality(context, video_id):
    return (
        context.localize('video.play.ask_for_quality'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.PLAY,),
            {
                'video_id': video_id,
                PLAY_PROMPT_QUALITY: True,
            },
        ))
    )


def history_remove(context, video_id):
    return (
        context.localize('history.remove'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.HISTORY,),
            {
                'action': 'remove',
                'video_id': video_id
            },
        ))
    )


def history_clear(context):
    return (
        context.localize('history.clear'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.HISTORY,),
            {
                'action': 'clear'
            },
        ))
    )


def history_mark_watched(context, video_id):
    return (
        context.localize('history.mark.watched'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.HISTORY,),
            {
                'video_id': video_id,
                'action': 'mark_watched',
            },
        ))
    )


def history_mark_unwatched(context, video_id):
    return (
        context.localize('history.mark.unwatched'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.HISTORY,),
            {
                'video_id': video_id,
                'action': 'mark_unwatched',
            },
        ))
    )


def history_reset_resume(context, video_id):
    return (
        context.localize('history.reset.resume_point'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.HISTORY,),
            {
                'video_id': video_id,
                'action': 'reset_resume',
            },
        ))
    )


def bookmark_add(context, item):
    return (
        context.localize('bookmark'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.BOOKMARKS, 'add',),
            {
                'item_id': item.get_id(),
                'item': repr(item),
            },
        ))
    )


def bookmark_add_channel(context, channel_id, channel_name=''):
    return (
        (context.localize('bookmark.channel') % (
            context.get_ui().bold(channel_name) if channel_name else
            context.localize(19029)
        )),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.BOOKMARKS, 'add',),
            {
                'item_id': channel_id,
                'item': None,
            },
        ))
    )


def bookmark_remove(context, item_id):
    return (
        context.localize('bookmark.remove'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.BOOKMARKS, 'remove',),
            {
                'item_id': item_id,
            },
        ))
    )


def bookmarks_clear(context):
    return (
        context.localize('bookmarks.clear'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.BOOKMARKS, 'clear',),
        ))
    )


def search_remove(context, query):
    return (
        context.localize('search.remove'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.SEARCH, 'remove',),
            {
                'q': query,
            },
        ))
    )


def search_rename(context, query):
    return (
        context.localize('search.rename'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.SEARCH, 'rename',),
            {
                'q': query,
            },
        ))
    )


def search_clear(context):
    return (
        context.localize('search.clear'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.SEARCH, 'clear',),
        ))
    )


def separator():
    return (
        '--------',
        'noop'
    )


def goto_home(context):
    return (
        context.localize(10000),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.ROUTE, PATHS.HOME,),
            {
                'window_return': False,
            },
        ))
    )


def goto_quick_search(context):
    return (
        context.localize('search.quick'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.ROUTE, PATHS.SEARCH, 'input',),
        ))
    )


def goto_page(context, params=None):
    return (
        context.localize('page.choose'),
        'RunPlugin({0})'.format(context.create_uri(
            (PATHS.GOTO_PAGE, context.get_path(),),
            params or context.get_params(),
        ))
    )

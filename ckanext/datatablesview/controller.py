# encoding: utf-8

from six.moves.urllib.parse import urlencode

from six import text_type

from ckan.plugins.toolkit import BaseController, get_action, request, h
from ckan.common import json


class DataTablesController(BaseController):
    def ajax(self, resource_view_id):
        resource_view = get_action(u'resource_view_show')(
            None, {u'id': resource_view_id})

        draw = int(request.params['draw'])
        search_text = text_type(request.params['search[value]'])
        offset = int(request.params['start'])
        limit = int(request.params['length'])
        view_filters = resource_view.get(u'filters', {})
        user_filters = text_type(request.params['filters'])
        filters = merge_filters(view_filters, user_filters)

        datastore_search = get_action(u'datastore_search')
        unfiltered_response = datastore_search(None, {
            u"resource_id": resource_view[u'resource_id'],
            u"limit": 0,
            u"filters": view_filters,
        })

        cols = [f['id'] for f in unfiltered_response['fields']]
        if u'show_fields' in resource_view:
            cols = [c for c in cols if c in resource_view['show_fields']]

        sort_list = []
        i = 0
        while True:
            if u'order[%d][column]' % i not in request.params:
                break
            sort_by_num = int(request.params[u'order[%d][column]' % i])
            sort_order = (
                u'desc' if request.params[u'order[%d][dir]' % i] == u'desc'
                else u'asc')
            sort_list.append(cols[sort_by_num] + u' ' + sort_order)
            i += 1

        response = datastore_search(None, {
            u"q": search_text,
            u"resource_id": resource_view[u'resource_id'],
            u"offset": offset,
            u"limit": limit,
            u"sort": u', '.join(sort_list),
            u"filters": filters,
        })

        return json.dumps({
            u'draw': draw,
            u'iTotalRecords': unfiltered_response.get(u'total', 0),
            u'iTotalDisplayRecords': response.get(u'total', 0),
            u'aaData': [
                [text_type(row.get(colname, u'')) for colname in cols]
                for row in response['records']
            ],
        })

    def filtered_download(self, resource_view_id):
        params = json.loads(request.params['params'])
        resource_view = get_action(u'resource_view_show')(
            None, {u'id': resource_view_id})

        search_text = text_type(params['search']['value'])
        view_filters = resource_view.get(u'filters', {})
        user_filters = text_type(params['filters'])
        filters = merge_filters(view_filters, user_filters)

        datastore_search = get_action(u'datastore_search')
        unfiltered_response = datastore_search(None, {
            u"resource_id": resource_view[u'resource_id'],
            u"limit": 0,
            u"filters": view_filters,
        })

        cols = [f['id'] for f in unfiltered_response['fields']]
        if u'show_fields' in resource_view:
            cols = [c for c in cols if c in resource_view['show_fields']]

        sort_list = []
        for order in params['order']:
            sort_by_num = int(order['column'])
            sort_order = (
                u'desc' if order['dir'] == u'desc'
                else u'asc')
            sort_list.append(cols[sort_by_num] + u' ' + sort_order)

        cols = [c for (c, v) in zip(cols, params['visible']) if v]

        h.redirect_to(
            h.url_for(
                u'datastore.dump',
                resource_id=resource_view[u'resource_id'])
            + u'?' + urlencode({
                u'q': search_text,
                u'sort': u','.join(sort_list),
                u'filters': json.dumps(filters),
                u'format': request.params['format'],
                u'fields': u','.join(cols),
            }))


def merge_filters(view_filters, user_filters_str):
    u'''
    view filters are built as part of the view, user filters
    are selected by the user interacting with the view. Any filters
    selected by user may only tighten filters set in the view,
    others are ignored.

    >>> merge_filters({
    ...    u'Department': [u'BTDT'], u'OnTime_Status': [u'ONTIME']},
    ...    u'CASE_STATUS:Open|CASE_STATUS:Closed|Department:INFO')
    {u'Department': [u'BTDT'],
     u'OnTime_Status': [u'ONTIME'],
     u'CASE_STATUS': [u'Open', u'Closed']}
    '''
    filters = dict(view_filters)
    if not user_filters_str:
        return filters
    user_filters = {}
    for k_v in user_filters_str.split(u'|'):
        k, sep, v = k_v.partition(u':')
        if k not in view_filters or v in view_filters[k]:
            user_filters.setdefault(k, []).append(v)
    for k in user_filters:
        filters[k] = user_filters[k]
    return filters

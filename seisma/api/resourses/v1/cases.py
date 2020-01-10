# -*- coding: utf-8 -*-


"""
Case Resource
-------------

==============  ==============================  ========
Field name      Field description               Readonly
==============  ==============================  ========
name            unique name                     Yes
created         creation date                   Yes
description     case description                No
==============  ==============================  ========


Case Result Resource
--------------------

==============  ==============================  ========
Field name      Field description               Readonly
==============  ==============================  ========
date            creation datetime               Yes
reason          reason of crash                 Yes
runtime         time of execution               Yes
status          result status. choice from      Yes
                (
                'passed',
                'skipped',
                'failed',
                'error'
                )
case            case resource                   Yes
metadata        Metadata of a case result.      Yes
                Key -> value array.
==============  ==============================  ========


Commands
--------
"""


from http import HTTPStatus as statuses

import flask
from sqlalchemy import desc

from ... import string
from ...result import make_result
from ...resource import ApiResource
from ...utils import paginated_query
from ....database import schema as db
from ....constants import API_AUTO_CREATION_PARAM


VERSION = 1

FIELD_NAME_TO_FIELD_INSTANCE = {
    'date': db.CaseResult.date,
    'runtime': db.CaseResult.runtime,
}


resource = ApiResource(__name__, version=VERSION)


@resource.route('/jobs/<string:job_name>/cases/<string:case_name>', methods=['GET'])
def get_case_from_job(job_name, case_name):
    """
    .. http:get:: /jobs/(string:job_name)/cases/(string:case_name)

    Get only ony case from job by name.

    :return: Case Resource
    """
    job = db.Job.get_by_name(job_name)

    if job:
        case = db.Case.query.filter_by(job_id=job.id, name=case_name).first()

        if case:
            return make_result(case), statuses.OK


@resource.route(
    '/jobs/<string:job_name>/cases/<string:case_name>',
    methods=['POST'],
    schema='case.post.json',
)
def add_case_to_job(job_name, case_name):
    """
    .. http:post:: /jobs/(string:job_name)/cases/(string:case_name)

    Add case to job, statistic about case stored separated of case data.

    :jsonparam string description: about case. it's can be docstring for example

    :return: Case Resource
    """
    job = db.Job.get_by_name(job_name)

    if job:
        json = flask.request.get_json()

        data = {
            'job_id': job.id,
            'name': case_name,
            'description': json.get('description', ''),
        }
        case = db.Case.create(**data)

        return make_result(case), statuses.CREATED


@resource.route(
    '/jobs/<string:job_name>/cases/<string:case_name>',
    methods=['PUT'],
    schema='case.put.json',
)
def update_case_in_job(job_name, case_name):
    """
    .. http:put:: /jobs/(string:job_name)/cases/(string:case_name)

    Update case in job, statistic about case stored separated of case data.

    :jsonparam string description: about case. it's can be docstring for example

    :return: Case Resource
    """
    job = db.Job.get_by_name(job_name)

    if job:
        case = db.Case.query.filter_by(job_id=job.id, name=case_name).first()

        if case:

            json = flask.request.get_json()

            case = case.update(**json)

            return make_result(case), statuses.OK


@resource.route('/jobs/<string:job_name>/cases', methods=['GET'])
def get_cases_from_job(job_name):
    """
    .. http:get:: /jobs/(string:job_name)/cases

    Get list of cases from job.

    :return: Case Resource List
    """
    job = db.Job.get_by_name(job_name)

    if job:
        query = db.Case.query.filter_by(job_id=job.id)
        query = query.order_by(desc(db.Case.created))
        query = paginated_query(query, flask.request)

        return make_result(
            query.all(),
            total_count=query.total_count,
        ), statuses.OK


@resource.route('/jobs/<string:job_name>/cases/<string:case_name>/stat', methods=['GET'])
def get_stats_of_case_from_job(job_name, case_name):
    """
    .. http:get:: /jobs/(string:job_name)/cases/(string:case_name)/stat

    Get statistic of case from job.

    :query string status: can be in (passed, skipped, failed, error)
    :query string date_from: range from date (use with date_to only)
    :query string date to: range to date (use with date_from only)
    :query int runtime_more: where runtime more than value
    :query int runtime_less: where runtime less than value
    :query string sort_by: sort results by field

    :return: Case Result Resource List
    """
    job = db.Job.get_by_name(job_name)

    if job:
        case = db.Case.query.filter_by(job_id=job.id, name=case_name).first()

        if case:
            status = flask.request.args.get('status', None)
            date_to = flask.request.args.get('date_to', None)
            date_from = flask.request.args.get('date_from', None)
            runtime_more = flask.request.args.get('runtime_more', None)
            runtime_less = flask.request.args.get('runtime_less', None)
            sort_by = flask.request.args.get('sort_by', 'date')

            sort_key = FIELD_NAME_TO_FIELD_INSTANCE.get(sort_by, db.CaseResult.date)

            query = db.CaseResult.query.filter_by(case_id=case.id)

            if status in db.CASE_STATUSES_CHOICE:
                query = query.filter(db.CaseResult.status == status)

            if date_from is not None:
                date_from = string.to_datetime(date_from, no_time=True)
                query = query.filter(db.CaseResult.date >= date_from)

            if date_to is not None:
                date_to = string.to_datetime(date_to, no_time=True, to_end_day=True)
                query = query.filter(db.CaseResult.date <= date_to)

            if runtime_more is not None:
                query = query.filter(db.CaseResult.runtime > string.to_float(runtime_more))
            elif runtime_less is not None:
                query = query.filter(db.CaseResult.runtime < string.to_float(runtime_less))

            query = query.order_by(desc(sort_key))
            query = paginated_query(query, flask.request)

            return make_result(
                query.all(),
                total_count=query.total_count,
            ), statuses.OK


@resource.route('/jobs/<string:job_name>/cases/<string:case_name>/stat/<int:result_id>', methods=['GET'])
def get_case_result_by_id(job_name, case_name, result_id):
    """
    .. http:get:: /jobs/(string:job_name)/cases/(string:case_name)/stat/<int:result_id>

    Get statistic of only one case by id.

    :return: Case Result Resource
    """
    job = db.Job.get_by_name(job_name)

    if job:
        case = db.Case.query.filter_by(job_id=job.id, name=case_name).first()

        if case:
            case_result = db.CaseResult.query.filter_by(
                id=result_id,
                case_id=case.id
            ).first()
            return make_result(case_result), statuses.OK


@resource.route(
    '/jobs/<string:job_name>/builds/<string:build_name>/cases/<string:case_name>',
    methods=['POST'],
    schema='case_result.post.json',
)
def add_case_to_build(job_name, build_name, case_name):
    """
    .. http:post:: /jobs/(string:job_name)/builds/(string:build_name)/cases/(string:case_name)

    Add case to a build.

    :jsonparam string status: choice from (passed, skipped, failed, error)
    :jsonparam float runtime: time of execution
    :jsonparam string reason: crush's reason
    :jsonparam array metadata: dictionary with contains info about case result.
        Key and value can be of string type only.

    :query string autocreation: magic param if case doesn't exists then will created new case on job.

    :return: Case Result Resource
    """
    job = db.Job.get_by_name(job_name)

    if job:
        build = db.Build.query.filter_by(job_id=job.id, name=build_name).first()

        if build:
            case = db.Case.query.filter_by(job_id=job.id, name=case_name).first()

            if not case and flask.request.args.get(API_AUTO_CREATION_PARAM):
                case = db.Case.create(name=case_name, job_id=job.id)

            if case:
                json = flask.request.get_json()

                data = {
                    'case_id': case.id,
                    'build_id': build.id,
                    'status': json.get('status'),
                    'runtime': json.get('runtime'),
                    'reason': json.get('reason', ''),
                    'dialect': json.get('dialect', '')
                }
                metadata = json.get('metadata')

                case_result = db.CaseResult.create(**data)

                if metadata:
                    case_result.md = metadata

                return make_result(case_result), statuses.CREATED


@resource.route('/jobs/<string:job_name>/builds/<string:build_name>/cases', methods=['GET'])
def get_cases_from_build(job_name, build_name):
    """
    .. http:get:: /jobs/(string:job_name)/builds/(string:build_name)/cases

    Get case result list from build

    :query string status: can be in (passed, skipped, failed, error)
    :query int runtime_more: where runtime more than value
    :query int runtime_less: where runtime less than value
    :query string sort_by: sort results by field

    :return: Case Result Resource List
    """
    job = db.Job.get_by_name(job_name)

    if job:
        build = db.Build.query.filter_by(job_id=job.id, name=build_name).first()

        if build:
            status = flask.request.args.get('status', None)
            runtime_more = flask.request.args.get('runtime_more', None)
            runtime_less = flask.request.args.get('runtime_less', None)
            sort_by = flask.request.args.get('sort_by', None)

            sort_key = FIELD_NAME_TO_FIELD_INSTANCE.get(sort_by, db.CaseResult.date)

            query = db.CaseResult.query.filter_by(build_id=build.id)

            if status in db.CASE_STATUSES_CHOICE:
                query = query.filter(db.CaseResult.status == status)

            if runtime_more is not None:
                query = query.filter(db.CaseResult.runtime > string.to_float(runtime_more))
            elif runtime_less is not None:
                query = query.filter(db.CaseResult.runtime < string.to_float(runtime_less))

            query = query.order_by(desc(sort_key))
            query = paginated_query(query, flask.request)

            return make_result(
                query.all(),
                total_count=query.total_count,
            ), statuses.OK


@resource.route(
    '/jobs/<string:job_name>/builds/<string:build_name>/cases/<string:case_name>',
    methods=['GET'],
)
def get_case_from_build(job_name, build_name, case_name):
    """
    .. http:get:: /jobs/(string:job_name)/builds/(string:build_name)/cases/(string:case_name)

    Get only one case result from a build by case name.

    :return: Case Result Resource
    """
    job = db.Job.get_by_name(job_name)

    if job:
        build = db.Build.query.filter_by(job_id=job.id, name=build_name).first()

        if build:
            case = db.Case.query.filter_by(job_id=job.id, name=case_name).first()

            if case:
                case_result = db.CaseResult.query.filter_by(
                    build_id=build.id, case_id=case.id,
                ).first()

                if case_result:
                    return make_result(case_result), statuses.OK


@resource.route('/jobs/<string:job_name>/cases/stat', methods=['GET'])
def get_cases_stats_from_job(job_name):
    """
    .. http:get:: /jobs/(string:job_name)/cases/stat

    Get statistic of cases from job.

    :query string status: can be in (passed, skipped, failed, error)
    :query string date_from: range from date
    :query string date to: range to date
    :query int runtime_more: where runtime more than value
    :query int runtime_less: where runtime less than value
    :query string sort_by: sort results by field

    :return: Case Resource List
    """
    job = db.Job.get_by_name(job_name)

    if job:
        status = flask.request.args.get('status', None)
        date_to = flask.request.args.get('date_to', None)
        date_from = flask.request.args.get('date_from', None)
        runtime_more = flask.request.args.get('runtime_more', None)
        runtime_less = flask.request.args.get('runtime_less', None)
        sort_by = flask.request.args.get('sort_by', 'date')

        sort_key = FIELD_NAME_TO_FIELD_INSTANCE.get(sort_by, db.CaseResult.date)

        query = db.CaseResult.query.join(
            db.Build,
        ).filter(db.Build.job_id == job.id)

        if date_from is not None:
            date_from = string.to_datetime(date_from, no_time=True)
            query = query.filter(db.CaseResult.date >= date_from)

        if date_to is not None:
            date_to = string.to_datetime(date_to, no_time=True, to_end_day=True)
            query = query.filter(db.CaseResult.date <= date_to)

        if status in db.CASE_STATUSES_CHOICE:
            query = query.filter(db.CaseResult.status == status)

        if runtime_more is not None:
            query = query.filter(db.CaseResult.runtime > string.to_float(runtime_more))
        elif runtime_less is not None:
            query = query.filter(db.CaseResult.runtime < string.to_float(runtime_less))

        query = query.order_by(desc(sort_key))
        query = paginated_query(query, flask.request)

        return make_result(
            query.all(),
            total_count=query.total_count,
        ), statuses.OK

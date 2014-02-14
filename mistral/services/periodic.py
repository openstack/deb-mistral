# -*- coding: utf-8 -*-
#
# Copyright 2013 - Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.


from mistral.db import api as db_api
from mistral.engine import engine
from mistral.openstack.common import log
from mistral.openstack.common import periodic_task
from mistral.openstack.common import threadgroup
from mistral import context
from mistral import dsl
from mistral.services import scheduler as sched
from mistral.services import trusts

LOG = log.getLogger(__name__)


class MistralPeriodicTasks(periodic_task.PeriodicTasks):
    @periodic_task.periodic_task(spacing=1, run_immediately=True)
    def scheduler_events(self, ctx):
        LOG.debug('Processing next Scheduler events.')

        for event in sched.get_next_events():
            wb = db_api.workbook_get(event['workbook_name'])
            context.set_ctx(trusts.create_context(wb))

            try:
                task = dsl.Parser(
                    wb['definition']).get_event_task_name(event['name'])
                engine.start_workflow_execution(wb['name'], task)
            finally:
                sched.set_next_execution_time(event)
                context.set_ctx(None)


def setup():
    tg = threadgroup.ThreadGroup()
    pt = MistralPeriodicTasks()

    tg.add_dynamic_timer(
        pt.run_periodic_tasks,
        initial_delay=None,
        periodic_interval_max=1,
        context=None)

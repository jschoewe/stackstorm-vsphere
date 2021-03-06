import threading

from pyVmomi import vim  # pylint: disable-msg=E0611
from base import VSphereSensor
from datetime import datetime


class TaskInfoSensor(VSphereSensor):
    DEFAULT_TASKNUM = 3
    DEFAULT_VSPHERE = 'default'

    def setup(self):
        self._log = self.sensor_service.get_logger(__name__)

        self._tasknum = self._get_config_entry('tasknum', prefix='sensors.taskinfo')
        if not self._tasknum:
            self._tasknum = self.DEFAULT_TASKNUM

        # Make a connection with vSphere server
        vsphere = self._get_config_entry('vsphere', prefix='sensors.taskinfo')
        if not vsphere:
            vsphere = self.DEFAULT_VSPHERE

        # Connect to the vSphere server
        self.establish_connection(vsphere)

        self._collector = self._get_task_collector()

    def poll(self):
        if self._collector:
            for taskinfo in self._collector.ReadNextTasks(self._tasknum):
                self._log.debug('Found a TaskInfo: %s' % taskinfo)

                # dispatches taskinfo trigger
                self._dispatch_taskinfo(taskinfo)

                # If task is uncompleted, waiting until it completes then dispatches it again
                if taskinfo.state == vim.TaskInfo.State.running:
                    threading.Thread(target=self._wait_until_task_complete,
                                     args=[taskinfo.task]).start()

    def _wait_until_task_complete(self, task):
        """Waits until target task complete, then dispatch trigger"""
        while task.info.state == vim.TaskInfo.State.running:
            pass

        self._dispatch_taskinfo(task.info)

    def _get_task_collector(self):
        # set filter to get TaskInfo which is queued in the vSphere after executing this Sensor
        time_filter = vim.TaskFilterSpec.ByTime()
        time_filter.timeType = vim.TaskFilterSpec.TimeOption.queuedTime
        time_filter.beginTime = datetime.now()

        filter_spec = vim.TaskFilterSpec(time=time_filter)

        try:
            return self.si_content.taskManager.CreateCollectorForTasks(filter=filter_spec)
        except Exception as e:
            self._log.error(e)

    def _dispatch_taskinfo(self, taskinfo):
        self.sensor_service.dispatch(trigger='vsphere.taskinfo', payload={
            'task_id': taskinfo.key,
            'operation_name': taskinfo.descriptionId,
            'queue_time':
                taskinfo.queueTime and taskinfo.queueTime.strftime('%Y/%m/%d %H:%M:%S') or '',
            'start_time':
                taskinfo.startTime and taskinfo.startTime.strftime('%Y/%m/%d %H:%M:%S') or '',
            'complete_time':
                taskinfo.completeTime and taskinfo.completeTime.strftime('%Y/%m/%d %H:%M:%S') or '',
            'state': str(taskinfo.state),
        })

    def cleanup(self):
        pass

    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass

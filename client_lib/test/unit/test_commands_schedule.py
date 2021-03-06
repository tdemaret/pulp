import copy

import mock

from pulp.bindings.responses import Response
from pulp.client.commands import schedule as commands
from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.extensions.core import TAG_FAILURE, TAG_SUCCESS, TAG_PARAGRAPH
from pulp.devel.unit import base


EXAMPLE_SCHEDULE_LIST = [
    {
        "next_run": "2012-05-31T00:00:00Z",
        "_id": "4fba4c7fba35be0be4000046",
        "first_run": "2012-05-31T00:00:00Z",
        "schedule": "2012-05-31T00:00:00Z/P1M",
        "enabled": True,
        "last_run": None,
        "failure_threshold": None,
        "override_config": {},
        "remaining_runs": None,
        "consecutive_failures": 0,
        "_href": "/pulp/api/v2/repositories/ks/importers/yum_importer/sync_schedules/"
                 "4fba4c7fba35be0be4000046/"
    },
    {
        "next_run": "2012-06-30T00:00:00Z",
        "_id": "4fba4c8dba35be0be4000050",
        "first_run": "2012-06-30T00:00:00Z",
        "schedule": "2012-06-30T00:00:00Z/P1M",
        "enabled": True,
        "last_run": None,
        "failure_threshold": None,
        "override_config": {},
        "remaining_runs": None,
        "consecutive_failures": 0,
        "_href": "/pulp/api/v2/repositories/ks/importers/yum_importer/sync_schedules/"
                 "4fba4c8dba35be0be4000050/"
    },
    {
        "next_run": "2012-05-22T00:00:00Z",
        "_id": "4fba4ca0ba35be0be4000055",
        "first_run": "2012-05-15T00:00:00Z",
        "schedule": "2012-05-15T00:00:00Z/P1W",
        "enabled": True,
        "last_run": "2012-05-15T00:00:00Z",
        "failure_threshold": None,
        "override_config": {},
        "remaining_runs": None,
        "consecutive_failures": 0,
        "_href": "/pulp/api/v2/repositories/ks/importers/yum_importer/sync_schedules/"
                 "4fba4ca0ba35be0be4000055/"
    }
]


class TestListScheduleCommand(base.PulpClientTests):

    def test_list(self):
        # Setup
        strategy = mock.Mock()
        strategy.retrieve_schedules.return_value = Response(200,
                                                            copy.deepcopy(EXAMPLE_SCHEDULE_LIST))

        list_command = commands.ListScheduleCommand(self.context, strategy, 'list', 'list')
        list_command.create_option('--extra', 'extra')
        self.cli.add_command(list_command)

        # Test
        self.cli.run('list --extra foo'.split())

        # Verify
        self.assertEqual(strategy.retrieve_schedules.call_count, 1)
        self.assertEqual(strategy.retrieve_schedules.call_args[0][0]['extra'], 'foo')

        # Spot check the ID lines in the displayed list
        id_lines = [l for l in self.recorder.lines if l.startswith('Id')]
        self.assertEqual(3, len(id_lines))

        ids = [l.split()[1] for l in id_lines]
        self.assertTrue(EXAMPLE_SCHEDULE_LIST[0]['_id'] in ids)
        self.assertTrue(EXAMPLE_SCHEDULE_LIST[1]['_id'] in ids)
        self.assertTrue(EXAMPLE_SCHEDULE_LIST[2]['_id'] in ids)

    def test_list_details(self):
        # Setup
        strategy = mock.Mock()
        strategy.retrieve_schedules.return_value = Response(
            200, copy.deepcopy(EXAMPLE_SCHEDULE_LIST))

        list_command = commands.ListScheduleCommand(self.context, strategy, 'list', 'list')
        self.cli.add_command(list_command)

        # Test
        self.cli.run('list --details'.split())

        # Verify
        self.assertEqual(strategy.retrieve_schedules.call_count, 1)

        # Spot check the ID lines in the displayed list
        fr_lines = [l for l in self.recorder.lines if l.startswith('First Run')]
        self.assertEqual(3, len(fr_lines))

        first_runs = [l.split()[2] for l in fr_lines]
        self.assertTrue(EXAMPLE_SCHEDULE_LIST[0]['first_run'] in first_runs)
        self.assertTrue(EXAMPLE_SCHEDULE_LIST[1]['first_run'] in first_runs)
        self.assertTrue(EXAMPLE_SCHEDULE_LIST[2]['first_run'] in first_runs)


class TestCreateCommand(base.PulpClientTests):

    def test_add(self):
        # Setup
        strategy = mock.Mock()
        strategy.create_schedule.return_value = Response(201, {})

        create_command = commands.CreateScheduleCommand(self.context, strategy, 'add', 'add')
        create_command.create_option('--extra', 'extra')
        self.cli.add_command(create_command)

        # Test
        self.cli.run(
            'add --schedule 2012-05-22T00:00:00/P1D --failure-threshold 10 --extra foo'.split())

        # Verify
        args = strategy.create_schedule.call_args[0]
        self.assertEqual('2012-05-22T00:00:00/P1D', args[0])
        self.assertEqual(10, args[1])
        self.assertEqual(True, args[2])
        self.assertEqual('foo', args[3]['extra'])

        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_SUCCESS, self.prompt.get_write_tags()[0])

    def test_add_with_error(self):
        # Setup
        strategy = mock.Mock()
        strategy.create_schedule.side_effect = ValueError('bad value')

        create_command = commands.CreateScheduleCommand(self.context, strategy, 'add', 'add')
        self.cli.add_command(create_command)

        # Test
        self.cli.run('add --schedule 2012-05-22T00:00:00/P1D --failure-threshold 10'.split())

        # Verify
        args = strategy.create_schedule.call_args[0]
        self.assertEqual('2012-05-22T00:00:00/P1D', args[0])
        self.assertEqual(10, args[1])
        self.assertEqual(True, args[2])

        self.assertEqual(2, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[1])


class TestDeleteCommand(base.PulpClientTests):

    def test_delete(self):
        # Setup
        strategy = mock.Mock()
        strategy.create_schedule.return_value = Response(200, {})

        delete_command = commands.DeleteScheduleCommand(self.context, strategy, 'delete', 'delete')
        delete_command.create_option('--extra', 'extra stuff')
        self.cli.add_command(delete_command)

        # Test
        self.cli.run('delete --schedule-id foo --extra e1'.split())

        # Verify
        args = strategy.delete_schedule.call_args[0]
        self.assertEqual('foo', args[0])
        self.assertTrue('extra' in args[1])
        self.assertEqual('e1', args[1]['extra'])

        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_SUCCESS, self.prompt.get_write_tags()[0])


class TestUpdateCommand(base.PulpClientTests):

    def test_update(self):
        # Setup
        strategy = mock.Mock()
        strategy.update_schedule.return_value = Response(200, {})

        update_command = commands.UpdateScheduleCommand(self.context, strategy, 'update', 'update')
        update_command.create_option('--extra', 'extra')
        self.cli.add_command(update_command)

        # Test
        self.cli.run('update --schedule-id foo --schedule 2012-05-22T00:00:00/P1D '
                     '--failure-threshold 1 --enabled true --extra bar'.split())

        # Verify
        args = strategy.update_schedule.call_args[0]
        self.assertEqual(1, len(args))
        self.assertEqual('foo', args[0])

        kwargs = strategy.update_schedule.call_args[1]
        self.assertTrue('schedule' in kwargs)
        self.assertEqual('2012-05-22T00:00:00/P1D', kwargs['schedule'])
        self.assertTrue('failure_threshold' in kwargs)
        self.assertEqual(1, kwargs['failure_threshold'])
        self.assertTrue('enabled' in kwargs)
        self.assertEqual(True, kwargs['enabled'])

        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_SUCCESS, self.prompt.get_write_tags()[0])


class TestNextRunCommand(base.PulpClientTests):

    def test_next_run(self):
        # Setup
        strategy = mock.Mock()
        strategy.retrieve_schedules.return_value = Response(200, copy.copy(EXAMPLE_SCHEDULE_LIST))

        next_command = commands.NextRunCommand(self.context, strategy, 'next', 'next')
        next_command.create_option('--extra', 'extra')
        self.cli.add_command(next_command)

        # Test
        self.cli.run('next --extra foo'.split())

        # Verify
        self.assertEqual(1, strategy.retrieve_schedules.call_count)
        self.assertEqual(strategy.retrieve_schedules.call_args[0][0]['extra'], 'foo')

        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_PARAGRAPH, self.prompt.get_write_tags()[0])
        self.assertTrue('2012-05-22T00:00:00Z' in self.recorder.lines[0])
        self.assertTrue('2012-05-15T00:00:00Z/P1W' in self.recorder.lines[0])

    def test_next_run_no_schedules(self):
        # Setup
        strategy = mock.Mock()
        strategy.retrieve_schedules.return_value = Response(200, {})

        next_command = commands.NextRunCommand(self.context, strategy, 'next', 'next')
        self.cli.add_command(next_command)

        # Test
        self.cli.run('next'.split())

        # Verify
        self.assertTrue('no schedules' in self.recorder.lines[0])

    def test_next_run_quiet(self):
        # Setup
        strategy = mock.Mock()
        strategy.retrieve_schedules.return_value = Response(200, copy.copy(EXAMPLE_SCHEDULE_LIST))

        next_command = commands.NextRunCommand(self.context, strategy, 'next', 'next')
        self.cli.add_command(next_command)

        # Test
        self.cli.run('next --quiet'.split())

        # Verify
        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_PARAGRAPH, self.prompt.get_write_tags()[0])
        self.assertEqual('2012-05-22T00:00:00Z\n', self.recorder.lines[0])


class TestRepoScheduleStrategy(base.PulpClientTests):
    """
    Test the RepoScheduleStrategy class.
    """
    @mock.patch('pulp.client.commands.schedule.ScheduleStrategy.__init__', autospec=True)
    def test___init__(self, __init__):
        """
        Test the constructor.
        """
        fake_api = mock.MagicMock()
        fake_type_id = 'fake_type_id'

        strat = commands.RepoScheduleStrategy(fake_api, fake_type_id)

        # Make sure our superclass __init__() was called, and the correct attributes were set
        __init__.assert_called_once_with()
        self.assertEqual(strat.type_id, fake_type_id)
        self.assertEqual(strat.api, fake_api)

    def test_create_schedule(self):
        """
        Test the create_schedule() method.
        """
        fake_api = mock.MagicMock()
        expected_return_value = 'return_value'
        fake_api.add_schedule = mock.MagicMock(return_value=expected_return_value)
        fake_type_id = 'fake_type_id'
        strat = commands.RepoScheduleStrategy(fake_api, fake_type_id)
        schedule = '2012-05-22T00:00:00/P1D'
        failure_threshold = 1
        enabled = True
        repo_id = 'awesome_repo'
        kwargs = {OPTION_REPO_ID.keyword: repo_id}

        return_value = strat.create_schedule(schedule, failure_threshold, enabled, kwargs)

        # For now, the override_config is not configurable, and it is an empty dict
        expected_override_config = {}
        fake_api.add_schedule.assert_called_once_with(
            repo_id, fake_type_id, schedule, expected_override_config, failure_threshold, enabled)
        self.assertEqual(return_value, expected_return_value)

    def test_delete_schedule(self):
        """
        Test the delete_schedule() method.
        """
        fake_api = mock.MagicMock()
        expected_return_value = 'return_value'
        fake_api.delete_schedule = mock.MagicMock(return_value=expected_return_value)
        fake_type_id = 'fake_type_id'
        strat = commands.RepoScheduleStrategy(fake_api, fake_type_id)
        schedule_id = 'schedule_id'
        repo_id = 'awesome_repo'
        kwargs = {OPTION_REPO_ID.keyword: repo_id}

        return_value = strat.delete_schedule(schedule_id, kwargs)

        fake_api.delete_schedule.assert_called_once_with(repo_id, fake_type_id, schedule_id)
        self.assertEqual(return_value, expected_return_value)

    def test_retrieve_schedules(self):
        """
        Test the retrieve_schedules() method.
        """
        fake_api = mock.MagicMock()
        expected_return_value = 'return_value'
        fake_api.list_schedules = mock.MagicMock(return_value=expected_return_value)
        fake_type_id = 'fake_type_id'
        strat = commands.RepoScheduleStrategy(fake_api, fake_type_id)
        repo_id = 'awesome_repo'
        kwargs = {OPTION_REPO_ID.keyword: repo_id}

        return_value = strat.retrieve_schedules(kwargs)

        fake_api.list_schedules.assert_called_once_with(repo_id, fake_type_id)
        self.assertEqual(return_value, expected_return_value)

    def test_update_schedule(self):
        """
        Test the update_schedule() method.
        """
        fake_api = mock.MagicMock()
        expected_return_value = 'return_value'
        fake_api.update_schedule = mock.MagicMock(return_value=expected_return_value)
        fake_type_id = 'fake_type_id'
        strat = commands.RepoScheduleStrategy(fake_api, fake_type_id)
        schedule_id = 'schedule_id'
        repo_id = 'awesome_repo'
        other_args = {'a': 1, 'b': 2}
        kwargs = {OPTION_REPO_ID.keyword: repo_id}
        kwargs.update(other_args)

        return_value = strat.update_schedule(schedule_id, **kwargs)

        fake_api.update_schedule.assert_called_once_with(repo_id, fake_type_id, schedule_id,
                                                         **other_args)
        self.assertEqual(return_value, expected_return_value)

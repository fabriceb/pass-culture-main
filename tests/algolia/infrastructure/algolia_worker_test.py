from unittest.mock import MagicMock, patch, call

from algolia.infrastructure.algolia_worker import process_multi_indexing, _run_indexing


class ProcessMultiIndexingTest:
    @patch('algolia.infrastructure.algolia_worker.get_venue_providers')
    def test_should_retrieve_venue_providers_to_process(self, mock_get_venue_providers):
        # Given
        client = MagicMock()

        # When
        process_multi_indexing(client=client)

        # Then
        mock_get_venue_providers.assert_called_once_with(client=client)

    @patch('algolia.infrastructure.algolia_worker.delete_venue_providers')
    @patch('algolia.infrastructure.algolia_worker.get_venue_providers')
    def test_should_delete_venue_providers_to_process(self, mock_get_venue_providers, mock_delete_venue_providers):
        # Given
        client = MagicMock()

        # When
        process_multi_indexing(client=client)

        # Then
        mock_delete_venue_providers.assert_called_once_with(client=client)

    @patch.dict('os.environ', {"ALGOLIA_SYNC_WORKERS_POOL_SIZE": '2'})
    @patch('algolia.infrastructure.algolia_worker.ALGOLIA_WAIT_TIME_FOR_AVAILABLE_WORKER')
    @patch('algolia.infrastructure.algolia_worker.sleep')
    @patch('algolia.infrastructure.algolia_worker._run_indexing')
    @patch('algolia.infrastructure.algolia_worker.get_number_of_venue_providers_currently_in_sync')
    @patch('algolia.infrastructure.algolia_worker.delete_venue_providers')
    @patch('algolia.infrastructure.algolia_worker.get_venue_providers')
    def test_should_run_indexing_until_reaching_max_pool_size(self,
                                                              mock_get_venue_providers,
                                                              mock_delete_venue_providers,
                                                              mock_get_number_of_venue_providers_currently_in_sync,
                                                              mock_run_indexing,
                                                              mock_sleep,
                                                              mock_wait_time_for_available_worker):
        # Given
        client = MagicMock()
        venue_provider1 = {'id': 1, 'providerId': 1, 'venueId': 1}
        venue_provider2 = {'id': 2, 'providerId': 2, 'venueId': 2}
        venue_provider3 = {'id': 3, 'providerId': 3, 'venueId': 3}
        mock_get_venue_providers.return_value = [venue_provider1, venue_provider2, venue_provider3]
        mock_get_number_of_venue_providers_currently_in_sync.side_effect = [
            0,
            1,
            2,
            1
        ]
        mock_wait_time_for_available_worker.return_value = 2

        # When
        process_multi_indexing(client=client)

        # Then
        assert mock_run_indexing.call_count == 3
        assert mock_run_indexing.call_args_list == [
            call(client=client, venue_provider={'id': 1, 'providerId': 1, 'venueId': 1}),
            call(client=client, venue_provider={'id': 2, 'providerId': 2, 'venueId': 2}),
            call(client=client, venue_provider={'id': 3, 'providerId': 3, 'venueId': 3})
        ]
        mock_sleep.assert_called_once_with(mock_wait_time_for_available_worker)


class RunIndexingTest:
    @patch('algolia.infrastructure.algolia_worker.run_process_in_one_off_container')
    def test_should_run_process_in_a_one_off_container(self, mock_run_process_in_one_off_container):
        # Given
        client = MagicMock()
        venue_provider = {
            'id': 1,
            'providerId': '2',
            'venueId': 3
        }
        run_algolia_venue_provider_command = f"PYTHONPATH=. " \
                                             f"python scripts/pc.py process_venue_provider_offers_for_algolia " \
                                             f"--venue-provider-id {venue_provider['id']} " \
                                             f"--provider-id {venue_provider['providerId']} " \
                                             f"--venueId {venue_provider['venueId']} "

        # When
        _run_indexing(client=client, venue_provider=venue_provider)

        # Then
        mock_run_process_in_one_off_container.assert_called_once_with(run_algolia_venue_provider_command)

    @patch('algolia.infrastructure.algolia_worker.add_venue_provider_currently_in_sync')
    @patch('algolia.infrastructure.algolia_worker.run_process_in_one_off_container')
    def test_should_add_venue_provider_to_hash_of_venue_providers_in_sync(self,
                                                                          mock_run_process_in_one_off_container,
                                                                          mock_add_venue_provider_currently_in_sync):
        # Given
        client = MagicMock()
        venue_provider = {
            'id': 1,
            'providerId': '2',
            'venueId': 3
        }
        mock_run_process_in_one_off_container.return_value = 'azerty123'

        # When
        _run_indexing(client=client, venue_provider=venue_provider)

        # Then
        mock_add_venue_provider_currently_in_sync.assert_called_once_with(client=client,
                                                                          container_id='azerty123',
                                                                          venue_provider_id=venue_provider['id'])

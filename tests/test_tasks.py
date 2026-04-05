from unittest.mock import MagicMock, patch

import pytest

from app.celery_app import celery_app

# Enable eager mode for testing (tasks run synchronously)
celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
)


class TestCeleryConfig:
    def test_celery_app_name(self):
        assert celery_app.main == "docpipeline"

    def test_celery_serializer_config(self):
        assert celery_app.conf.task_serializer == "json"
        assert "json" in celery_app.conf.accept_content

    def test_celery_timezone(self):
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True


class TestProcessDocumentTask:
    def test_task_is_registered(self):
        from app.tasks import process_document_task

        assert process_document_task.name is not None
        assert process_document_task.max_retries == 3

    def test_task_calls_pipeline(self):
        from app.tasks import process_document_task

        with patch("app.tasks._run_async") as mock_run:
            mock_run.return_value = None
            # Call the task function directly with apply
            result = process_document_task.apply(
                args=["test-doc-id"],
            )
            assert result.result["status"] == "completed"
            mock_run.assert_called_once()

    def test_task_retries_on_failure(self):
        from celery.exceptions import Retry
        from app.tasks import process_document_task

        with patch("app.tasks._run_async", side_effect=Exception("Pipeline error")):
            with pytest.raises(Retry):
                process_document_task.apply(args=["test-doc-id"])


class TestProcessBatchTask:
    def test_task_is_registered(self):
        from app.tasks import process_batch_task

        assert process_batch_task.name is not None

    def test_batch_processes_all(self):
        from app.tasks import process_batch_task

        with patch("app.tasks._run_async") as mock_run:
            mock_run.return_value = None
            result = process_batch_task.apply(
                args=[["id-1", "id-2", "id-3"]],
            )
            data = result.result
            assert data["total"] == 3
            assert len(data["results"]) == 3
            assert all(r["status"] == "completed" for r in data["results"])

    def test_batch_handles_individual_failures(self):
        from app.tasks import process_batch_task

        call_count = 0

        def fail_second_call(coro):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Second doc failed")
            return None

        with patch("app.tasks._run_async", side_effect=fail_second_call):
            result = process_batch_task.apply(
                args=[["id-1", "id-2", "id-3"]],
            )
            data = result.result
            assert data["total"] == 3
            assert data["results"][0]["status"] == "completed"
            assert data["results"][1]["status"] == "failed"
            assert data["results"][2]["status"] == "completed"

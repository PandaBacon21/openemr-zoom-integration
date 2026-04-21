from pathlib import Path


def _patch_path(filename: str) -> Path:
    return Path(__file__).resolve().parents[2] / "patches" / "zoom_appointment_listener" / filename


def test_bootstrap_registers_dialog_close_listener():
    text = _patch_path("Bootstrap.php").read_text(encoding="utf-8")

    assert "AppointmentDialogCloseEvent" in text
    assert "DialogCloseListener" in text
    assert "AppointmentDialogCloseEvent::EVENT_NAME" in text
    assert "onDialogClose" in text


def test_openemr_bootstrap_requires_dialog_close_listener():
    text = _patch_path("openemr.bootstrap.php").read_text(encoding="utf-8")

    assert "require_once $module['path'] . '/DialogCloseListener.php';" in text


def test_dialog_close_listener_emits_appointment_deleted_payload():
    text = _patch_path("DialogCloseListener.php").read_text(encoding="utf-8")

    assert "'event'    => 'appointment.deleted'" in text
    assert "$event->getDialogAction() !== 'delete'" in text
    assert "'eid'      => (int)$eid" in text
    assert "'X-Zoomly-Signature: ' . $signature" in text


def test_appointment_listener_includes_new_payload_fields_and_all_day_guard():
    text = _patch_path("AppointmentListener.php").read_text(encoding="utf-8")

    assert "All-day event, skipping" in text
    assert "'duration_minutes' => $durationMinutes" in text
    assert "'title'            => !empty($postData['form_title'])" in text
    assert "'room'             => !empty($postData['form_room'])" in text

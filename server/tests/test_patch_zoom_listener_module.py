from pathlib import Path


def _patch_path(filename: str) -> Path:
    return Path(__file__).resolve().parents[2] / "patches" / "zoom_appointment_listener" / filename


def _epic_cti_path(filename: str) -> Path:
    return Path(__file__).resolve().parents[2] / "patches" / "epic_cti" / filename


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
    assert "zoomly_bridge_post('/webhooks/openemr', $payloadJson, 5)" in text


def test_appointment_listener_includes_new_payload_fields_and_all_day_guard():
    text = _patch_path("AppointmentListener.php").read_text(encoding="utf-8")

    assert "All-day event, skipping" in text
    assert "'duration_minutes' => $durationMinutes" in text
    assert "'title'            => !empty($postData['form_title'])" in text
    assert "'room'             => !empty($postData['form_room'])" in text


def test_epic_cti_inject_bootstraps_with_openemr_user_id():
    text = _epic_cti_path("cti_subscriber_inject.php").read_text(encoding="utf-8")

    assert "$_SESSION['authUserID']" in text
    assert "zoomly_bridge_post('/zoomly/epic-zcc/screenpop/bootstrap'" in text
    assert "window.ZoomlyEpicCti" in text


def test_epic_cti_subscriber_uses_eventsource_and_openemr_tabs():
    text = _epic_cti_path("cti_subscriber.js").read_text(encoding="utf-8")

    assert "new EventSource(stream.url)" in text
    assert 'source.addEventListener("navigate", handleNavigate)' in text
    assert "/interface/patient_file/summary/demographics.php?set_pid=" in text
    assert "/interface/main/finder/dynamic_finder.php?search_any=" in text
    assert "window.navigateTab" in text


def test_main_patch_loads_epic_cti_assets_and_panel():
    text = (Path(__file__).resolve().parents[2] / "patches" / "main.php").read_text(encoding="utf-8")

    assert "/interface/epic_cti/cti_panel.css" in text
    assert "cti_subscriber_inject.php" in text
    assert "/interface/epic_cti/cti_subscriber.js" in text
    assert "cti_panel.php" in text

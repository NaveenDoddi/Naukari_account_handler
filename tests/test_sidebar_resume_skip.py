from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sidebar import (
    detect_question_type,
    find_checkbox_option_element,
    is_resume_upload_prompt,
)


class DummyElement:
    def __init__(self, text="", value="", element_id=""):
        self.text = text
        self.value = value
        self.element_id = element_id
        self.clicked = False

    def click(self):
        self.clicked = True

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def get_attribute(self, name):
        if name == "value":
            return self.value
        if name == "id":
            return self.element_id
        if name == "for":
            return self.element_id
        return None


class DummyDriver:
    def __init__(self, has_file_input=False, labels=None, inputs=None):
        self.has_file_input = has_file_input
        self.labels = labels or []
        self.inputs = inputs or []

    def find_elements(self, by, value):
        if value == "input[type='file']" and self.has_file_input:
            return [object()]
        if value == "label":
            return self.labels
        if value == "input[type='checkbox']":
            return self.inputs
        if value == "div.multiselectcheckboxes":
            return [object()] if self.inputs else []
        if value == "input[name='day'], input[name='month'], input[name='year']":
            return []
        return []

    def find_element(self, by, value):
        if value == "input[type='checkbox']":
            return self.inputs[0] if self.inputs else None
        return None


def test_resume_upload_prompt_detection():
    class DummyDriver:
        def __init__(self, has_file_input=False):
            self.has_file_input = has_file_input

        def find_elements(self, by, value):
            if value == "input[type='file']" and self.has_file_input:
                return [object()]
            return []

    assert is_resume_upload_prompt("Please upload your resume", DummyDriver()) is True
    assert is_resume_upload_prompt("Please upload your CV", DummyDriver()) is True
    assert is_resume_upload_prompt("Tell us about yourself", DummyDriver()) is False
    assert (
        is_resume_upload_prompt("Any other details?", DummyDriver(has_file_input=True))
        is False
    )


def test_checkbox_detection_and_matching_use_label_text():
    input_el = DummyElement(element_id="chk-experience")
    label = DummyElement(text="2-4 years", element_id="chk-experience")
    driver = DummyDriver(labels=[label], inputs=[input_el])

    assert detect_question_type(driver) == "checkbox"
    assert find_checkbox_option_element(driver, "2-4 years") is input_el


def test_checkbox_detection_with_multiselect_input_selector():
    input_el = DummyElement(value="Yes, I can join Immediately")
    driver = DummyDriver(inputs=[input_el])

    assert detect_question_type(driver) == "checkbox"


def test_checkbox_label_fallback_returns_label_when_input_is_hidden():
    label = DummyElement(text="Yes, I can join Immediately", element_id="chk-join")
    driver = DummyDriver(labels=[label], inputs=[])

    result = find_checkbox_option_element(driver, "Yes, I can join Immediately")
    assert result is label

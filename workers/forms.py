from django import forms
from django.utils import timezone

from workers.models import AttendanceRecord


class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ("category", "record_date")
        widgets = {
            "record_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["record_date"].required = False
        self.fields["record_date"].help_text = "Optional — defaults to today."

    def clean_record_date(self):
        value = self.cleaned_data.get("record_date")
        if not value:
            return timezone.localdate()
        return value

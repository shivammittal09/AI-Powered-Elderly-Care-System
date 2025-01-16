from django.db import models

class FallLog(models.Model):
    snapshot_url = models.URLField(null=True, blank=True)  # Optional URL for snapshot
    timestamp = models.DateTimeField()  # When the fall was detected
    status = models.CharField(max_length=50)  # Status like 'Fall Detected', 'False Alarm', etc.

    def __str__(self):
        return f"{self.timestamp} - {self.status}"

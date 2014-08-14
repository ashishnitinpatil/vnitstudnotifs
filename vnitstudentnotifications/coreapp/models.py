from django.db import models


class Posts(models.Model):
    """Database Model to store each update/notification."""

    url      = models.URLField(max_length=256)
    title    = models.CharField(max_length=256)
    added_on = models.DateTimeField(auto_now_add=True)
    added_on.editable = True

    def __unicode__(self):
        return u"{0}".format(self.title)

    class Meta:
        ordering = ["-added_on",]
        verbose_name_plural = "Posts"


class Urls(models.Model):
    """Database Model to store each notification page url."""

    url      = models.URLField(max_length=256, verbose_name="Notifs Site URL")
    added_on = models.DateTimeField(auto_now_add=True, editable=True)

    def __unicode__(self):
        return u"{0}".format(self.url)

    class Meta:
        ordering = ["-added_on",]
        verbose_name_plural = "Urls"

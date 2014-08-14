from django.contrib import admin
from vnitstudentnotifications.coreapp.models import Posts, Urls


class PostsAdmin(admin.ModelAdmin):
    list_display  = ("title", "added_on")
    search_fields = ("title",)
    list_filter   = ("added_on",)
    # readonly_fields = ('added_on',)


class UrlsAdmin(admin.ModelAdmin):
    readonly_fields = ('added_on',)


admin.site.register(Posts, PostsAdmin)
admin.site.register(Urls, UrlsAdmin)

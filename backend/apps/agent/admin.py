from django.contrib import admin

from apps.agent.models import AgentRun, Proposal, Source


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "section", "is_active", "needs_browser", "last_status")
    list_filter = ("kind", "is_active", "needs_browser", "section")
    search_fields = ("name", "url")


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ("kind", "status", "source_url", "created_at")
    list_filter = ("kind", "status")
    readonly_fields = ("created_at", "reviewed_at")


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    list_display = ("status", "started_at", "finished_at")
    readonly_fields = ("started_at", "finished_at", "stats", "errors")

from django.contrib import admin
from .models import Order, OrderItem, Question

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0 # Don't show extra empty forms
    readonly_fields = ('product', 'quantity', 'price') # Items shouldn't be editable directly on order admin

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total', 'shipping_address', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'user__username', 'user__email', 'shipping_address__street')
    readonly_fields = ('user', 'total', 'created_at', 'updated_at')
    inlines = [OrderItemInline]

class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'user', 'parent', 'text_preview', 'is_answered', 'created_at')
    list_filter = ('is_answered', 'created_at', 'product')
    search_fields = ('text', 'user__username', 'product__name')
    readonly_fields = ('created_at', 'answered_at')
    actions = ['mark_as_answered']

    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Question Text'

    def mark_as_answered(self, request, queryset):
        for question in queryset:
            question.mark_as_answered()
        self.message_user(request, "Selected questions marked as answered.")
    mark_as_answered.short_description = "Mark selected questions as answered"


admin.site.register(Order, OrderAdmin)
admin.site.register(Question, QuestionAdmin)
